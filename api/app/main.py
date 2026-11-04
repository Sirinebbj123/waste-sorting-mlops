from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def page_demo():
    page = STATIC / "index.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="Page de démo absente")
    return FileResponse(page)
