import json
from typing import Annotated

from fastapi import APIRouter, Depends

from app.inference import get_pipeline
from app.schemas import InfoResponse
from waste_core.bins import CLASSES, MATIERES_FR, POUBELLES
from waste_core.pipeline import ROOT

router = APIRouter()
RAPPORTS = ROOT / "ml" / "reports"


def lire_rapport(nom: str, cles: list[str]) -> dict[str, float]:
    """Lit quelques scores dans un rapport ml/reports/*.json (écrit par l'entraînement)."""
    chemin = RAPPORTS / nom
    if not chemin.exists():
        return {}
    rapport = json.loads(chemin.read_text(encoding="utf-8"))
    return {cle: rapport[cle] for cle in cles if cle in rapport}


@router.get("/info", response_model=InfoResponse)
def info(pipeline: Annotated[object, Depends(get_pipeline)]):
    return {
        "versions": pipeline.versions,
        "scores": {
            "classifieur": lire_rapport("cls_resnet18_ft.json", ["val_accuracy", "val_f1_macro"]),
            "detecteur": lire_rapport(
                "yolo_yolov8n_640.json", ["val_mAP50", "val_precision", "val_recall"]
            ),
        },
        "classes": [
            {"matiere": c, "matiere_fr": MATIERES_FR[c], "poubelle": POUBELLES[c]} for c in CLASSES
        ],
    }
