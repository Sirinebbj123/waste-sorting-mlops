# Journal de bord · Syrine
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