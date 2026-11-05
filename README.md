# Detection de dechets pour le tri selectif 
## Lancer l'API et la démo
[![CI](https://github.com/Sirinebbj123/waste-sorting-mlops/actions/workflows/ci.yml/badge.svg)](https://github.com/Sirinebbj123/waste-sorting-mlops/actions/workflows/ci.yml)
[![CD](https://github.com/Sirinebbj123/waste-sorting-mlops/actions/workflows/cd.yml/badge.svg)](https://github.com/Sirinebbj123/waste-sorting-mlops/actions/workflows/cd.yml)

```powershell
.venv\Scripts\Activate.ps1
dvc pull -j 2 train_cls train_yolo      # récupère les deux modèles depuis DagsHub
python -m uvicorn app.main:app --app-dir api
```

- Démo : http://127.0.0.1:8000
- Documentation de l'API : http://127.0.0.1:8000/docs
- Tests : `pytest -v`

`POST /predict` (champ `fichier`) renvoie pour chaque déchet sa boîte, sa matière, sa poubelle
et la version des modèles (début du md5 DVC).

## Lancer avec Docker

Prérequis : Docker Desktop démarré, et les modèles récupérés avec DVC.

```powershell
dvc pull -j 2 train_cls train_yolo
docker compose up --build -d
```

- Application : http://127.0.0.1:8000
- Documentation de l'API : http://127.0.0.1:8000/docs
- État du conteneur : `docker compose ps` (doit afficher `healthy`)
- Journaux : `docker compose logs -f api`
- Arrêter : `docker compose down`

## CI/CD

| Workflow | Quand | Ce qu'il fait |
|---|---|---|
| [CI](.github/workflows/ci.yml) | chaque PR vers `main`, chaque fusion | `ruff`, `pytest`, `dvc pull`, `docker build`, test de fumée de l'image |
| [CD](.github/workflows/cd.yml) | chaque tag `v*` | build + test de fumée, publication sur ghcr.io, Release |

`main` est protégée : une PR ne peut être fusionnée que si la CI est verte et qu'une autre personne l'a approuvée.

Lancer la dernière version publiée, sans cloner le projet :
```bash
docker run --rm -p 8000:8000 ghcr.io/sirinebbj123/waste-sorting-mlops:latest
```
puis http://127.0.0.1:8000.

Les mêmes vérifications que la CI, sur son PC :
```bash
pip install -r api/requirements-test.txt
ruff check .
ruff format --check .
pytest
docker compose up --build -d
python scripts/smoke_test.py http://127.0.0.1:8000
```
## Monitoring (Prometheus et Grafana)

`docker compose up --build -d` lance l'API **et** son monitoring :

| Service | Adresse | Pour quoi faire |
|---|---|---|
| API + application | http://127.0.0.1:8000 | analyser des photos |
| Métriques brutes | http://127.0.0.1:8000/metrics | ce que lit Prometheus |
| Prometheus | http://127.0.0.1:9090 | requêtes PromQL, cibles, **alertes** |
| Grafana | http://127.0.0.1:3000 | le tableau de bord « EcoTri · Tri des déchets » |

Le tableau de bord s'ouvre directement (lecture seule). Pour le modifier : connexion `admin`,
mot de passe `admin` ou celui de la variable `GRAFANA_PASSWORD` (fichier `.env`, jamais commité).

Remplir le tableau de bord avec des photos :
```bash
python scripts/generer_trafic.py --dossier ml/data/processed/trashnet/test --nombre 60
```

Configuration : `monitoring/prometheus/` (collecte et alertes), `monitoring/grafana/`
(source de données et tableau de bord, chargés automatiquement). Choix expliqués dans
[docs/decisions/0004-monitoring.md](docs/decisions/0004-monitoring.md).