
# Journal de bord · Syrine
## 2026-10-23 · Tâche 5 : étape train_yolo, .dvcignore, versions fixées
- Fait : train_yolo dans dvc.yaml, poids Colab enregistrés avec dvc commit, .dvcignore (*.cache), requirements.txt avec versions
- Compris : pourquoi YOLO « modifiait » les données (fichiers .cache), dvc commit vs dvc repro
- Bloqué : ...
## 2026-10-14 · Tâche 4B : YOLOv8n 640 px sur Colab
- Fait : train_yolo.py accepte --config, réglages train_yolo_640.yaml, notebook Colab
  (code depuis GitHub, données depuis DagsHub avec dvc pull, run envoyé sur MLflow DagsHub)
- Résultats sur val :
  | Run | imgsz | Époques | mAP50 | mAP50-95 | Précision | Rappel | Durée |
  |---|---|---|---|---|---|---|---|
  | yolov8n_416 (CPU, tâche 3) | 416 | 10 | 0.8965 | 0.548 | 0.9464 | 0.7881 | 53.5 min |
  | yolov8n_640 (GPU T4, Colab) | 640 | ... | 0.8984 | 0.5648 | 0.9288 | 0.8207 | 13.7 min |
- Gain : mAP50 +0.19 point (quasi stable), mAP50-95 +1.68 point, rappel +3.26 points, précision -1.76 point
- Lecture : en 640 px, le modèle trouve plus de déchets (rappel 0.79 → 0.82) et ses boîtes sont mieux placées
  (mAP50-95 en hausse), au prix d'un peu plus de fausses détections (précision 0.95 → 0.93).
  mAP50 était déjà très haut (0.90) : la marge de progrès est surtout sur la précision des boîtes.
- Early stopping : arrêt à l'époque ... sur 30 (ou : les 30 époques ont été faites)
- Temps : 13.7 min sur GPU T4 contre 53.5 min sur CPU, soit environ 4 fois plus rapide
  avec 3 fois plus d'époques et des images plus grandes
- Compris : token hors Git, dvc pull sur une autre machine, MLflow distant sur DagsHub
- Bloqué : ...
## 2026-10-.. · Tâche 4A : données sur DagsHub
- Fait : dépôt DagsHub relié à GitHub, remote DVC "origin", dvc push (... fichiers), Maryem invitée
- Compris : .dvc/config (adresse, dans Git) et .dvc/config.local (token, hors Git)
- Bloqué : ...
## 2026-10-09 · Tâche 3 : baseline du détecteur
- Fait : script train_yolo.py avec suivi MLflow ; YOLOv8n fine-tuné sur une classe "waste", imgsz 416, 10 époques sur CPU (53,5 min). Sur val : mAP@0.5 0,896, mAP@0.5:0.95 0,548, précision 0,946, rappel 0,788
- Compris : la précision mesure si les déchets détectés sont vrais, le rappel si on n'en oublie pas ; ici le modèle oublie environ 1 déchet sur 5. Le mAP@0.5:0.95 plus bas montre que les boxes ne sont pas encore très précises. Pas de sur-apprentissage (val_box_loss proche de train_box_loss)
- Bloqué : rien ; l'entraînement sur CPU est long, les prochains essais (640 px, plus d'époques) se feront sur Colab ou Kaggle
Une entrée par séance : fait / compris / bloqué. La plus récente en haut.

## 2026-10-09 · Tâche 2 : préparation des données
- Fait : script prepare_roboflow.py, étape DVC prepare_roboflow, tag v0.1-data
- Compris : pourquoi garder les copies .rf. d'une même photo dans le même split
- Bloqué : 0 image trouvée, car dataset-resized était un sous-dossier (résolu)

## 2026-10-09 · Tâche 1 : exploration des données
- Fait : notebook 01_eda_roboflow, résumé docs/eda-roboflow.md
- Compris : ...
- Bloqué : ...