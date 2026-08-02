"""Health check (HU-15)."""

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import SesionBD
from app.core.config import get_settings
from app.services import tts

router = APIRouter(tags=["Operación"])
_settings = get_settings()


@router.get("/health")
async def health(bd: SesionBD) -> dict:
    """Estado del servicio y de sus dependencias.

    Expone el motor TTS activo: es el criterio de aceptación de T-012 que
    permite verificar en producción cuál se seleccionó realmente.
    """
    return {
        "status": "ok",
        "version": _settings.APP_VERSION,
        "entorno": _settings.ENTORNO,
        "db": await _estado_bd(bd),
        "ollama": await _estado_ollama(),
        "stt": {"modelo": _settings.WHISPER_MODEL, "device": _settings.WHISPER_DEVICE},
        "tts": tts.motor_activo().describir(),
    }


async def _estado_bd(bd: SesionBD) -> str:
    try:
        await bd.execute(text("SELECT 1"))
    except Exception:
        return "error"
    return "ok"


async def _estado_ollama() -> dict:
    url = _settings.OLLAMA_URL.replace("/api/chat", "/api/tags")
    try:
        async with httpx.AsyncClient(timeout=3.0) as cliente:
            r = await cliente.get(url)
            r.raise_for_status()
    except Exception:
        return {"estado": "no disponible", "modelo": _settings.OLLAMA_MODEL}
    return {"estado": "ok", "modelo": _settings.OLLAMA_MODEL}
