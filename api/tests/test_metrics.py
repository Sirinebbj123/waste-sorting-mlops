"""Tests de /metrics : les compteurs bougent quand on utilise l'API."""

import io

from fastapi.testclient import TestClient
from PIL import Image
from prometheus_client import REGISTRY

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
                    "boite": [0.0, 0.0, 10.0, 10.0],
                    "confiance_detection": 0.9,
                    "matiere": "glass",
                    "matiere_fr": "verre",
                    "confiance_matiere": 0.85,
                    "poubelle": "verte",
                }
            ],
            "versions": {"detecteur": "yolo.pt (aaaa1111)", "classifieur": "cls.pt (bbbb2222)"},
        }


def valeur(nom: str, **etiquettes: str) -> float:
    """Valeur actuelle d'une métrique (0 si elle n'existe pas encore)."""
    return REGISTRY.get_sample_value(nom, etiquettes) or 0.0


def image_png() -> bytes:
    tampon = io.BytesIO()
    Image.new("RGB", (64, 64), "white").save(tampon, format="PNG")
    return tampon.getvalue()


def test_metrics_format_prometheus() -> None:
    reponse = TestClient(app).get("/metrics")

    assert reponse.status_code == 200
    assert reponse.headers["content-type"].startswith("text/plain")
    assert "ecotri_requetes_total" in reponse.text


def test_health_est_compte() -> None:
    avant = valeur("ecotri_requetes_total", methode="GET", route="/health", statut="200")
    TestClient(app).get("/health")
    apres = valeur("ecotri_requetes_total", methode="GET", route="/health", statut="200")

    assert apres == avant + 1


def test_prediction_met_a_jour_les_metriques_metier() -> None:
    app.dependency_overrides[get_pipeline] = FauxPipeline
    try:
        avant = valeur("ecotri_dechets_total", matiere="glass", poubelle="verte")
        reponse = TestClient(app).post(
            "/predict", files={"fichier": ("photo.png", image_png(), "image/png")}
        )
    finally:
        app.dependency_overrides.clear()

    assert reponse.status_code == 200
    assert valeur("ecotri_dechets_total", matiere="glass", poubelle="verte") == avant + 1
    assert valeur("ecotri_predictions_total", mode="detection") >= 1
    assert valeur("ecotri_confiance_matiere_count") >= 1
    modele = {"detecteur": "yolo.pt (aaaa1111)", "classifieur": "cls.pt (bbbb2222)"}
    assert valeur("ecotri_modele_info", **modele) == 1


def test_metrics_ne_se_compte_pas_lui_meme() -> None:
    client = TestClient(app)
    client.get("/metrics")
    client.get("/metrics")

    assert valeur("ecotri_requetes_total", methode="GET", route="/metrics", statut="200") == 0