FROM docker.m.daocloud.io/library/python:3.12-slim-bookworm

USER root

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cu121 \
    torch==2.5.1 torchvision==0.20.1

RUN pip install --no-cache-dir \
    transformers==4.57.1 \
    Pillow==12.1.1 \
    matplotlib==3.10.8 \
    einops==0.8.2 \
    addict==2.4.0 \
    easydict==1.13 \
    pymupdf==1.27.2.2 \
    psutil==7.2.2 \
    accelerate \
    huggingface_hub \
    safetensors \
    tqdm \
    numpy \
    requests

WORKDIR /app
COPY run_ocr.py /app/run_ocr.py
