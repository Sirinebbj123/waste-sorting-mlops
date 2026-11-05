"""Test de fumée : vérifie qu'une API EcoTri qui tourne (dans Docker) répond vraiment.

Utilisé par la CI après `docker run`, et utilisable sur vos PC :
    python scripts/smoke_test.py http://127.0.0.1:8000

Seulement la bibliothèque standard de Python : rien à installer.
"""

import json
import re
import struct
import sys
import time
import urllib.request
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def lire(url: str, donnees: bytes | None = None, entetes: dict | None = None) -> tuple[int, bytes]:
    requete = urllib.request.Request(url, data=donnees, headers=entetes or {})
    with urllib.request.urlopen(requete, timeout=60) as reponse:
        return reponse.status, reponse.read()


def attendre_api(base: str, delai_max: int = 120) -> None:
    """Attend que /health réponde (le chargement des modèles prend quelques secondes)."""
    fin = time.time() + delai_max
    while True:
        try:
            statut, corps = lire(f"{base}/health")
            if statut == 200 and json.loads(corps) == {"status": "ok"}:
                print("OK  /health")
                return
        except OSError:
            pass
        if time.time() > fin:
            sys.exit(f"ERREUR : /health ne répond pas après {delai_max} s")
        time.sleep(3)


def md5_dans_dvc_lock(nom_modele: str) -> str:
    """md5 du modèle noté par DVC dans dvc.lock (8 premiers caractères)."""
    texte = (ROOT / "dvc.lock").read_text(encoding="utf-8")
    trouve = re.search(rf"path: ml/models/{re.escape(nom_modele)}\s+hash: md5\s+md5: (\w+)", texte)
    if not trouve:
        sys.exit(f"ERREUR : {nom_modele} absent de dvc.lock")
    return trouve.group(1)[:8]


def verifier_info(base: str) -> None:
    """Les modèles dans l'image sont bien ceux versionnés par DVC (même md5)."""
    _, corps = lire(f"{base}/info")
    versions = json.loads(corps)["versions"]
    for role, texte in versions.items():
        nom, md5 = re.fullmatch(r"(\S+) \((\w+)\)", texte).groups()
        attendu = md5_dans_dvc_lock(nom)
        if md5 != attendu:
            sys.exit(f"ERREUR : {role} {nom} a le md5 {md5}, dvc.lock dit {attendu}")
        print(f"OK  /info  {role} = {nom} ({md5}), comme dans dvc.lock")


def image_png(largeur: int = 320, hauteur: int = 240) -> bytes:
    """Petite image PNG unie, fabriquée sans Pillow."""

    def bloc(type_: bytes, donnees: bytes) -> bytes:
        crc = zlib.crc32(type_ + donnees)
        return struct.pack(">I", len(donnees)) + type_ + donnees + struct.pack(">I", crc)

    ligne = b"\x00" + bytes([200, 200, 190]) * largeur
    entete = struct.pack(">IIBBBBB", largeur, hauteur, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + bloc(b"IHDR", entete)
        + bloc(b"IDAT", zlib.compress(ligne * hauteur))
        + bloc(b"IEND", b"")
    )


def verifier_predict(base: str) -> None:
    """Une vraie prédiction avec les vrais modèles."""
    frontiere = "----ecotri-smoke-test"
    corps = (
        (
            f"--{frontiere}\r\n"
            'Content-Disposition: form-data; name="fichier"; filename="test.png"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode()
        + image_png()
        + f"\r\n--{frontiere}--\r\n".encode()
    )
    entetes = {"Content-Type": f"multipart/form-data; boundary={frontiere}"}
    statut, reponse = lire(f"{base}/predict", corps, entetes)
    resultat = json.loads(reponse)
    if statut != 200 or resultat["largeur"] != 320 or "detections" not in resultat:
        sys.exit(f"ERREUR : /predict a répondu {statut} {resultat}")
    print(
        f"OK  /predict  mode={resultat['mode']}, {resultat['nb_dechets']} déchet(s), "
        f"{resultat['duree_ms']} ms"
    )


def verifier_metrics(base: str) -> None:
    """Prometheus pourra lire les métriques, et la prédiction ci-dessus y est comptée."""
    _, corps = lire(f"{base}/metrics")
    texte = corps.decode()
    if "ecotri_predictions_total" not in texte or "ecotri_modele_info" not in texte:
        sys.exit("ERREUR : /metrics ne contient pas les métriques EcoTri")
    print("OK  /metrics  (métriques Prometheus)")


def verifier_page(base: str) -> None:
    _, corps = lire(f"{base}/")
    if b"EcoTri" not in corps:
        sys.exit("ERREUR : la page d'accueil ne contient pas EcoTri")
    print("OK  /  (application web)")


if __name__ == "__main__":
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    attendre_api(base)
    verifier_info(base)
    verifier_predict(base)
    verifier_metrics(base)
    verifier_page(base)
    print("Test de fumée réussi")
