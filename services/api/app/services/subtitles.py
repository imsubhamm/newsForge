from __future__ import annotations

import re

from app.schemas import CaptionCue

SPLIT_PATTERN = re.compile(r"(?<=[।!?\n,;])\s+|\s{2,}")
WHITESPACE = re.compile(r"\s+")


def segment_bengali_script(script: str, max_chars: int = 28) -> list[str]:
    cleaned = WHITESPACE.sub(" ", script).strip()
    if not cleaned:
        return []

    pieces = [part.strip(" \n\t-") for part in SPLIT_PATTERN.split(cleaned) if part.strip()]
    if not pieces:
        pieces = [cleaned]

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if not current:
            current = piece
            continue
        candidate = f"{current} {piece}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.extend(_split_long(current, max_chars))
            current = piece
    if current:
        chunks.extend(_split_long(current, max_chars))
    return [chunk for chunk in chunks if chunk]


def cues_from_script(script: str, duration: float, max_chars: int = 28) -> list[CaptionCue]:
    if duration <= 0:
        raise ValueError("duration must be positive")
    chunks = segment_bengali_script(script, max_chars=max_chars)
    if not chunks:
        return []
    weights = [max(len(chunk), 1) for chunk in chunks]
    total = sum(weights)
    cursor = 0.0
    cues: list[CaptionCue] = []
    for index, (chunk, weight) in enumerate(zip(chunks, weights, strict=True)):
        span = duration * (weight / total)
        end = duration if index == len(chunks) - 1 else cursor + span
        cues.append(CaptionCue(start=round(cursor, 3), end=round(end, 3), text=chunk))
        cursor = end
    return cues


def _split_long(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    words = text.split(" ")
    out: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                out.append(current)
            current = word
    if current:
        out.append(current)
    return out
