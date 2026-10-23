from fastapi.testclient import TestClient

from app.main import app


def test_page_de_demo() -> None:
    reponse = TestClient(app).get("/")
    assert reponse.status_code == 200
    assert "text/html" in reponse.headers["content-type"]
    assert "Tri des déchets" in reponse.text