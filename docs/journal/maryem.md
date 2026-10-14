# Journal de bord · Maryem
## 2026-10-14 · Tâche 4 : ResNet18 en fine-tuning partiel
- Fait : données récupérées depuis DagsHub (dvc pull, data_version fd7e5248), resnet18 refait (val F1 macro 0.750, acc 0.767, 6.4 min), resnet18_ft (val F1 macro 0.894, acc 0.905, 19 min), runs comparés sur MLflow DagsHub
- Résultats : +14.4 points de F1 macro pour +12.6 min d'entraînement. Trash : F1 0.634 → ? (classe la plus faible de la baseline). val_loss en fin d'entraînement : ? (si elle remonte, 5 époques suffiraient)
- Compris : feature extraction (seule la dernière couche apprend, 3 078 paramètres) vs fine-tuning (une partie du réseau réentraînée, 8.4 M paramètres) ; deux vitesses d'apprentissage : lr 0.001 pour la tête, backbone_lr 0.0001 pour le réseau pré-entraîné, pour ne pas abîmer ce qu'il sait déjà
- Remarques : léger sur-apprentissage (train_loss 0.048) ; le run ft a été lancé sans commit de la config (git_commit 5bef81b = commit de la baseline), à corriger : committer avant chaque entraînement
- Bloqué : rien
## 2026-10-.. · Tâche 3 : baselines du classifieur
- Fait : train_cls.py, petit CNN (val F1 ...), ResNet18 gelé (val F1 ...), suivi MLflow
- Compris : ...
- Bloqué : ...

Une entrée par séance : fait / compris / bloqué. La plus récente en haut.

## 2026-10-09 · Tâche 2 : préparation des données
- Fait : script prepare_trashnet.py, création de params.yaml et dvc.yaml, étape DVC prepare_trashnet (retrait des doublons, découpage stratifié 70/15/15, graine 42)
- Compris : dvc repro relance seulement ce qui a changé ; dvc.lock garde les empreintes, donc Syrine obtient exactement le même découpage sur son PC
- Bloqué : ...

## 2026-10-09 · Tâche 1 : exploration des données
- Fait : notebook 01_eda_trashnet, résumé docs/eda-trashnet.md (2527 images, 6 classes, 512x384)
- Compris : la classe trash est rare (137 images, 5,4 %) donc il faudra regarder le F1 par classe ; 56 % des images ont un fond blanc, risque que le CNN apprenne le fond ; 6 images concernées par des doublons exacts
- Bloqué : ...