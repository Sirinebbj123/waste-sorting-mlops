# Journal de bord · Maryem
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