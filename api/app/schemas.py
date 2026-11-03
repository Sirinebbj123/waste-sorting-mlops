"""Schémas Pydantic : le format exact des réponses de l'API (affiché dans /docs)."""

from pydantic import BaseModel, Field


class Detection(BaseModel):
    boite: list[float] = Field(description="[x1, y1, x2, y2] en pixels de l'image envoyée")
    confiance_detection: float | None = Field(
        description="Confiance de YOLO (null si l'image entière a été classée)"
    )
    matiere: str = Field(examples=["plastic"])
    matiere_fr: str = Field(examples=["plastique"])
    confiance_matiere: float = Field(ge=0, le=1)
    poubelle: str = Field(examples=["jaune"])


class PredictResponse(BaseModel):
    largeur: int
    hauteur: int
    mode: str = Field(description="'detection', ou 'image_entiere' si YOLO n'a rien trouvé")
    nb_dechets: int
    detections: list[Detection]
    versions: dict[str, str] = Field(description="Fichiers de modèles et début de leur md5 DVC")
    duree_ms: float
class Classe(BaseModel):
    matiere: str
    matiere_fr: str
    poubelle: str


class InfoResponse(BaseModel):
    versions: dict[str, str] = Field(description="Fichiers de modèles et début de leur md5 DVC")
    scores: dict[str, dict[str, float]] = Field(
        description="Scores sur le jeu de validation, lus dans ml/reports/*.json"
    )
    classes: list[Classe]