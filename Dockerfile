# Image de l'API EcoTri : FastAPI + YOLOv8n + ResNet18, sur CPU
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    YOLO_CONFIG_DIR=/tmp/Ultralytics

WORKDIR /app

# 1. PyTorch en version CPU : bien plus léger que la version GPU, inutile ici
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
RUN pip install --index-url ${TORCH_INDEX} torch==2.14.1 torchvision==0.29.1

# 2. Les autres dépendances (couche gardée en cache tant que le fichier ne change pas).
#    Ultralytics installe OpenCV "normal", qui a besoin d'un écran (libGL) : on le remplace
#    par la version "headless" (sans écran), qui marche dans un conteneur sans rien ajouter.
COPY api/requirements.txt api/requirements.txt
RUN pip install -r api/requirements.txt \
    && pip uninstall -y opencv-python \
    && pip install --force-reinstall --no-deps opencv-python-headless==5.0.0.93

# 3. Le code, les scores et les deux modèles suivis par DVC (dvc pull avant le build)
COPY waste_core/ waste_core/
COPY api/app/ api/app/
COPY ml/reports/ ml/reports/
COPY ml/models/cls_resnet18_ft.pt ml/models/yolo_yolov8n_640.pt ml/models/

# 4. On ne tourne pas en root
RUN useradd --create-home ecotri
USER ecotri

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "api", "--host", "0.0.0.0", "--port", "8000"]