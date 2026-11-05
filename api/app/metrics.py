"""Métriques Prometheus de l'API EcoTri, lues sur /metrics.

Deux familles :
- le fonctionnement de l'API : nombre de requêtes, codes de réponse, temps de réponse ;
- le métier et le modèle : déchets trouvés par poubelle, confiance du classifieur,
  temps d'inférence, version des modèles. C'est ce qui permet de voir une dérive
  (par exemple la confiance qui baisse) sans regarder les photos une par une.
"""

from prometheus_client import Counter, Gauge, Histogram

REQUETES = Counter(
    "ecotri_requetes",
    "Requêtes HTTP reçues par l'API",
    ["methode", "route", "statut"],
)
DUREE_REQUETE = Histogram(
    "ecotri_duree_requete_secondes",
    "Temps de réponse de l'API, en secondes",
    ["route"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)
PREDICTIONS = Counter(
    "ecotri_predictions",
    "Photos analysées, par mode (detection ou image_entiere)",
    ["mode"],
)
DECHETS = Counter(
    "ecotri_dechets",
    "Déchets trouvés, par matière et par poubelle",
    ["matiere", "poubelle"],
)
CONFIANCE = Histogram(
    "ecotri_confiance_matiere",
    "Confiance du classifieur pour chaque déchet (0 à 1)",
    buckets=(0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0),
)
DUREE_INFERENCE = Histogram(
    "ecotri_duree_inference_secondes",
    "Temps des modèles (YOLO + ResNet18) pour une photo, en secondes",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)
MODELES = Gauge(
    "ecotri_modele_info",
    "Version des modèles en service (fichier et md5 DVC) ; la valeur vaut toujours 1",
    ["detecteur", "classifieur"],
)


def enregistrer_prediction(resultat: dict, duree_s: float) -> None:
    """Met à jour les métriques métier après une prédiction."""
    PREDICTIONS.labels(mode=resultat["mode"]).inc()
    DUREE_INFERENCE.observe(duree_s)
    for dechet in resultat["detections"]:
        DECHETS.labels(matiere=dechet["matiere"], poubelle=dechet["poubelle"]).inc()
        CONFIANCE.observe(dechet["confiance_matiere"])
    versions = resultat.get("versions", {})
    MODELES.labels(
        detecteur=versions.get("detecteur", "?"),
        classifieur=versions.get("classifieur", "?"),
    ).set(1)