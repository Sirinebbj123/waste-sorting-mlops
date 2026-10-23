"""Test du vrai pipeline : il faut les modèles en local (dvc pull -j 2 train_cls train_yolo).

Sans les modèles (par exemple dans la CI GitHub), ce test est sauté et pytest affiche "s".
"""

import pytest
from PIL import Image

from waste_core.pipeline import CLS_DEFAUT, YOLO_DEFAUT

modeles_absents = not (YOLO_DEFAUT.exists() and CLS_DEFAUT.exists())
RAISON = "modèles absents : lance dvc pull -j 2 train_cls train_yolo"


@pytest.mark.skipif(modeles_absents, reason=RAISON)
def test_pipeline_sur_une_image():
    from waste_core.pipeline import WastePipeline

    resultat = WastePipeline().predire(Image.new("RGB", (320, 240), "white"))

    assert resultat["largeur"] == 320 and resultat["hauteur"] == 240
    assert resultat["mode"] in ("detection", "image_entiere")
    assert len(resultat["detections"]) >= 1
    for d in resultat["detections"]:
        assert len(d["boite"]) == 4
        assert d["poubelle"] in ("jaune", "verte", "grise")
        assert 0 <= d["confiance_matiere"] <= 1
