"""Configuración de la aplicación, leída de variables de entorno.

Ningún secreto se escribe en el código. El arranque falla de forma explícita si
falta algo crítico, en lugar de continuar con un valor por defecto inseguro.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Aplicación ---
    APP_NAME: str = "EvalAgent SENA"
    APP_VERSION: str = "2.0.0"
    ENTORNO: Literal["desarrollo", "pruebas", "produccion"] = "desarrollo"
    DEBUG: bool = False

    # --- Base de datos ---
    DATABASE_URL: str = "postgresql+asyncpg://evalagent:evalagent@localhost:5432/evalagent"

    # --- Seguridad ---
    SECRET_KEY: str = Field(min_length=32)
    ALGORITMO_JWT: str = "HS256"
    MINUTOS_TOKEN_ACCESO: int = 30
    DIAS_TOKEN_REFRESCO: int = 7
    SEGUNDOS_TICKET_WS: int = 60
    BCRYPT_ROUNDS: int = 12

    # --- CORS (T-013 / deuda D6) ---
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Límite de peticiones ---
    LOGIN_INTENTOS_MAX: int = 5
    LOGIN_VENTANA_SEGUNDOS: int = 60

    # --- Motores de IA ---
    OLLAMA_URL: str = "http://localhost:11434/api/chat"
    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_TIMEOUT: float = 60.0

    WHISPER_MODEL: str = "medium"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    # `auto` selecciona el primer motor disponible: piper -> say -> espeak.
    TTS_ENGINE: Literal["auto", "piper", "say", "espeak", "ninguno"] = "auto"
    PIPER_BIN: str = "piper"
    PIPER_VOICE_PATH: str = "/app/voces/es_ES-davefx-medium.onnx"
    SAY_VOICE: str = "Paulina"

    # --- Límites de la sustentación ---
    MAX_AUDIO_BYTES: int = 10 * 1024 * 1024
    MINUTOS_SESION_INACTIVA: int = 60

    @property
    def cors_origins_lista(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @field_validator("SECRET_KEY")
    @classmethod
    def _secret_no_por_defecto(cls, v: str) -> str:
        inseguras = {"changeme", "secret", "cambiame", "dev", "test"}
        if v.lower() in inseguras:
            raise ValueError(
                "SECRET_KEY tiene un valor por defecto inseguro. "
                "Genera una con: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
        return v

    @model_validator(mode="after")
    def _cors_no_comodin(self) -> "Settings":
        """T-013: `*` con credenciales es inválido por especificación de CORS.

        En la v1 se usaba allow_origins=["*"] junto a allow_credentials=True.
        Con JWT y despliegue público eso pasa a ser un fallo de seguridad real,
        así que el arranque se aborta en lugar de degradarse en silencio.
        """
        if "*" in self.cors_origins_lista:
            raise ValueError(
                "CORS_ORIGINS no admite '*': la API envía credenciales. "
                "Indica los orígenes permitidos separados por comas."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
