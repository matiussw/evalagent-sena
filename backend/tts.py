import asyncio
import base64
import os
import re
import tempfile
from pathlib import Path

# macOS 'say' voice for Spanish — options: Paulina (es_MX), Mónica (es_ES)
SAY_VOICE = "Paulina"


async def synthesize_speech(text: str) -> str:
    """
    Convert text to speech using macOS 'say' command.
    Returns base64-encoded WAV audio, or empty string on error.
    """
    clean = _clean_text(text)
    if not clean.strip():
        return ""

    aiff_path = ""
    wav_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
            aiff_path = tmp.name

        wav_path = aiff_path.replace(".aiff", ".wav")

        # 1. Generate AIFF with macOS say
        proc = await asyncio.create_subprocess_exec(
            "say",
            "-v", SAY_VOICE,
            "--output-file", aiff_path,
            clean,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        if not Path(aiff_path).exists() or Path(aiff_path).stat().st_size == 0:
            raise RuntimeError("say produced empty output")

        # 2. Convert AIFF → WAV (16 kHz mono) using ffmpeg
        conv = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", aiff_path,
            "-ar", "22050", "-ac", "1", "-f", "wav", wav_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await conv.wait()

        with open(wav_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    except Exception as e:
        print(f"TTS error: {e}")
        return ""
    finally:
        for p in [aiff_path, wav_path]:
            try:
                if p and os.path.exists(p):
                    os.unlink(p)
            except Exception:
                pass


def _clean_text(text: str) -> str:
    """Remove markdown and internal tags before sending to TTS."""
    text = re.sub(r'\[.*?\]', '', text)          # [INSTRUCCIÓN INTERNA: ...]
    text = re.sub(r'\*+', '', text)               # **bold**
    text = re.sub(r'#+\s*', '', text)             # ## headers
    text = re.sub(r'`+', '', text)                # `code`
    text = re.sub(r'\s+', ' ', text).strip()
    return text
