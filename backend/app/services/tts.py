"""Síntesis de voz multiplataforma (T-012 · corrige la deuda D1).

El defecto de la v1 no fue elegir el comando `say` de macOS, sino **llamarlo
directamente desde la lógica de negocio**. El README y `start.sh` prometían
Piper, pero `tts.py` invocaba `say`, dejando el sistema mudo en Linux — justo
donde hay que desplegarlo.

Aquí el TTS es una interfaz con varias implementaciones, seleccionadas en el
arranque por disponibilidad real. Ver ADR-005.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import shutil
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()


def limpiar_texto(texto: str) -> str:
    """Quita Markdown y etiquetas internas antes de sintetizar."""
    texto = re.sub(r"\[.*?\]", "", texto)  # [INSTRUCCIÓN INTERNA: ...]
    texto = re.sub(r"\*+", "", texto)  # **negrita**
    texto = re.sub(r"#+\s*", "", texto)  # ## encabezados
    texto = re.sub(r"`+", "", texto)  # `código`
    return re.sub(r"\s+", " ", texto).strip()


async def _ejecutar(*args: str, timeout: float = 30.0) -> int:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        raise RuntimeError(f"{args[0]} superó el tiempo límite de {timeout}s") from None
    if proc.returncode != 0:
        detalle = stderr.decode("utf-8", "replace")[:300] if stderr else ""
        raise RuntimeError(f"{args[0]} falló (código {proc.returncode}): {detalle}")
    return proc.returncode


# --------------------------------------------------------------------------- #
# Interfaz
# --------------------------------------------------------------------------- #


class MotorTTS(ABC):
    """Contrato común. Toda implementación devuelve WAV en base64."""

    nombre: str

    @abstractmethod
    def disponible(self) -> bool:
        """¿Están los binarios y modelos que este motor necesita?"""

    @abstractmethod
    async def sintetizar(self, texto: str) -> str:
        """Devuelve WAV codificado en base64."""

    def describir(self) -> dict[str, str]:
        return {"motor": self.nombre}


class PiperTTS(MotorTTS):
    """Motor de referencia. Funciona en Linux, macOS y Windows."""

    nombre = "piper"

    def __init__(self, binario: str, voz: str) -> None:
        self._binario = binario
        self._voz = voz

    def disponible(self) -> bool:
        return bool(shutil.which(self._binario)) and Path(self._voz).is_file()

    async def sintetizar(self, texto: str) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            salida = tmp.name
        try:
            proc = await asyncio.create_subprocess_exec(
                self._binario,
                "--model",
                self._voz,
                "--output_file",
                salida,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(
                proc.communicate(texto.encode("utf-8")), timeout=30.0
            )
            if proc.returncode != 0:
                detalle = stderr.decode("utf-8", "replace")[:300] if stderr else ""
                raise RuntimeError(f"piper falló: {detalle}")
            return _leer_wav_base64(salida)
        finally:
            _borrar(salida)

    def describir(self) -> dict[str, str]:
        return {"motor": self.nombre, "voz": Path(self._voz).stem}


class SayTTS(MotorTTS):
    """Reserva para desarrollo local en macOS. Requiere ffmpeg para el WAV."""

    nombre = "say"

    def __init__(self, voz: str) -> None:
        self._voz = voz

    def disponible(self) -> bool:
        return bool(shutil.which("say")) and bool(shutil.which("ffmpeg"))

    async def sintetizar(self, texto: str) -> str:
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
            aiff = tmp.name
        wav = aiff.replace(".aiff", ".wav")
        try:
            await _ejecutar("say", "-v", self._voz, "--output-file", aiff, texto)
            await _ejecutar(
                "ffmpeg",
                "-y",
                "-i",
                aiff,
                "-ar",
                "22050",
                "-ac",
                "1",
                "-f",
                "wav",
                wav,
            )
            return _leer_wav_base64(wav)
        finally:
            _borrar(aiff, wav)

    def describir(self) -> dict[str, str]:
        return {"motor": self.nombre, "voz": self._voz}


class EspeakTTS(MotorTTS):
    """Reserva de emergencia en Linux. Voz robótica, pero inteligible."""

    nombre = "espeak"

    def disponible(self) -> bool:
        return bool(shutil.which("espeak-ng"))

    async def sintetizar(self, texto: str) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            salida = tmp.name
        try:
            await _ejecutar("espeak-ng", "-v", "es", "-s", "150", "-w", salida, texto)
            return _leer_wav_base64(salida)
        finally:
            _borrar(salida)


class SinTTS(MotorTTS):
    """Modo solo texto.

    Una sustentación sin voz es peor que con voz, pero es mejor que ninguna
    sustentación. El frontend avisa al aprendiz de que no habrá audio.
    """

    nombre = "ninguno"

    def disponible(self) -> bool:
        return True

    async def sintetizar(self, texto: str) -> str:  # noqa: ARG002
        return ""


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #


def _leer_wav_base64(ruta: str) -> str:
    archivo = Path(ruta)
    if not archivo.is_file() or archivo.stat().st_size == 0:
        raise RuntimeError(f"El motor TTS no generó audio en {ruta}")
    return base64.b64encode(archivo.read_bytes()).decode("utf-8")


def _borrar(*rutas: str) -> None:
    for ruta in rutas:
        try:
            if ruta and os.path.exists(ruta):
                os.unlink(ruta)
        except OSError:  # pragma: no cover - limpieza best-effort
            logger.warning("No se pudo borrar el temporal %s", ruta)


# --------------------------------------------------------------------------- #
# Selección del motor
# --------------------------------------------------------------------------- #

_ORDEN_PREFERENCIA = ("piper", "say", "espeak")


def _construir(nombre: str) -> MotorTTS:
    match nombre:
        case "piper":
            return PiperTTS(_settings.PIPER_BIN, _settings.PIPER_VOICE_PATH)
        case "say":
            return SayTTS(_settings.SAY_VOICE)
        case "espeak":
            return EspeakTTS()
        case _:
            return SinTTS()


def seleccionar_motor() -> MotorTTS:
    """Elige el motor en el arranque.

    Si `TTS_ENGINE` nombra un motor concreto y no está disponible, se aborta el
    arranque: un fallo silencioso a otro motor sería una sorpresa desagradable
    en producción.
    """
    configurado = _settings.TTS_ENGINE

    if configurado == "ninguno":
        logger.warning("TTS deshabilitado por configuración: modo solo texto")
        return SinTTS()

    if configurado != "auto":
        motor = _construir(configurado)
        if not motor.disponible():
            raise RuntimeError(
                f"TTS_ENGINE={configurado} pero el motor no está disponible. "
                f"Instálalo o usa TTS_ENGINE=auto."
            )
        logger.info("Motor TTS forzado por configuración: %s", motor.nombre)
        return motor

    for nombre in _ORDEN_PREFERENCIA:
        motor = _construir(nombre)
        if motor.disponible():
            logger.info("Motor TTS seleccionado automáticamente: %s", motor.nombre)
            return motor

    logger.error(
        "Ningún motor TTS disponible (%s). El agente funcionará en modo solo texto.",
        ", ".join(_ORDEN_PREFERENCIA),
    )
    return SinTTS()


_motor: MotorTTS | None = None


def motor_activo() -> MotorTTS:
    global _motor
    if _motor is None:
        _motor = seleccionar_motor()
    return _motor


async def sintetizar_voz(texto: str) -> str:
    """Punto de entrada del servicio. Devuelve WAV base64, o "" si no hay audio.

    Un fallo de síntesis nunca interrumpe la sustentación: se registra y se
    continúa en modo solo texto para ese turno.
    """
    limpio = limpiar_texto(texto)
    if not limpio:
        return ""
    try:
        return await motor_activo().sintetizar(limpio)
    except Exception:
        logger.exception("Fallo al sintetizar voz con el motor %s", motor_activo().nombre)
        return ""
