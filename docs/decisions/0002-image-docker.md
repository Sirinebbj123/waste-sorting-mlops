# 0002 · Image Docker de l'API

- Statut : accepté
- Date : 2026-11-04

## Contexte
L'application (API FastAPI + page EcoTri) doit se lancer sur n'importe quel PC avec une seule
commande, puis être construite et publiée par la CI/CD (tâche 9).

## Décisions
1. **Une seule image** : FastAPI sert à la fois l'API et l'application web (`/static`).
2. **PyTorch CPU** (index `download.pytorch.org/whl/cpu`) : la version GPU ajoute plusieurs Go
   de bibliothèques CUDA inutiles, nos PC et la CI n'ont pas de GPU.
3. **OpenCV headless** à la place d'OpenCV : pas besoin de bibliothèques d'affichage (libGL).
4. **Les deux modèles sont copiés dans l'image** (après `dvc pull`) : l'image est autonome,
   et sa version de modèle est figée (md5 visible dans `/info`).
5. **`.dockerignore`** : ni données, ni `.venv`, ni secrets (`.env`, `.dvc/config.local`).
6. **Utilisateur non root** et **healthcheck** sur `/health`.

## Conséquences
- Il faut faire `dvc pull -j 2 train_cls train_yolo` avant `docker build`.
- Changer de modèle = reconstruire l'image (c'est voulu : une image = une version de modèle).
- La CI devra récupérer les modèles depuis DagsHub avant de construire l'image (tâche 9).