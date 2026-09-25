from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from app.config import Settings
from app.schemas import Transcript, TranscriptSegment, TranscriptWord
from app.services.media import MediaProbeError, probe_media

logger = logging.getLogger("bangla.news")

_model = None


def pin_huggingface_cache() -> Path:
    """Keep Whisper weights off Flash volumes that corrupt Hugging Face cache files."""
    cache = Path.home() / ".cache" / "huggingface"
    hub = cache / "hub"
    hub.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(cache)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hub)
    os.environ["HF_HUB_DISABLE_XET"] = "1"
    return cache


class TranscriptionError(RuntimeError):
    pass


def transcribe_voice(audio_path: Path, settings: Settings, script: str | None = None) -> Transcript:
    return transcribe_media(audio_path, settings, script=script)


def transcribe_media(
    media_path: Path,
    settings: Settings,
    script: str | None = None,
    wav_path: Path | None = None,
) -> Transcript:
    if not media_path.exists():
        raise TranscriptionError("media file is missing")
    if settings.mock_whisper:
        return _mock_transcript(media_path)

    pin_huggingface_cache()
    wav = _ensure_wav(media_path, wav_path)
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscriptionError("faster-whisper is not installed") from exc

    model = _load_model(settings, WhisperModel)
    try:
        prompt = "বাংলা সংবাদ।"
        if script:
            prompt = f"{prompt} {' '.join(script.split())[:180]}"
        segments, info = model.transcribe(
            str(wav),
            language="bn",
            word_timestamps=True,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=prompt,
        )
    except Exception as exc:
        raise TranscriptionError(f"Whisper failed: {exc}") from exc

    out_segments: list[TranscriptSegment] = []
    words: list[TranscriptWord] = []
    last_end = 0.0
    for segment in segments:
        text = (segment.text or "").strip()
        start = float(segment.start or 0)
        end = float(segment.end or start)
        last_end = max(last_end, end)
        if text:
            out_segments.append(TranscriptSegment(start=round(start, 3), end=round(end, 3), text=text))
        for word in segment.words or []:
            token = (word.word or "").strip()
            if not token:
                continue
            words.append(
                TranscriptWord(
                    start=round(float(word.start), 3),
                    end=round(float(word.end), 3),
                    text=token,
                )
            )
            last_end = max(last_end, float(word.end))

    duration = float(getattr(info, "duration", 0) or last_end)
    if duration <= 0:
        try:
            duration = float(probe_media(audio_path)["duration"])
        except MediaProbeError:
            duration = last_end
    return Transcript(
        language=getattr(info, "language", None) or "bn",
        duration=round(duration, 3),
        segments=out_segments,
        words=words,
        source="faster-whisper",
        model=settings.whisper_model,
    )


def _load_model(settings: Settings, whisper_cls):
    global _model
    if _model is not None:
        return _model
    device = settings.whisper_device
    if device == "auto":
        device = "cpu"
    logger.info("loading whisper model", extra={"stage": "TRANSCRIBING", "job_id": "-"})
    try:
        _model = whisper_cls(settings.whisper_model, device=device, compute_type=settings.whisper_compute_type)
    except Exception as exc:
        _model = None
        raise TranscriptionError(f"Whisper model could not be loaded: {exc}") from exc
    return _model


def _ensure_wav(path: Path, wav_path: Path | None = None) -> Path:
    if wav_path is None and path.suffix.lower() == ".wav":
        return path
    wav = wav_path or path.with_name("voice-16k.wav")
    wav.parent.mkdir(parents=True, exist_ok=True)
    if wav.exists() and wav.stat().st_mtime >= path.stat().st_mtime:
        return wav
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(wav),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise TranscriptionError("ffmpeg is required to decode the voice-over") from exc
    except subprocess.CalledProcessError as exc:
        raise TranscriptionError(exc.stderr.strip() or "could not decode voice-over") from exc
    return wav


def _mock_transcript(audio_path: Path) -> Transcript:
    try:
        duration = float(probe_media(audio_path)["duration"] or 8)
    except MediaProbeError:
        duration = 8.0
    return Transcript(
        language="bn",
        duration=round(duration, 3),
        segments=[TranscriptSegment(start=0, end=round(duration, 3), text="mock transcript")],
        words=[
            TranscriptWord(start=0, end=round(duration * 0.5, 3), text="mock"),
            TranscriptWord(start=round(duration * 0.5, 3), end=round(duration, 3), text="transcript"),
        ],
        source="mock",
        model="mock",
    )
