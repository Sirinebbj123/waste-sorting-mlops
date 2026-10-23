"""Pipeline complet : YOLO trouve les déchets, le ResNet18 reconnaît leur matière.

Utilisation rapide (depuis la racine du projet, venv activé) :
    python -m waste_core.pipeline chemin\\vers\\photo.jpg

Lit : ml/models/yolo_yolov8n_640.pt   (sortie de l'étape DVC train_yolo)
      ml/models/cls_resnet18_ft.pt    (sortie de l'étape DVC train_cls)
"""

import hashlib
import json
import sys
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms

from waste_core.bins import CLASSES, MATIERES_FR, poubelle

ROOT = Path(__file__).resolve().parents[1]
YOLO_DEFAUT = ROOT / "ml" / "models" / "yolo_yolov8n_640.pt"
CLS_DEFAUT = ROOT / "ml" / "models" / "cls_resnet18_ft.pt"

# Mêmes réglages que t_eval dans ml/src/train/train_cls.py : une image doit être
# préparée exactement comme pendant l'évaluation, sinon les prédictions se dégradent
IMG_SIZE = 224
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
PREPARATION = transforms.Compose(
    [
        transforms.Resize(IMG_SIZE),
        transforms.CenterCrop(IMG_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ]
)


def empreinte(chemin: Path) -> str:
    """md5 du fichier : c'est la même valeur que celle notée par DVC dans dvc.lock."""
    return hashlib.md5(Path(chemin).read_bytes()).hexdigest()


def charger_classifieur(chemin: Path) -> nn.Module:
    modele = models.resnet18(weights=None)  # architecture vide, les poids viennent du fichier
    modele.fc = nn.Linear(modele.fc.in_features, len(CLASSES))
    modele.load_state_dict(torch.load(chemin, map_location="cpu"))
    modele.eval()
    return modele


class WastePipeline:
    def __init__(self, yolo_path=YOLO_DEFAUT, cls_path=CLS_DEFAUT, seuil=0.25, imgsz=640):
        from ultralytics import YOLO  # import ici : il est lent, on ne le paie qu'une fois

        yolo_path, cls_path = Path(yolo_path), Path(cls_path)
        for chemin in (yolo_path, cls_path):
            if not chemin.exists():
                raise FileNotFoundError(
                    f"{chemin} introuvable. Récupère les modèles avec : "
                    "dvc pull -j 2 train_cls train_yolo"
                )
        self.detecteur = YOLO(str(yolo_path))
        self.classifieur = charger_classifieur(cls_path)
        self.seuil = seuil
        self.imgsz = imgsz
        self.versions = {
            "detecteur": f"{yolo_path.name} ({empreinte(yolo_path)[:8]})",
            "classifieur": f"{cls_path.name} ({empreinte(cls_path)[:8]})",
        }

    def classer(self, images: list[Image.Image]) -> list[tuple[str, float]]:
        """Matière et confiance pour chaque image (déchet découpé)."""
        lot = torch.stack([PREPARATION(img) for img in images])
        with torch.no_grad():
            probas = torch.softmax(self.classifieur(lot), dim=1)
        scores, indices = probas.max(dim=1)
        return [(CLASSES[i], s) for i, s in zip(indices.tolist(), scores.tolist(), strict=True)]

    def predire(self, image: Image.Image) -> dict:
        image = image.convert("RGB")
        sorties = self.detecteur.predict(image, conf=self.seuil, imgsz=self.imgsz, verbose=False)
        resultat = sorties[0]  # une seule image envoyée, donc un seul résultat
        boites = resultat.boxes.xyxy.tolist()
        confiances = resultat.boxes.conf.tolist()

        if boites:
            mode = "detection"
            decoupes = [image.crop(tuple(b)) for b in boites]
        else:
            # Aucun déchet trouvé (photo d'un seul objet en gros plan, comme TrashNet) :
            # on classe l'image entière pour quand même donner une réponse
            mode = "image_entiere"
            boites = [[0.0, 0.0, float(image.width), float(image.height)]]
            confiances = [None]
            decoupes = [image]

        detections = []
        matieres = self.classer(decoupes)
        for boite, conf, (matiere, score) in zip(boites, confiances, matieres, strict=True):
            detections.append(
                {
                    "boite": [round(v, 1) for v in boite],
                    "confiance_detection": None if conf is None else round(conf, 4),
                    "matiere": matiere,
                    "matiere_fr": MATIERES_FR[matiere],
                    "confiance_matiere": round(score, 4),
                    "poubelle": poubelle(matiere),
                }
            )
        return {
            "largeur": image.width,
            "hauteur": image.height,
            "mode": mode,
            "detections": detections,
            "versions": self.versions,
        }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Utilisation : python -m waste_core.pipeline chemin\\vers\\photo.jpg")
    resultat = WastePipeline().predire(Image.open(sys.argv[1]))
    print(json.dumps(resultat, indent=2, ensure_ascii=False))
