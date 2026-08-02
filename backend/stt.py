import asyncio
import os
from pathlib import Path
import tempfile

# medium = mejor precisión para términos técnicos en español
# Si es muy lento, cambia a "small"
WHISPER_MODEL = "medium"

# Contexto técnico para ayudar a Whisper a entender vocabulario de programación
INITIAL_PROMPT = (
    "Sustentación de proyecto de API REST. Términos técnicos: "
    "endpoint, request, response, HTTP, GET, POST, PUT, DELETE, "
    "JSON, autenticación, JWT, token, middleware, base de datos, "
    "MongoDB, MySQL, PostgreSQL, Express, Node.js, Python, FastAPI, "
    "error 400, error 401, error 404, error 500, bad request, "
    "validación, seguridad, variable de entorno, deploy, framework."
)


async def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio usando faster-whisper en local.
    Devuelve el texto transcrito.
    """
    wav_path = str(Path(audio_path).with_suffix(".wav"))

    try:
        # Convertir a WAV 16kHz mono (óptimo para Whisper)
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", audio_path,
            "-ar", "16000",
            "-ac", "1",
            "-f", "wav",
            wav_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        try:
            transcript = await _transcribe_faster_whisper(wav_path)
        except ImportError:
            transcript = await _transcribe_openai_whisper(wav_path)

        return transcript.strip()

    finally:
        try:
            if os.path.exists(wav_path):
                os.unlink(wav_path)
        except Exception:
            pass


async def _transcribe_faster_whisper(wav_path: str) -> str:
    from faster_whisper import WhisperModel

    # Carga el modelo una sola vez y lo reutiliza
    if not hasattr(_transcribe_faster_whisper, "_model"):
        print(f"[STT] Cargando modelo Whisper '{WHISPER_MODEL}'...")
        _transcribe_faster_whisper._model = WhisperModel(
            WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
        )
        print("[STT] Modelo cargado.")

    model = _transcribe_faster_whisper._model
    loop = asyncio.get_event_loop()

    def _run():
        segments, info = model.transcribe(
            wav_path,
            language="es",
            beam_size=5,
            initial_prompt=INITIAL_PROMPT,   # contexto técnico
            vad_filter=True,                  # filtra silencios automáticamente
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False, # evita alucinaciones encadenadas
            temperature=0.0,                  # más determinista
        )
        return " ".join(seg.text for seg in segments)

    return await loop.run_in_executor(None, _run)


async def _transcribe_openai_whisper(wav_path: str) -> str:
    import whisper

    if not hasattr(_transcribe_openai_whisper, "_model"):
        _transcribe_openai_whisper._model = whisper.load_model(WHISPER_MODEL)

    model = _transcribe_openai_whisper._model
    loop = asyncio.get_event_loop()

    result = await loop.run_in_executor(
        None,
        lambda: model.transcribe(
            wav_path,
            language="es",
            initial_prompt=INITIAL_PROMPT,
            temperature=0.0,
        )
    )
    return result["text"]
