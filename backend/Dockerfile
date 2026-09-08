# EvalAgent SENA — imagen de la API
#
# Instala Piper y su voz en español (T-012 / ADR-005). Es lo que permite que el
# agente hable en Linux: la v1 dependía del comando `say` de macOS y era muda
# fuera de él.

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg: decodifica el audio del navegador (webm/ogg/mp4) para Whisper.
# espeak-ng: motor TTS de reserva.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        espeak-ng \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- Piper TTS -------------------------------------------------------------
ARG PIPER_VERSION=2023.11.14-2
ARG VOZ=es_ES-davefx-medium
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
        amd64) piper_arch=x86_64 ;; \
        arm64) piper_arch=aarch64 ;; \
        *) echo "Arquitectura no soportada por Piper: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/piper.tar.gz \
        "https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/piper_linux_${piper_arch}.tar.gz"; \
    tar -xzf /tmp/piper.tar.gz -C /opt; \
    ln -s /opt/piper/piper /usr/local/bin/piper; \
    rm /tmp/piper.tar.gz

RUN mkdir -p /app/voces && \
    curl -fsSL -o /app/voces/${VOZ}.onnx \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/${VOZ}.onnx" && \
    curl -fsSL -o /app/voces/${VOZ}.onnx.json \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/${VOZ}.onnx.json"

# --- Dependencias de Python ------------------------------------------------
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# No ejecutar como root.
RUN useradd --create-home --uid 1000 evalagent && chown -R evalagent:evalagent /app
USER evalagent

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
