"""Transcripción de voz a texto con faster-whisper (ADR-001).

El modelo se carga una sola vez y se reutiliza: cargarlo por petición añadiría
varios segundos a cada turno. La transcripción corre en un *thread pool* para no
bloquear el bucle de eventos de asyncio.
"""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()


@lru_cache(maxsize=1)
def _modelo() -> Any:
    from faster_whisper import WhisperModel

    logger.info(
        "Cargando Whisper %s en %s (%s)",
        _settings.WHISPER_MODEL,
        _settings.WHISPER_DEVICE,
        _settings.WHISPER_COMPUTE_TYPE,
    )
    return WhisperModel(
        _settings.WHISPER_MODEL,
        device=_settings.WHISPER_DEVICE,
        compute_type=_settings.WHISPER_COMPUTE_TYPE,
    )


def _transcribir_sincrono(ruta: str) -> str:
    segmentos, _ = _modelo().transcribe(
        ruta,
        language="es",
        beam_size=5,
        # Filtra silencios: evita que el modelo alucine texto sobre ruido de fondo.
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    return " ".join(s.text.strip() for s in segmentos).strip()


async def transcribir(ruta_audio: str) -> str:
    """Devuelve el texto reconocido, o cadena vacía si no se detectó voz."""
    try:
        return await asyncio.to_thread(_transcribir_sincrono, ruta_audio)
    except Exception:
        logger.exception("Fallo al transcribir %s", ruta_audio)
        return ""


def precargar() -> None:
    """Carga el modelo en el arranque para que el primer turno no pague la espera."""
    try:
        _modelo()
    except Exception:
        logger.exception("No se pudo precargar el modelo de Whisper")
