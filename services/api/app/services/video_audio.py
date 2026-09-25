from __future__ import annotations

import re
import subprocess
from pathlib import Path

from app.config import Settings
from app.schemas import AudioSegment, AudioType
from app.services.alignment import normalize_token
from app.services.transcription import TranscriptionError, transcribe_media


def analyse_video_audio(root: Path, footage: dict, settings: Settings, script: str) -> list[AudioSegment]:
    clips = footage.get("clips") or []
    segments: list[AudioSegment] = []
    for index, clip in enumerate(clips, start=1):
        filename = clip.get("filename") or ""
        source = root / "footage" / filename
        if not source.exists():
            continue
        wav = root / "analysis" / "audio" / f"{Path(filename).stem}.wav"
        levels = _measure_levels(source)
        try:
            transcript = transcribe_media(source, settings, script=script, wav_path=wav)
        except TranscriptionError:
            transcript = None
        speech = list(transcript.segments) if transcript else []
        if speech:
            for part_index, part in enumerate(speech, start=1):
                text = (part.text or "").strip()
                quality = _speech_quality(levels, bool(text))
                audio_type, speaker = classify_audio(text, script, quality, speech=True)
                relevance = _script_overlap(text, script)
                segments.append(
                    AudioSegment(
                        id=f"audio_{Path(filename).stem}_{part_index:02d}",
                        source_file=filename,
                        start=round(part.start, 3),
                        end=round(max(part.end, part.start + 0.4), 3),
                        contains_speech=True,
                        transcript=text,
                        speaker_type=speaker,
                        audio_type=audio_type,
                        speech_quality=quality,
                        information_value=round(min(1.0, 0.2 + relevance + (0.15 if len(text) > 18 else 0)), 3),
                        news_relevance=relevance,
                        rms=levels["rms"],
                        peak=levels["peak"],
                        playback_gain=_playback_gain(levels),
                    )
                )
        else:
            audio_type, speaker = classify_audio("", script, _speech_quality(levels, False), speech=False)
            span_end = float(clip.get("usable_end") or clip.get("duration") or 4)
            span_start = float(clip.get("usable_start") or 0)
            if span_end - span_start < 0.6:
                span_end = span_start + min(4.0, float(clip.get("duration") or 4))
            segments.append(
                AudioSegment(
                    id=f"audio_{Path(filename).stem}_01",
                    source_file=filename,
                    start=round(span_start, 3),
                    end=round(span_end, 3),
                    contains_speech=False,
                    transcript="",
                    speaker_type=speaker,
                    audio_type=audio_type,
                    speech_quality=0.0,
                    information_value=0.12 if audio_type == "natural_sound" else 0.02,
                    news_relevance=0.35 if audio_type == "natural_sound" else 0.05,
                    rms=levels["rms"],
                    peak=levels["peak"],
                    playback_gain=_playback_gain(levels),
                )
            )
        _ = index
    return segments


def classify_audio(text: str, script: str, quality: float, speech: bool) -> tuple[AudioType, str]:
    if not speech or not text.strip():
        if quality >= 0.35:
            return "natural_sound", "environment"
        return "ambient_sound", "environment"
    if quality < 0.28:
        return "unusable_audio", "unknown"
    overlap = _script_overlap(text, script)
    lowered = text
    if overlap < 0.18:
        return "irrelevant_speech", "unknown"
    if _has_any(lowered, ("সূত্রে", "দপ্তর", "ঘোষণা", "বিধায়ক", "আধিকারিক")):
        return "official_statement", "official"
    if _has_any(lowered, ("দাঁড়িয়ে", "সংবাদ", "রিপোর্ট", "ব্যুরো")):
        return "reporter_standup", "reporter"
    if _has_any(lowered, ("দেখেছি", "চোখের সামনে", "আমি দেখ")):
        return "eyewitness_bite", "eyewitness"
    if _has_any(lowered, ("এখানে", "আমাদের", "জমে", "বাসিন্দা")):
        return "local_resident_bite", "local_resident"
    if overlap >= 0.55:
        return "soundbite", "unknown"
    return "reaction", "unknown"


def _script_overlap(text: str, script: str) -> float:
    needles = _tokens(text)
    hay = _tokens(script)
    if not needles or not hay:
        return 0.0
    return round(len(needles & hay) / max(len(needles), 1), 3)


def _tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.split(r"\s+", text or ""):
        key = normalize_token(raw)
        if len(key) >= 3:
            tokens.add(key)
    return tokens


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _speech_quality(levels: dict[str, float], has_text: bool) -> float:
    rms_db = levels.get("rms_db", -50)
    score = 0.42
    if rms_db > -22:
        score += 0.28
    elif rms_db > -32:
        score += 0.16
    elif rms_db < -42:
        score -= 0.2
    if has_text:
        score += 0.18
    return round(max(0.0, min(1.0, score)), 3)


def _playback_gain(levels: dict[str, float]) -> float:
    rms = max(levels.get("rms") or 0.0, 1e-6)
    peak = max(levels.get("peak") or rms, 1e-6)
    gain = min(0.08 / rms, 3.5)
    if peak * gain > 0.95:
        gain = 0.95 / peak
    return round(max(0.35, min(gain, 3.5)), 3)


def _measure_levels(path: Path) -> dict[str, float]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        str(path),
        "-af",
        "volumedetect",
        "-f",
        "null",
        "-",
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        return {"rms": 0.05, "peak": 0.4, "rms_db": -26.0}
    blob = (completed.stderr or "") + (completed.stdout or "")
    mean = _parse_db(blob, r"mean_volume:\s*([-\d.]+)")
    peak = _parse_db(blob, r"max_volume:\s*([-\d.]+)")
    rms_db = mean if mean is not None else -28.0
    peak_db = peak if peak is not None else -8.0
    return {
        "rms": _db_to_amp(rms_db),
        "peak": _db_to_amp(peak_db),
        "rms_db": rms_db,
    }


def _parse_db(blob: str, pattern: str) -> float | None:
    match = re.search(pattern, blob)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _db_to_amp(db: float) -> float:
    return max(1e-6, min(1.0, 10 ** (db / 20)))
