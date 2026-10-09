"""Prépare TrashNet pour le classifieur CNN.

Lit    : ml/data/raw/trashnet/<classe>/*.jpg
Écrit  : ml/data/processed/trashnet/{train,val,test}/<classe>/*.jpg
         ml/reports/trashnet_split.json (résumé, suivi comme métrique DVC)

Étapes : 1) liste les images (ignore .DS_Store et autres fichiers)
         2) retire les doublons exacts (même contenu)
         3) découpe chaque classe en train / val / test (stratifié, graine fixe)
         4) copie les images dans les dossiers de sortie
"""

import hashlib
import json
import random
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]  # dossier du projet
RAW = ROOT / "ml" / "data" / "raw" / "trashnet"
OUT = ROOT / "ml" / "data" / "processed" / "trashnet"
REPORT = ROOT / "ml" / "reports" / "trashnet_split.json"
EXTS = {".jpg", ".jpeg", ".png"}


def lire_params():
    params = yaml.safe_load((ROOT / "params.yaml").read_text(encoding="utf-8"))
    return params["seed"], params["trashnet"]["split"]


def lister_images():
    """Retourne une liste triée de (classe, chemin). Le tri rend le résultat identique sur tous les PC."""
    images = []
    for dossier in sorted(p for p in RAW.iterdir() if p.is_dir()):
        for f in sorted(dossier.iterdir()):
            if f.suffix.lower() in EXTS:
                images.append((dossier.name, f))
    return images


def retirer_doublons(images):
    """Garde une seule copie de chaque image identique.
    Si les copies sont dans des classes différentes, on les retire toutes (étiquette ambiguë)."""
    par_hash = {}
    for classe, f in images:
        h = hashlib.md5(f.read_bytes()).hexdigest()
        par_hash.setdefault(h, []).append((classe, f))

    gardees, retirees = [], []
    for copies in par_hash.values():
        if len({c for c, _ in copies}) > 1:
            retirees.extend(copies)
        else:
            gardees.append(copies[0])
            retirees.extend(copies[1:])
    gardees.sort(key=lambda x: (x[0], x[1].name))
    return gardees, retirees


def decouper(images, seed, split):
    """Découpage stratifié : chaque classe est coupée séparément avec les mêmes proportions."""
    rng = random.Random(seed)
    resultat = {"train": [], "val": [], "test": []}
    for classe in sorted({c for c, _ in images}):
        fichiers = [f for c, f in images if c == classe]
        rng.shuffle(fichiers)
        n_train = round(len(fichiers) * split["train"])
        n_val = round(len(fichiers) * split["val"])
        resultat["train"] += [(classe, f) for f in fichiers[:n_train]]
        resultat["val"] += [(classe, f) for f in fichiers[n_train:n_train + n_val]]
        resultat["test"] += [(classe, f) for f in fichiers[n_train + n_val:]]
    return resultat


def main():
    seed, split = lire_params()
    images = lister_images()
    gardees, retirees = retirer_doublons(images)
    decoupage = decouper(gardees, seed, split)

    if OUT.exists():
        shutil.rmtree(OUT)  # on repart de zéro à chaque exécution
    for nom_split, liste in decoupage.items():
        for classe, f in liste:
            dest = OUT / nom_split / classe
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest / f.name)

    resume = {
        "images_brutes": len(images),
        "doublons_retires": len(retirees),
        "images_gardees": len(gardees),
        **{f"{s}_total": len(l) for s, l in decoupage.items()},
        **{f"{s}_{c}": sum(1 for cc, _ in l if cc == c)
           for s, l in decoupage.items() for c in sorted({c for c, _ in gardees})},
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(resume, indent=2), encoding="utf-8")

    print(f"Images brutes : {len(images)}, doublons retirés : {len(retirees)}")
    for f in retirees:
        print("  retiré :", f[0], f[1].name)
    for s, l in decoupage.items():
        print(f"{s:5s} : {len(l)} images")
    print("Résumé écrit dans", REPORT.relative_to(ROOT))


if __name__ == "__main__":
    main()
