from __future__ import annotations

import re

from app.schemas import AlignmentResult, NarrationSegment
from app.services.alignment import normalize_token

SENTENCE_END = re.compile(r"(?<=[।!?])\s+")
SPACE = re.compile(r"\s+")
STOP = {
    "এবং",
    "ও",
    "একটি",
    "এক",
    "এই",
    "সেই",
    "করা",
    "হয়",
    "হয়ে",
    "হয়েছে",
    "হয়ে",
    "জন্য",
    "থেকে",
    "করে",
    "বলে",
    "আরও",
    "আর",
    "যে",
    "কি",
    "না",
}
LOCATION_MARKERS = ("দুর্গাপুর", "কলকাতা", "মল", "স্টেশন", "রোড", "শহর", "থানা", "বাজার")
QUOTE_MARKERS = ("জানান", "বলেন", "জানিয়ে", "বিধায়ক", "আধিকারিক")
SOUNDBITE_MARKERS = (
    "জানান",
    "বলেন",
    "জানিয়ে",
    "অভিযোগ",
    "দাবি",
    "সরব",
    "হুঁশিয়ারি",
    "হুঁশিয়ারি",
)


def segment_narration(script: str, alignment: AlignmentResult) -> list[NarrationSegment]:
    """Split the reporter script into news ideas. Whisper only supplies clocks."""
    duration = max(alignment.duration, 0.01)
    sentences = _script_sentences(script)
    if not sentences:
        return []
    windows = _sentence_times(sentences, alignment, duration)
    segments: list[NarrationSegment] = []
    for index, (text, start, end) in enumerate(windows):
        entities = _entities(text)
        kind = _segment_type(text, index, len(windows))
        location = next((token for token in entities if any(mark in token for mark in LOCATION_MARKERS)), None)
        requirements = list(entities)
        if kind == "location":
            requirements.append("establishing shot")
        if kind == "hook":
            requirements.append("opening visual")
        segments.append(
            NarrationSegment(
                id=f"narration_{index + 1:02d}",
                start=round(start, 3),
                end=round(end, 3),
                text=text,
                type=kind,
                summary=text,
                entities=entities,
                actions=_actions(text, kind),
                location=location,
                visual_requirements=requirements,
                audio_intent=_audio_intent(text, kind),
            )
        )
    if segments:
        segments[0].start = 0.0
        segments[-1].end = round(duration, 3)
    return segments


def _script_sentences(script: str) -> list[str]:
    cleaned = SPACE.sub(" ", script).strip()
    parts = [part.strip() for part in SENTENCE_END.split(cleaned) if part.strip()]
    return parts or ([cleaned] if cleaned else [])


def _sentence_times(
    sentences: list[str], alignment: AlignmentResult, duration: float
) -> list[tuple[str, float, float]]:
    if not alignment.cues or alignment.match_ratio < 0.35:
        return _proportional_times(sentences, duration)
    remaining = list(alignment.cues)
    windows: list[tuple[str, float, float]] = []
    for index, sentence in enumerate(sentences):
        used = _cues_for_sentence(sentence, remaining, last=index == len(sentences) - 1)
        if not used:
            continue
        start = used[0].start if not windows else windows[-1][2]
        end = used[-1].end
        if end <= start:
            end = start + 0.4
        windows.append((sentence, start, end))
    if windows:
        windows[0] = (windows[0][0], 0.0, windows[0][2])
        last = windows[-1]
        windows[-1] = (last[0], last[1], duration)
    return windows or _proportional_times(sentences, duration)


def _cues_for_sentence(sentence: str, remaining: list, last: bool) -> list:
    if last:
        used = list(remaining)
        remaining.clear()
        return used
    used = []
    target = set(normalize_token(token) for token in sentence.split() if normalize_token(token))
    while remaining:
        cue = remaining[0]
        used.append(remaining.pop(0))
        if cue.text.rstrip().endswith(("।", "!", "?")):
            break
        cue_tokens = set(normalize_token(token) for token in cue.text.split() if normalize_token(token))
        if target and cue_tokens and cue_tokens <= target and len(" ".join(item.text for item in used)) >= min(len(sentence), 24):
            break
    return used


def _proportional_times(sentences: list[str], duration: float) -> list[tuple[str, float, float]]:
    weights = [max(len(sentence), 1) for sentence in sentences]
    total = sum(weights)
    cursor = 0.0
    windows = []
    for index, (sentence, weight) in enumerate(zip(sentences, weights, strict=True)):
        end = duration if index == len(sentences) - 1 else cursor + duration * (weight / total)
        windows.append((sentence, cursor, end))
        cursor = end
    return windows


def _entities(text: str) -> list[str]:
    found: list[str] = []
    for token in text.split():
        clean = token.strip("-,;:।!?\"'")
        key = normalize_token(clean)
        if len(key) < 3 or key in STOP:
            continue
        if clean not in found:
            found.append(clean)
    return found[:8]


def _segment_type(text: str, index: int, total: int) -> str:
    if index == 0:
        return "hook"
    if any(mark in text for mark in QUOTE_MARKERS):
        return "quote"
    if any(mark in text for mark in LOCATION_MARKERS):
        return "location"
    if index == total - 1:
        return "close"
    return "event"


def _audio_intent(text: str, kind: str) -> str:
    """Reporter keeps talking unless the line hands the story to a person on camera."""
    if kind == "hook":
        return "script"
    if any(mark in text for mark in SOUNDBITE_MARKERS):
        return "soundbite"
    if kind == "quote":
        return "soundbite"
    return "script"


def _actions(text: str, kind: str) -> list[str]:
    if "যুক্ত" in text:
        return ["new equipment arrives"]
    if kind == "location":
        return ["establishing location"]
    if kind == "quote":
        return ["official speaks"]
    return ["news event"]
