"""Prépare le dataset Roboflow pour le détecteur YOLO.

Lit    : ml/data/raw/roboflow/{train,valid,test}/{images,labels} + data.yaml
Écrit  : ml/data/processed/roboflow/images/{train,val,test}/*.jpg
         ml/data/processed/roboflow/labels/{train,val,test}/*.txt
         ml/data/processed/roboflow/data.yaml (pour Ultralytics)
         ml/reports/roboflow_split.json (résumé, suivi comme métrique DVC)

Étapes : 1) rassemble toutes les images des 3 splits Roboflow
         2) les regroupe par photo d'origine (le nom avant ".rf.")
         3) refait un découpage train / val / test PAR GROUPE : toutes les copies
            augmentées d'une même photo vont dans le même split (pas de fuite)
         4) réécrit les labels : polygones -> boxes, et une seule classe "waste"
            si single_class est vrai (YOLO trouve, le CNN donnera la matière)
"""

import json
import random
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]  # dossier du projet
RAW = ROOT / "ml" / "data" / "raw" / "roboflow"
OUT = ROOT / "ml" / "data" / "processed" / "roboflow"
REPORT = ROOT / "ml" / "reports" / "roboflow_split.json"
EXTS = {".jpg", ".jpeg", ".png"}

# Valeurs utilisées tant que params.yaml n'a pas encore de section "roboflow"
DEFAUT = {"split": {"train": 0.70, "val": 0.15, "test": 0.15}, "single_class": True}


def lire_params():
    fichier = ROOT / "params.yaml"
    params = yaml.safe_load(fichier.read_text(encoding="utf-8")) if fichier.exists() else None
    params = params or {}
    return params.get("seed", 42), params.get("roboflow", DEFAUT)


def lire_noms_classes():
    config = yaml.safe_load((RAW / "data.yaml").read_text(encoding="utf-8"))
    noms = config["names"]
    if isinstance(noms, dict):
        noms = [noms[k] for k in sorted(noms)]
    return noms


def lister_images():
    """Retourne une liste triée de (photo_d_origine, image, label)."""
    images = []
    for split in ["train", "valid", "test"]:
        dossier = RAW / split / "images"
        if not dossier.exists():
            continue
        for f in sorted(dossier.iterdir()):
            if f.suffix.lower() in EXTS:
                label = RAW / split / "labels" / (f.stem + ".txt")
                origine = f.stem.split(".rf.")[0]
                images.append((origine, f, label))
    images.sort(key=lambda x: (x[0], x[1].name))
    return images


def convertir_label(label, single_class):
    """Lit un label YOLO et renvoie des lignes 'classe x y w h' (les polygones deviennent des boxes)."""
    lignes = []
    if not label.exists():
        return lignes
    for ligne in label.read_text().splitlines():
        v = ligne.split()
        if len(v) < 5:
            continue
        c, nums = int(v[0]), [float(x) for x in v[1:]]
        if len(nums) == 4:
            x, y, w, h = nums
        else:
            xs, ys = nums[0::2], nums[1::2]
            x, y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            w, h = max(xs) - min(xs), max(ys) - min(ys)
        c = 0 if single_class else c
        lignes.append(f"{c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
    return lignes


def decouper_par_groupe(images, seed, split):
    origines = sorted({o for o, _, _ in images})
    random.Random(seed).shuffle(origines)
    n_train = round(len(origines) * split["train"])
    n_val = round(len(origines) * split["val"])
    groupe = {}
    for i, o in enumerate(origines):
        groupe[o] = "train" if i < n_train else "val" if i < n_train + n_val else "test"
    return groupe


def main():
    seed, p = lire_params()
    noms = lire_noms_classes()
    images = lister_images()
    groupe = decouper_par_groupe(images, seed, p["split"])

    if OUT.exists():
        shutil.rmtree(OUT)
    compte = {s: {"images": 0, "boxes": 0, "photos": set()} for s in ["train", "val", "test"]}
    for origine, f, label in images:
        s = groupe[origine]
        (OUT / "images" / s).mkdir(parents=True, exist_ok=True)
        (OUT / "labels" / s).mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, OUT / "images" / s / f.name)
        lignes = convertir_label(label, p["single_class"])
        (OUT / "labels" / s / (f.stem + ".txt")).write_text("\n".join(lignes), encoding="utf-8")
        compte[s]["images"] += 1
        compte[s]["boxes"] += len(lignes)
        compte[s]["photos"].add(origine)

    # Vérification : aucune photo d'origine dans deux splits
    vus = [o for s in compte for o in compte[s]["photos"]]
    assert len(vus) == len(set(vus)), "Fuite : une photo est dans plusieurs splits"

    classes = ["waste"] if p["single_class"] else noms
    data_yaml = {
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": len(classes),
        "names": classes,
    }
    (OUT / "data.yaml").write_text(yaml.safe_dump(data_yaml, sort_keys=False), encoding="utf-8")

    resume = {"photos_origine": len(groupe), "images": len(images), "classes": len(classes)}
    for s, c in compte.items():
        resume[f"{s}_photos"] = len(c["photos"])
        resume[f"{s}_images"] = c["images"]
        resume[f"{s}_boxes"] = c["boxes"]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(resume, indent=2), encoding="utf-8")

    print(f"{len(images)} images, {len(groupe)} photos d'origine, classes : {classes}")
    for s, c in compte.items():
        print(f"{s:5s} : {len(c['photos'])} photos, {c['images']} images, {c['boxes']} boxes")
    print("Aucune fuite entre splits. Résumé écrit dans", REPORT.relative_to(ROOT))


if __name__ == "__main__":
    main()
