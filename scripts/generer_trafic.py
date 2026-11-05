"""Envoie des photos à l'API pour remplir le tableau de bord Grafana (démo).

    python scripts/generer_trafic.py                        # 30 images de test
    python scripts/generer_trafic.py --dossier C:\\photos    # vos propres photos
    python scripts/generer_trafic.py --nombre 100 --pause 0.5

Envoie aussi quelques fichiers qui ne sont pas des images, pour voir les erreurs 400
dans Grafana. Seulement la bibliothèque standard de Python : rien à installer.
"""

import argparse
import itertools
import json
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from smoke_test import image_png

EXTENSIONS = {".jpg", ".jpeg", ".png"}


def envoyer(base: str, nom: str, contenu: bytes, type_mime: str) -> tuple[int, dict]:
    frontiere = "----ecotri-trafic"
    corps = (
        (
            f"--{frontiere}\r\n"
            f'Content-Disposition: form-data; name="fichier"; filename="{nom}"\r\n'
            f"Content-Type: {type_mime}\r\n\r\n"
        ).encode()
        + contenu
        + f"\r\n--{frontiere}--\r\n".encode()
    )
    requete = urllib.request.Request(
        f"{base}/predict",
        data=corps,
        headers={"Content-Type": f"multipart/form-data; boundary={frontiere}"},
    )
    try:
        with urllib.request.urlopen(requete, timeout=60) as reponse:
            return reponse.status, json.loads(reponse.read())
    except urllib.error.HTTPError as erreur:
        return erreur.code, {}


def photos(dossier: str | None) -> list[tuple[str, bytes]]:
    if dossier:
        fichiers = [p for p in Path(dossier).rglob("*") if p.suffix.lower() in EXTENSIONS]
        if not fichiers:
            sys.exit(f"Aucune photo .jpg/.png dans {dossier}")
        return [(p.name, p.read_bytes()) for p in fichiers]
    # Sans dossier : petites images de couleurs différentes
    return [(f"test_{i}.png", image_png(160 + 40 * i, 120 + 30 * i)) for i in range(5)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--dossier", help="dossier de photos (sinon images de test)")
    parser.add_argument("--nombre", type=int, default=30, help="nombre d'envois")
    parser.add_argument("--pause", type=float, default=1.0, help="secondes entre deux envois")
    args = parser.parse_args()

    liste = photos(args.dossier)
    random.shuffle(liste)
    for i, (nom, contenu) in zip(range(1, args.nombre + 1), itertools.cycle(liste), strict=False):
        if i % 10 == 0:  # de temps en temps, un fichier qui n'est pas une image
            statut, _ = envoyer(args.url, "notes.txt", b"pas une image", "text/plain")
            print(f"{i:>3}  notes.txt  -> {statut} (erreur voulue)")
            continue
        statut, resultat = envoyer(args.url, nom, contenu, "image/jpeg")
        poubelles = [d["poubelle"] for d in resultat.get("detections", [])]
        print(f"{i:>3}  {nom}  -> {statut}  {poubelles}")
        time.sleep(args.pause)
    print("Terminé : regarde le tableau de bord sur http://127.0.0.1:3000")


if __name__ == "__main__":
    main()
