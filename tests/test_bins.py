import pytest

from waste_core.bins import CLASSES, MATIERES_FR, POUBELLES, poubelle


def test_chaque_classe_a_une_poubelle_et_un_nom_francais():
    for matiere in CLASSES:
        assert matiere in POUBELLES
        assert matiere in MATIERES_FR


def test_classes_dans_l_ordre_de_imagefolder():
    # Le classifieur sort les classes dans l'ordre alphabétique des dossiers TrashNet
    assert CLASSES == sorted(CLASSES)
    assert len(CLASSES) == 6


@pytest.mark.parametrize(
    "matiere, attendu",
    [("glass", "verte"), ("trash", "grise"), ("plastic", "jaune"), ("paper", "jaune")],
)
def test_poubelle(matiere, attendu):
    assert poubelle(matiere) == attendu


def test_matiere_inconnue():
    with pytest.raises(ValueError):
        poubelle("bois")
