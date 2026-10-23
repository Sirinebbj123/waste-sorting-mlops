"""Traduction d'une matière (classe du classifieur) en poubelle de tri."""

# Ordre alphabétique : c'est l'ordre des dossiers de TrashNet, donc l'ordre des sorties
# du classifieur (torchvision ImageFolder trie les noms de dossiers).
CLASSES = ["cardboard", "glass", "metal", "paper", "plastic", "trash"]

MATIERES_FR = {
    "cardboard": "carton",
    "glass": "verre",
    "metal": "métal",
    "paper": "papier",
    "plastic": "plastique",
    "trash": "ordures",
}

# Consignes de tri en France : bac jaune (emballages et papiers), bac vert (verre),
# bac gris (ordures ménagères)
POUBELLES = {
    "cardboard": "jaune",
    "paper": "jaune",
    "plastic": "jaune",
    "metal": "jaune",
    "glass": "verte",
    "trash": "grise",
}


def poubelle(matiere: str) -> str:
    """Renvoie la couleur de la poubelle pour une matière ('cardboard', 'glass'...)."""
    if matiere not in POUBELLES:
        raise ValueError(f"Matière inconnue : {matiere}")
    return POUBELLES[matiere]
