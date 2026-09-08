"""Tests del TTS multiplataforma (T-012 · deuda D1).

Se simulan los binarios: los tests no pueden depender de que Piper, `say` o
espeak-ng estén instalados en la máquina que ejecuta la suite.
"""

import base64
import struct

import pytest

from app.services import tts


def _wav_minimo() -> bytes:
    """Cabecera WAV válida con un frame de silencio."""
    datos = b"\x00\x00"
    return (
        b"RIFF"
        + struct.pack("<I", 36 + len(datos))
        + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, 22050, 44100, 2, 16)
        + b"data"
        + struct.pack("<I", len(datos))
        + datos
    )


# --------------------------------------------------------------------------- #
# limpiar_texto
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("[INSTRUCCIÓN INTERNA: cierra] Buen trabajo", "Buen trabajo"),
        ("**Muy bien**, sigue así", "Muy bien, sigue así"),
        ("## Pregunta 3\n¿Qué es un endpoint?", "Pregunta 3 ¿Qué es un endpoint?"),
        ("Usa `GET /tareas` para listar", "Usa GET /tareas para listar"),
        ("   espacios    de     sobra   ", "espacios de sobra"),
    ],
)
def test_limpiar_texto_quita_marcado(entrada: str, esperado: str) -> None:
    assert tts.limpiar_texto(entrada) == esperado


# --------------------------------------------------------------------------- #
# Selección de motor (ADR-005)
# --------------------------------------------------------------------------- #


def test_auto_prefiere_piper_cuando_esta_disponible(monkeypatch) -> None:
    monkeypatch.setattr(tts.PiperTTS, "disponible", lambda self: True)
    monkeypatch.setattr(tts.SayTTS, "disponible", lambda self: True)
    monkeypatch.setattr(tts._settings, "TTS_ENGINE", "auto")

    assert tts.seleccionar_motor().nombre == "piper"


def test_auto_cae_a_say_si_no_hay_piper(monkeypatch) -> None:
    """Criterio de aceptación: sin Piper y en macOS, se usa `say` como reserva."""
    monkeypatch.setattr(tts.PiperTTS, "disponible", lambda self: False)
    monkeypatch.setattr(tts.SayTTS, "disponible", lambda self: True)
    monkeypatch.setattr(tts._settings, "TTS_ENGINE", "auto")

    assert tts.seleccionar_motor().nombre == "say"


def test_auto_cae_a_espeak_en_linux_sin_piper(monkeypatch) -> None:
    monkeypatch.setattr(tts.PiperTTS, "disponible", lambda self: False)
    monkeypatch.setattr(tts.SayTTS, "disponible", lambda self: False)
    monkeypatch.setattr(tts.EspeakTTS, "disponible", lambda self: True)
    monkeypatch.setattr(tts._settings, "TTS_ENGINE", "auto")

    assert tts.seleccionar_motor().nombre == "espeak"


def test_sin_ningun_motor_pasa_a_modo_solo_texto(monkeypatch) -> None:
    """Criterio de aceptación: sin motores, la sesión continúa sin audio."""
    for clase in (tts.PiperTTS, tts.SayTTS, tts.EspeakTTS):
        monkeypatch.setattr(clase, "disponible", lambda self: False)
    monkeypatch.setattr(tts._settings, "TTS_ENGINE", "auto")

    assert tts.seleccionar_motor().nombre == "ninguno"


def test_motor_forzado_ausente_aborta_el_arranque(monkeypatch) -> None:
    """Criterio de aceptación: TTS_ENGINE=piper sin Piper falla explícitamente.

    Caer en silencio a otro motor sería una sorpresa desagradable en producción.
    """
    monkeypatch.setattr(tts.PiperTTS, "disponible", lambda self: False)
    monkeypatch.setattr(tts._settings, "TTS_ENGINE", "piper")

    with pytest.raises(RuntimeError, match="no está disponible"):
        tts.seleccionar_motor()


# --------------------------------------------------------------------------- #
# Síntesis
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_piper_devuelve_wav_en_base64(monkeypatch, tmp_path) -> None:
    """Criterio de aceptación: en Linux con Piper, se obtiene WAV de >0 bytes."""
    voz = tmp_path / "es_ES-davefx-medium.onnx"
    voz.write_bytes(b"modelo-simulado")
    motor = tts.PiperTTS("piper", str(voz))

    class ProcesoSimulado:
        returncode = 0

        async def communicate(self, entrada=None):
            # Piper escribe el WAV en la ruta que recibe por --output_file.
            from pathlib import Path

            Path(ProcesoSimulado.salida).write_bytes(_wav_minimo())
            return b"", b""

    async def crear_proceso(*args, **kwargs):
        ProcesoSimulado.salida = args[args.index("--output_file") + 1]
        return ProcesoSimulado()

    monkeypatch.setattr("asyncio.create_subprocess_exec", crear_proceso)

    resultado = await motor.sintetizar("Cuéntame sobre tu proyecto")

    assert resultado
    assert base64.b64decode(resultado).startswith(b"RIFF")


@pytest.mark.asyncio
async def test_texto_vacio_no_invoca_al_motor(monkeypatch) -> None:
    llamadas = []

    class MotorEspia(tts.SinTTS):
        async def sintetizar(self, texto: str) -> str:
            llamadas.append(texto)
            return "audio"

    monkeypatch.setattr(tts, "_motor", MotorEspia())

    assert await tts.sintetizar_voz("   ") == ""
    assert await tts.sintetizar_voz("[SOLO ETIQUETA]") == ""
    assert llamadas == []


@pytest.mark.asyncio
async def test_fallo_de_sintesis_no_interrumpe_la_sustentacion(monkeypatch) -> None:
    """Un motor que revienta degrada a solo texto, no tumba el turno."""

    class MotorRoto(tts.SinTTS):
        nombre = "roto"

        async def sintetizar(self, texto: str) -> str:
            raise RuntimeError("piper murió")

    monkeypatch.setattr(tts, "_motor", MotorRoto())

    assert await tts.sintetizar_voz("Hola") == ""


@pytest.mark.asyncio
async def test_piper_borra_el_temporal_aunque_falle(monkeypatch, tmp_path) -> None:
    """Sin este `finally`, cada fallo dejaría un WAV huérfano en disco."""
    voz = tmp_path / "voz.onnx"
    voz.write_bytes(b"x")
    motor = tts.PiperTTS("piper", str(voz))
    rutas: list[str] = []

    class ProcesoRoto:
        returncode = 1

        async def communicate(self, entrada=None):
            return b"", b"boom"

    async def crear_proceso(*args, **kwargs):
        rutas.append(args[args.index("--output_file") + 1])
        return ProcesoRoto()

    monkeypatch.setattr("asyncio.create_subprocess_exec", crear_proceso)

    with pytest.raises(RuntimeError):
        await motor.sintetizar("Hola")

    from pathlib import Path

    assert rutas and not Path(rutas[0]).exists()
