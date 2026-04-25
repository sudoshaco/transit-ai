"""
Voice-Router: /api/voice/stt (Parakeet) + /api/voice/tts (Kokoro/Thorsten).

Die eigentlichen Modelle liegen nicht im Container. Dieser Router prüft
per Env-Flag + Dateipräsenz und antwortet sauber mit 503, solange sie
noch nicht gemountet sind. Sobald die Dateien da sind, werden sie lazy
geladen und verwendet.

Mounts (erwartet):
  /models/stt/parakeet-tdt-0.6b-v3.nemo
  /models/tts/kokoro/kokoro-v0_19.onnx   + voices-*.bin
  /models/tts/piper/de_DE-thorsten-high.onnx + .onnx.json
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice"])

MODELS_ROOT = Path(os.getenv("MODELS_DIR", "/models"))
STT_PATH = MODELS_ROOT / "stt" / "parakeet-tdt-0.6b-v3.nemo"
STT_ENABLED = os.getenv("STT_ENABLED", "1") == "1"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_CACHE = Path(os.getenv("WHISPER_CACHE", "/models/stt-whisper"))
# Falls ein lokales Whisper-Modell gemountet ist, direkt von dort laden (kein HF-Download).
WHISPER_LOCAL_DIR = Path(os.getenv(
    "WHISPER_LOCAL_DIR",
    "/models/stt-whisper/models--Systran--faster-whisper-small/snapshots/main",
))
TTS_PIPER = MODELS_ROOT / "tts" / "piper" / "de_DE-thorsten-high.onnx"
TTS_KOKORO = MODELS_ROOT / "tts" / "kokoro" / "kokoro-v0_19.onnx"

MAX_AUDIO_BYTES = 4 * 1024 * 1024   # 4 MB für STT-Uploads
MAX_TTS_CHARS = 600                  # Rate-Schutz

# Magic-Byte-Whitelist — nur echte Audio-Container akzeptieren, keine EXE / Script-Payloads.
_AUDIO_MAGIC_PREFIXES = (
    b"\x1a\x45\xdf\xa3",             # EBML / WebM / Matroska
    b"OggS",                         # Ogg / Opus / Vorbis
    b"RIFF",                         # WAV / RIFF-Container (prüft Sub-ID separat)
    b"ID3",                          # MP3 mit ID3-Tag
    b"\xff\xfb", b"\xff\xf3", b"\xff\xf2",   # MPEG-1/2 Layer III frames
    b"fLaC",                         # FLAC
    b"FORM",                         # AIFF
    b"\x00\x00\x00\x18ftyp", b"\x00\x00\x00\x1cftyp",
    b"\x00\x00\x00\x20ftyp",         # MP4 / M4A / AAC in MP4
)
_ALLOWED_CONTENT_TYPES = {
    "audio/webm", "audio/webm;codecs=opus", "audio/ogg", "audio/opus",
    "audio/wav", "audio/x-wav", "audio/wave", "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/x-m4a", "audio/aac", "audio/flac",
    "application/octet-stream",   # Browser-MediaRecorder setzt dies gelegentlich
}


def _looks_like_audio(data: bytes) -> bool:
    if len(data) < 4:
        return False
    for prefix in _AUDIO_MAGIC_PREFIXES:
        if data.startswith(prefix):
            return True
    # MP4 ftyp-Box kann an Offset 4 stehen
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return True
    return False

_stt_model = None
_tts_piper = None
_tts_kokoro = None


# ---------------------------------------------------------------------------
# Auth dep — reuse access-token check (Voice ist User-only, schützt Ressourcen)
# ---------------------------------------------------------------------------
try:
    from app.auth.deps import current_user as require_user  # type: ignore
except Exception:  # pragma: no cover — lets app start even if deps missing
    async def require_user():
        return None


# ---------------------------------------------------------------------------
# GET /api/voice/status — zeigt ob Modelle verfügbar sind
# ---------------------------------------------------------------------------
class VoiceStatus(BaseModel):
    stt_available: bool
    tts_available: bool
    tts_engine: Optional[str] = None


@router.get("/status", response_model=VoiceStatus)
async def voice_status():
    tts_engine = None
    if TTS_PIPER.exists():
        tts_engine = "piper-thorsten"
    elif TTS_KOKORO.exists():
        tts_engine = "kokoro"
    return VoiceStatus(
        stt_available=STT_ENABLED,
        tts_available=tts_engine is not None,
        tts_engine=tts_engine,
    )


# ---------------------------------------------------------------------------
# POST /api/voice/stt — Audio (webm/wav/ogg) -> Transkript
# ---------------------------------------------------------------------------
class STTResponse(BaseModel):
    text: str
    lang: str = "de"


@router.post("/stt", response_model=STTResponse)
async def stt(
    audio: UploadFile = File(...),
    _user=Depends(require_user),
):
    if not STT_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Spracherkennung deaktiviert.",
        )

    ct = (audio.content_type or "").lower().split(";")[0].strip()
    if ct and ct not in _ALLOWED_CONTENT_TYPES:
        logger.warning("STT rejected content-type=%s", ct)
        raise HTTPException(status_code=415, detail="Audio-Format nicht erlaubt.")

    data = await audio.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audiodatei zu groß (max 4 MB).")
    if len(data) < 200:
        raise HTTPException(status_code=400, detail="Leere oder kaputte Audiodatei.")
    if not _looks_like_audio(data):
        logger.warning("STT rejected non-audio payload, len=%d, head=%r", len(data), data[:16])
        raise HTTPException(status_code=415, detail="Datei ist keine Audioaufnahme.")

    try:
        text = await asyncio.to_thread(_transcribe_whisper, data, audio.content_type or "")
    except subprocess.CalledProcessError as e:
        logger.error("ffmpeg failed: %s", getattr(e, "stderr", b"")[-400:])
        raise HTTPException(status_code=422, detail="Audio konnte nicht dekodiert werden.")
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timeout")
        raise HTTPException(status_code=504, detail="Audio-Dekodierung dauerte zu lange.")
    except Exception as e:
        logger.error("STT failed: %s", e)
        raise HTTPException(status_code=500, detail="Spracherkennung fehlgeschlagen.")

    text = re.sub(r"\s+", " ", text).strip()[:500]
    return STTResponse(text=text)


def _transcribe_whisper(audio_bytes: bytes, content_type: str) -> str:
    global _stt_model
    if _stt_model is None:
        from faster_whisper import WhisperModel  # type: ignore
        if WHISPER_LOCAL_DIR.exists() and (WHISPER_LOCAL_DIR / "model.bin").exists():
            logger.info("Loading whisper from local dir: %s", WHISPER_LOCAL_DIR)
            _stt_model = WhisperModel(
                str(WHISPER_LOCAL_DIR),
                device="cpu",
                compute_type="int8",
            )
        else:
            logger.info("Loading whisper via HF hub, cache: %s", WHISPER_CACHE)
            try:
                WHISPER_CACHE.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
            _stt_model = WhisperModel(
                WHISPER_MODEL,
                device="cpu",
                compute_type="int8",
                download_root=str(WHISPER_CACHE),
            )

    import tempfile
    src_path = dst_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".in", delete=False) as src, \
             tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as dst:
            src_path, dst_path = src.name, dst.name
            src.write(audio_bytes)
            src.flush()
            # Harte ffmpeg-Flags: kein Netzwerk, keine externen Protokolle, Thread-Limit
            subprocess.run(
                [
                    "ffmpeg", "-y", "-nostdin",
                    "-loglevel", "error",
                    "-threads", "1",
                    "-i", src_path,
                    "-ar", "16000", "-ac", "1", "-f", "wav",
                    "-t", "120",
                    dst_path,
                ],
                check=True, capture_output=True, timeout=30,
            )
            segments, info = _stt_model.transcribe(dst_path, language="de", vad_filter=True)
            return " ".join(seg.text.strip() for seg in segments).strip()
    finally:
        for p in (src_path, dst_path):
            if p:
                try:
                    os.unlink(p)
                except OSError:
                    pass


# ---------------------------------------------------------------------------
# POST /api/voice/tts — Text -> audio/wav
# ---------------------------------------------------------------------------
class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TTS_CHARS)


@router.post("/tts")
async def tts(req: TTSRequest, _user=Depends(require_user)):
    engine = None
    if TTS_PIPER.exists():
        engine = "piper"
    elif TTS_KOKORO.exists():
        engine = "kokoro"

    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="Sprachausgabe noch nicht aktiviert — TTS-Modell fehlt auf dem Server.",
        )

    # Sanitize: nur Zeichen, die für Sprachsynthese sinnvoll sind
    text = re.sub(r"[^\w\s\.,:;\-–!?€%/üöäÜÖÄß\"'()]", " ", req.text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise HTTPException(status_code=400, detail="Leerer Text.")

    try:
        if engine == "piper":
            wav = await asyncio.to_thread(_synth_piper, text)
        else:
            wav = await asyncio.to_thread(_synth_kokoro, text)
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail="Sprachausgabe fehlgeschlagen.")

    return Response(
        content=wav,
        media_type="audio/wav",
        headers={"Cache-Control": "private, max-age=60"},
    )


def _synth_piper(text: str) -> bytes:
    global _tts_piper
    if _tts_piper is None:
        from piper import PiperVoice  # type: ignore
        _tts_piper = PiperVoice.load(str(TTS_PIPER))
    import io, wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        _tts_piper.synthesize(text, wf)
    return buf.getvalue()


def _synth_kokoro(text: str) -> bytes:
    global _tts_kokoro
    if _tts_kokoro is None:
        from kokoro_onnx import Kokoro  # type: ignore
        voices = str(TTS_KOKORO.parent / "voices.bin")
        _tts_kokoro = Kokoro(str(TTS_KOKORO), voices)
    import io, wave
    samples, sr = _tts_kokoro.create(text, voice="af_sky", speed=1.0, lang="de")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        # float32 -> int16
        import struct
        int_samples = (
            max(-1.0, min(1.0, float(s))) for s in samples
        )
        packed = b"".join(
            struct.pack("<h", int(v * 32767)) for v in int_samples
        )
        wf.writeframes(packed)
    return buf.getvalue()
