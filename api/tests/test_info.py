from fastapi.testclient import TestClient

from app.inference import get_pipeline
from app.main import app


class FauxPipeline:
    versions = {"detecteur": "yolo.pt (aaaa1111)", "classifieur": "cls.pt (bbbb2222)"}


def test_info() -> None:
    app.dependency_overrides[get_pipeline] = FauxPipeline
    try:
        reponse = TestClient(app).get("/info")
    finally:
        app.dependency_overrides.clear()

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["versions"]["detecteur"] == "yolo.pt (aaaa1111)"
    assert set(corps["scores"]) == {"classifieur", "detecteur"}
    assert len(corps["classes"]) == 6
    assert {c["poubelle"] for c in corps["classes"]} == {"jaune", "verte", "grise"}