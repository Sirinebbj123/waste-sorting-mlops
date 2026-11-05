import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.metrics import DUREE_REQUETE, REQUETES
from app.routers import info, predict

STATIC = Path(__file__).parent / "static"

app = FastAPI(
    title="Waste Sorting API",
    version="0.6.0",
    description="Envoie une photo, reçois les déchets détectés, leur matière et leur poubelle.",
)
app.include_router(predict.router)
app.include_router(info.router)
# Fichiers de l'application web (style.css, app.js...) servis sur /static/...
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def mesurer(request: Request, call_next):
    """Compte chaque requête et mesure son temps de réponse (sauf /metrics lui-même)."""
    debut = time.perf_counter()
    reponse = await call_next(request)
    route = request.scope.get("route")
    # Le modèle de route (/predict, /static...) et pas l'adresse exacte : peu d'étiquettes
    chemin = getattr(route, "path", "autre")
    if chemin != "/metrics":
        REQUETES.labels(request.method, chemin, str(reponse.status_code)).inc()
        DUREE_REQUETE.labels(chemin).observe(time.perf_counter() - debut)
    return reponse


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Les métriques au format texte de Prometheus (lu toutes les 5 s par Prometheus)."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def page_demo():
    page = STATIC / "index.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="Page de démo absente")
    return FileResponse(page)
