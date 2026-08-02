"""Tests de configuración (T-013 · deuda D6)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(**extra) -> Settings:
    base = {"SECRET_KEY": "x" * 48, "CORS_ORIGINS": "http://localhost:5173"}
    return Settings(**{**base, **extra})  # type: ignore[arg-type]


def test_cors_comodin_aborta_el_arranque() -> None:
    """La v1 usaba allow_origins=['*'] con credenciales: combinación inválida.

    Con JWT y despliegue público pasa a ser un fallo de seguridad real, así que
    el arranque se aborta en lugar de degradarse en silencio.
    """
    with pytest.raises(ValidationError, match="no admite"):
        _settings(CORS_ORIGINS="*")


def test_cors_comodin_entre_otros_origenes_tambien_aborta() -> None:
    with pytest.raises(ValidationError):
        _settings(CORS_ORIGINS="http://localhost:5173,*")


def test_cors_acepta_lista_de_origenes() -> None:
    s = _settings(CORS_ORIGINS="http://localhost:5173, https://evalagent.sena.edu.co")
    assert s.cors_origins_lista == [
        "http://localhost:5173",
        "https://evalagent.sena.edu.co",
    ]


def test_secret_key_corta_es_rechazada() -> None:
    with pytest.raises(ValidationError):
        _settings(SECRET_KEY="corta")


@pytest.mark.parametrize("insegura", ["changeme", "SECRET", "cambiame", "dev"])
def test_secret_key_por_defecto_es_rechazada(insegura: str) -> None:
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY=insegura, CORS_ORIGINS="http://localhost:5173")  # type: ignore[arg-type]


def test_tts_engine_invalido_es_rechazado() -> None:
    with pytest.raises(ValidationError):
        _settings(TTS_ENGINE="festival")
