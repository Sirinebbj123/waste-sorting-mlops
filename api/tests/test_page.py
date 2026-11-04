from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_page_de_demo() -> None:
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert "text/html" in reponse.headers["content-type"]
    assert "Tri des déchets" in reponse.text


def test_fichiers_de_l_application() -> None:
    css = client.get("/static/style.css")
    js = client.get("/static/app.js")
    assert css.status_code == 200 and "text/css" in css.headers["content-type"]
    assert js.status_code == 200 and "/predict" in js.text
