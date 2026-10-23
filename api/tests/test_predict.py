"""Tests de /predict avec un faux pipeline : rapides, et sans les vrais modèles.

On teste ici l'API (format de la réponse, gestion des erreurs), pas la qualité des modèles :
celle-ci est mesurée par DVC et MLflow (ml/reports/*.json).
"""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.inference import get_pipeline
from app.main import app


class FauxPipeline:
    def predire(self, image):
        return {
            "largeur": image.width,
            "hauteur": image.height,
            "mode": "detection",
            "detections": [
                {
                    "boite": [10.0, 20.0, 110.0, 220.0],
                    "confiance_detection": 0.9,
                    "matiere": "plastic",
                    "matiere_fr": "plastique",
                    "confiance_matiere": 0.8,
                    "poubelle": "jaune",
                }
            ],
            "versions": {"detecteur": "faux", "classifieur": "faux"},
        }


@pytest.fixture
def client():
    app.dependency_overrides[get_pipeline] = FauxPipeline  # remplace le vrai pipeline
    yield TestClient(app)
    app.dependency_overrides.clear()


def image_png(largeur=200, hauteur=300):
    tampon = io.BytesIO()
    Image.new("RGB", (largeur, hauteur), "green").save(tampon, format="PNG")
    return tampon.getvalue()


def test_predict_renvoie_les_dechets(client):
    reponse = client.post("/predict", files={"fichier": ("photo.png", image_png(), "image/png")})

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["largeur"] == 200 and corps["hauteur"] == 300
    assert corps["nb_dechets"] == 1
    assert corps["detections"][0]["poubelle"] == "jaune"
    assert corps["duree_ms"] >= 0


def test_predict_refuse_un_fichier_qui_n_est_pas_une_image(client):
    reponse = client.post("/predict", files={"fichier": ("note.txt", b"bonjour", "text/plain")})
    assert reponse.status_code == 400


def test_predict_refuse_un_fichier_vide(client):
    reponse = client.post("/predict", files={"fichier": ("vide.png", b"", "image/png")})
    assert reponse.status_code == 400


def test_predict_sans_fichier(client):
    assert client.post("/predict").status_code == 422
