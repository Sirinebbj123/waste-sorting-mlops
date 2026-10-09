"""Entraîne un classifieur de matière sur TrashNet et trace tout dans MLflow.

Utilisation (depuis la racine du projet, venv activé) :
    python ml/src/train/train_cls.py --model simple_cnn
    python ml/src/train/train_cls.py --model resnet18

Lit    : ml/configs/train_cls.yaml
         ml/data/processed/trashnet/{train,val}/<classe>/*.jpg   (produit par dvc repro)
Écrit  : ml/models/cls_<modele>.pt                (poids, hors Git)
         ml/reports/cls_<modele>.json             (résultats sur val, dans Git)
         un run MLflow dans mlflow.db / mlruns/   (hors Git)

Le jeu de test n'est PAS utilisé ici : il est réservé à l'évaluation finale.
"""

import argparse
import json
import random
import subprocess
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import torch
import yaml
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "ml" / "configs" / "train_cls.yaml"
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]  # normalisation ImageNet


# ---------- Modèles ----------

class SimpleCNN(nn.Module):
    """4 blocs Conv -> BatchNorm -> ReLU -> MaxPool, puis une couche de décision."""

    def __init__(self, n_classes):
        super().__init__()

        def bloc(c_in, c_out):
            return nn.Sequential(
                nn.Conv2d(c_in, c_out, kernel_size=3, padding=1),
                nn.BatchNorm2d(c_out),
                nn.ReLU(),
                nn.MaxPool2d(2),
            )

        self.features = nn.Sequential(bloc(3, 32), bloc(32, 64), bloc(64, 128), bloc(128, 256))
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.classifier = nn.Sequential(nn.Flatten(), nn.Dropout(0.3), nn.Linear(256, n_classes))

    def forward(self, x):
        return self.classifier(self.pool(self.features(x)))


def creer_modele(nom, n_classes, cfg):
    if nom == "simple_cnn":
        return SimpleCNN(n_classes)
    if nom == "resnet18":
        modele = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        if cfg.get("freeze_backbone", True):
            for p in modele.parameters():
                p.requires_grad = False  # on gèle tout le réseau pré-entraîné
        modele.fc = nn.Linear(modele.fc.in_features, n_classes)  # nouvelle couche, entraînable
        return modele
    raise ValueError(f"Modèle inconnu : {nom}")


# ---------- Données ----------

def charger_donnees(cfg, img_size, batch_size):
    data_dir = ROOT / cfg["data_dir"]
    t_train = transforms.Compose([
        transforms.RandomResizedCrop(img_size, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    t_eval = transforms.Compose([
        transforms.Resize(img_size),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    train = datasets.ImageFolder(data_dir / "train", transform=t_train)
    val = datasets.ImageFolder(data_dir / "val", transform=t_eval)
    # num_workers=0 : le plus sûr sous Windows
    return (DataLoader(train, batch_size=batch_size, shuffle=True, num_workers=0),
            DataLoader(val, batch_size=batch_size, shuffle=False, num_workers=0),
            train.classes, train.targets)


# ---------- Métriques (sans bibliothèque externe) ----------

def matrice_confusion(vrais, predits, n):
    m = np.zeros((n, n), dtype=int)
    for v, p in zip(vrais, predits):
        m[v, p] += 1
    return m


def f1_par_classe(m):
    tp = np.diag(m).astype(float)
    precision = tp / np.maximum(m.sum(axis=0), 1)
    rappel = tp / np.maximum(m.sum(axis=1), 1)
    return 2 * precision * rappel / np.maximum(precision + rappel, 1e-9)


def evaluer(modele, loader, critere):
    modele.eval()
    perte, vrais, predits = 0.0, [], []
    with torch.no_grad():
        for x, y in loader:
            sortie = modele(x)
            perte += critere(sortie, y).item() * len(y)
            vrais += y.tolist()
            predits += sortie.argmax(1).tolist()
    return perte / len(vrais), vrais, predits


def dessiner_confusion(m, classes, chemin):
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.imshow(m, cmap="Blues")
    ax.set_xticks(range(len(classes)), classes, rotation=45)
    ax.set_yticks(range(len(classes)), classes)
    ax.set_xlabel("prédit")
    ax.set_ylabel("vrai")
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, m[i, j], ha="center", va="center",
                    color="white" if m[i, j] > m.max() / 2 else "black")
    ax.set_title("Matrice de confusion (val)")
    fig.tight_layout()
    fig.savefig(chemin, dpi=100)
    plt.close(fig)


# ---------- Traçabilité ----------

def commit_git():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "inconnu"


def version_donnees(etape):
    """Empreinte DVC des données préparées, lue dans dvc.lock."""
    lock = ROOT / "dvc.lock"
    if not lock.exists():
        return "inconnue"
    contenu = yaml.safe_load(lock.read_text(encoding="utf-8"))
    return contenu["stages"][etape]["outs"][0]["md5"]


# ---------- Entraînement ----------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["simple_cnn", "resnet18"], required=True)
    nom = parser.parse_args().model

    cfg_globale = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    cfg = cfg_globale["models"][nom]
    seed = cfg_globale["seed"]
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(cfg_globale.get("num_threads", 4))

    train_loader, val_loader, classes, cibles = charger_donnees(cfg_globale, cfg["img_size"], cfg["batch_size"])
    n = len(classes)
    modele = creer_modele(nom, n, cfg)

    if cfg_globale.get("class_weights", True):
        effectifs = np.bincount(cibles, minlength=n)
        poids = torch.tensor(effectifs.sum() / (n * effectifs), dtype=torch.float32)
    else:
        poids = None
    critere = nn.CrossEntropyLoss(weight=poids)
    optimiseur = torch.optim.Adam([p for p in modele.parameters() if p.requires_grad], lr=cfg["lr"])

    dossier_modeles = ROOT / "ml" / "models"
    dossier_rapports = ROOT / "ml" / "reports"
    dossier_modeles.mkdir(parents=True, exist_ok=True)
    dossier_rapports.mkdir(parents=True, exist_ok=True)
    chemin_poids = dossier_modeles / f"cls_{nom}.pt"

    mlflow.set_tracking_uri("sqlite:///" + (ROOT / "mlflow.db").as_posix())
    mlflow.set_experiment(cfg_globale["experiment"])
    with mlflow.start_run(run_name=nom):
        mlflow.set_tags({"git_commit": commit_git(),
                         "data_version": version_donnees("prepare_trashnet"),
                         "model_family": nom})
        mlflow.log_params({"model": nom, "seed": seed, "class_weights": poids is not None,
                           "n_train": len(cibles), **cfg})

        meilleur_f1, debut = -1.0, time.time()
        for epoque in range(1, cfg["epochs"] + 1):
            modele.train()
            perte_train, n_vus = 0.0, 0
            for x, y in train_loader:
                optimiseur.zero_grad()
                perte = critere(modele(x), y)
                perte.backward()
                optimiseur.step()
                perte_train += perte.item() * len(y)
                n_vus += len(y)

            perte_val, vrais, predits = evaluer(modele, val_loader, critere)
            m = matrice_confusion(vrais, predits, n)
            acc = np.trace(m) / m.sum()
            f1_macro = f1_par_classe(m).mean()
            mlflow.log_metrics({"train_loss": perte_train / n_vus, "val_loss": perte_val,
                                "val_accuracy": acc, "val_f1_macro": f1_macro}, step=epoque)
            print(f"époque {epoque:2d}/{cfg['epochs']}  train_loss {perte_train / n_vus:.3f}  "
                  f"val_loss {perte_val:.3f}  val_acc {acc:.3f}  val_f1 {f1_macro:.3f}")
            if f1_macro > meilleur_f1:
                meilleur_f1 = f1_macro
                torch.save(modele.state_dict(), chemin_poids)

        # Évaluation finale du meilleur modèle sur val
        modele.load_state_dict(torch.load(chemin_poids))
        _, vrais, predits = evaluer(modele, val_loader, critere)
        m = matrice_confusion(vrais, predits, n)
        f1 = f1_par_classe(m)
        resultat = {
            "model": nom,
            "val_accuracy": round(float(np.trace(m) / m.sum()), 4),
            "val_f1_macro": round(float(f1.mean()), 4),
            **{f"val_f1_{c}": round(float(v), 4) for c, v in zip(classes, f1)},
            "train_minutes": round((time.time() - debut) / 60, 1),
        }
        mlflow.log_metrics({k: v for k, v in resultat.items() if k.startswith("val_")})
        mlflow.log_metric("train_minutes", resultat["train_minutes"])

        chemin_cm = dossier_rapports / f"cls_{nom}_confusion.png"
        dessiner_confusion(m, classes, chemin_cm)
        chemin_json = dossier_rapports / f"cls_{nom}.json"
        chemin_json.write_text(json.dumps(resultat, indent=2), encoding="utf-8")
        mlflow.log_artifact(str(chemin_cm))
        mlflow.log_artifact(str(chemin_json))
        mlflow.log_artifact(str(chemin_poids))

    print(json.dumps(resultat, indent=2))
    print("Résultats écrits dans", chemin_json.relative_to(ROOT))


if __name__ == "__main__":
    main()
