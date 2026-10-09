"""Fine-tune YOLOv8n sur le dataset Roboflow préparé (une classe "waste") et trace tout dans MLflow.

Utilisation (depuis la racine du projet, venv activé) :
    python ml/src/train/train_yolo.py

Lit    : ml/configs/train_yolo.yaml
         ml/data/processed/roboflow/  (produit par dvc repro)
Écrit  : ml/runs/<run_name>/          (sorties Ultralytics : poids, courbes, hors Git)
         ml/reports/yolo_<run_name>.json  (résultats sur val, dans Git)
         un run MLflow dans mlflow.db / mlruns/  (hors Git)

Le jeu de test n'est PAS utilisé ici : il est réservé à l'évaluation finale.
"""

import json
import subprocess
import time
from pathlib import Path

import mlflow
import pandas as pd
import yaml
from ultralytics import YOLO, settings

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "ml" / "configs" / "train_yolo.yaml"


def commit_git():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "inconnu"


def version_donnees(etape):
    lock = ROOT / "dvc.lock"
    if not lock.exists():
        return "inconnue"
    contenu = yaml.safe_load(lock.read_text(encoding="utf-8"))
    return contenu["stages"][etape]["outs"][0]["md5"]


def main():
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    data_yaml = (ROOT / cfg["data"]).resolve()  # chemin absolu : Ultralytics trouve les images à côté
    settings.update({"mlflow": False})  # on trace nous-mêmes, pour garder le contrôle

    mlflow.set_tracking_uri("sqlite:///" + (ROOT / "mlflow.db").as_posix())
    mlflow.set_experiment(cfg["experiment"])
    with mlflow.start_run(run_name=cfg["run_name"]):
        mlflow.set_tags({"git_commit": commit_git(),
                         "data_version": version_donnees("prepare_roboflow"),
                         "model_family": "yolov8"})
        mlflow.log_params({k: v for k, v in cfg.items() if k not in ("experiment",)})

        debut = time.time()
        modele = YOLO(cfg["model"])
        modele.train(
            data=str(data_yaml),
            imgsz=cfg["imgsz"],
            epochs=cfg["epochs"],
            batch=cfg["batch"],
            patience=cfg["patience"],
            workers=cfg["workers"],
            device=cfg["device"],
            seed=cfg["seed"],
            deterministic=True,
            project=str(ROOT / "ml" / "runs"),
            name=cfg["run_name"],
            exist_ok=True,
        )
        dossier = ROOT / "ml" / "runs" / cfg["run_name"]

        # Courbes époque par époque (results.csv écrit par Ultralytics)
        courbes = pd.read_csv(dossier / "results.csv")
        courbes.columns = [c.strip() for c in courbes.columns]
        for _, ligne in courbes.iterrows():
            epoque = int(ligne["epoch"])
            mlflow.log_metrics({
                "train_box_loss": ligne["train/box_loss"],
                "val_box_loss": ligne["val/box_loss"],
                "val_mAP50": ligne["metrics/mAP50(B)"],
                "val_mAP50_95": ligne["metrics/mAP50-95(B)"],
            }, step=epoque)

        # Évaluation du meilleur modèle sur val
        meilleur = YOLO(str(dossier / "weights" / "best.pt"))
        m = meilleur.val(data=str(data_yaml), split="val", imgsz=cfg["imgsz"], batch=cfg["batch"],
                         device=cfg["device"], workers=cfg["workers"],
                         project=str(ROOT / "ml" / "runs"), name=cfg["run_name"] + "_val", exist_ok=True)
        resultat = {
            "model": cfg["model"],
            "imgsz": cfg["imgsz"],
            "val_mAP50": round(float(m.box.map50), 4),
            "val_mAP50_95": round(float(m.box.map), 4),
            "val_precision": round(float(m.box.mp), 4),
            "val_recall": round(float(m.box.mr), 4),
            "train_minutes": round((time.time() - debut) / 60, 1),
        }
        mlflow.log_metrics({k: v for k, v in resultat.items() if k.startswith("val_") or k == "train_minutes"})

        rapports = ROOT / "ml" / "reports"
        rapports.mkdir(parents=True, exist_ok=True)
        chemin_json = rapports / f"yolo_{cfg['run_name']}.json"
        chemin_json.write_text(json.dumps(resultat, indent=2), encoding="utf-8")
        mlflow.log_artifact(str(chemin_json))
        for nom in ["results.png", "confusion_matrix.png", "BoxPR_curve.png", "PR_curve.png", "val_batch0_pred.jpg"]:
            for d in (dossier, ROOT / "ml" / "runs" / (cfg["run_name"] + "_val")):
                if (d / nom).exists():
                    mlflow.log_artifact(str(d / nom))
        mlflow.log_artifact(str(dossier / "weights" / "best.pt"))

    print(json.dumps(resultat, indent=2))
    print("Résultats écrits dans", chemin_json.relative_to(ROOT))


if __name__ == "__main__":
    main()
