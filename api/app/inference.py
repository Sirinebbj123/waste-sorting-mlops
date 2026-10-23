"""Chargement unique du pipeline (YOLO + ResNet18) pour toute la vie de l'API."""

import os
from functools import lru_cache

from waste_core.pipeline import CLS_DEFAUT, YOLO_DEFAUT, WastePipeline


@lru_cache(maxsize=1)
def get_pipeline() -> WastePipeline:
    # lru_cache : les modèles sont chargés à la première requête, puis réutilisés.
    # Les chemins peuvent être changés par variables d'environnement (utile pour Docker).
    return WastePipeline(
        yolo_path=os.environ.get("MODEL_YOLO", YOLO_DEFAUT),
        cls_path=os.environ.get("MODEL_CLS", CLS_DEFAUT),
        seuil=float(os.environ.get("SEUIL_DETECTION", "0.25")),
    )
