import io
import time
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image

from app.inference import get_pipeline
from app.schemas import PredictResponse

router = APIRouter()
TAILLE_MAX = 10 * 1024 * 1024  # 10 Mo


@router.post("/predict", response_model=PredictResponse)
async def predict(
    fichier: Annotated[UploadFile, File(description="Photo JPG ou PNG")],
    pipeline: Annotated[object, Depends(get_pipeline)],
):
    contenu = await fichier.read()
    if not contenu:
        raise HTTPException(status_code=400, detail="Fichier vide")
    if len(contenu) > TAILLE_MAX:
        raise HTTPException(status_code=413, detail="Image trop lourde (10 Mo maximum)")
    try:
        image = Image.open(io.BytesIO(contenu))
        image.load()
    except Exception:
        # Exception large : Ultralytics modifie Image.open et peut lever d'autres erreurs
        raise HTTPException(status_code=400, detail="Le fichier n'est pas une image") from None

    debut = time.perf_counter()
    resultat = pipeline.predire(image)
    duree_ms = round((time.perf_counter() - debut) * 1000, 1)
    return {**resultat, "nb_dechets": len(resultat["detections"]), "duree_ms": duree_ms}
