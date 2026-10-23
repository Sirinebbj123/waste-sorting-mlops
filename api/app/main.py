from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.routers import predict

STATIC = Path(__file__).parent / "static"

app = FastAPI(
    title="Waste Sorting API",
    version="0.5.0",
    description="Envoie une photo, reçois les déchets détectés, leur matière et leur poubelle.",
)
app.include_router(predict.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def page_demo():
    page = STATIC / "index.html"
    if not page.exists():  # la page de démo arrive dans la PR de Maryem
        raise HTTPException(status_code=404, detail="Page de démo pas encore ajoutée")
    return FileResponse(page)
