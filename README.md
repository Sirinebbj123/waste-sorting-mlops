# Detection de dechets pour le tri selectif 
## Lancer l'API et la démo

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