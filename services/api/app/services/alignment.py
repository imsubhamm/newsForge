from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.schemas import AlignmentResult, CaptionCue, Transcript, TranscriptWord
from app.services.subtitles import segment_bengali_script

PUNCT = re.compile(r"[।!?,;:\"'`“”‘’()\[\]{}।,.…\-—–/\\|]+")
SPACE = re.compile(r"\s+")


def align_script_to_transcript(script: str, transcript: Transcript, max_chars: int = 28) -> AlignmentResult:
    """Time the reporter's original script using Whisper word clocks.

    Whisper spelling is never written into the cues.
    """
    duration = max(transcript.duration, transcript.words[-1].end if transcript.words else 0, 0.01)
    phrases = segment_bengali_script(script, max_chars=max_chars)
    if not phrases:
        return AlignmentResult(duration=duration, cues=[], match_ratio=0)

    script_tokens = _tokenize(SPACE.sub(" ", script).strip())
    whisper_words = [word for word in transcript.words if normalize_token(word.text)]
    mapping, match_ratio = _map_tokens(script_tokens, whisper_words)

    if _unusable_whisper_clocks(script_tokens, whisper_words, match_ratio):
        token_times = _proportional_token_times(script_tokens, duration)
    elif match_ratio < 0.35 and whisper_words:
        token_times = _index_mapped_token_times(script_tokens, whisper_words, duration)
    else:
        token_times = _times_for_tokens(script_tokens, mapping, whisper_words, duration)
    cues = _phrases_to_cues(phrases, script_tokens, token_times, duration)
    return AlignmentResult(
        script_authoritative=True,
        match_ratio=round(match_ratio, 3),
        duration=round(duration, 3),
        cues=cues,
        source="whisper+script",
    )


def normalize_token(text: str) -> str:
    """Compare tokens in Bengali letters so Hindi-script Whisper still times the script."""
    mapped = "".join(_indic_letter(char) for char in text)
    return PUNCT.sub("", mapped).strip().casefold()


def _indic_letter(char: str) -> str:
    code = ord(char)
    if 0x0900 <= code <= 0x097F:
        return chr(code + 0x80)
    return char


def _tokenize(script: str) -> list[str]:
    return [part for part in SPACE.split(script) if part]


def _similar(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    if left in right or right in left:
        return len(min(left, right, key=len)) >= 3
    return SequenceMatcher(None, left, right).ratio() >= 0.72


def _map_tokens(script_tokens: list[str], words: list[TranscriptWord]) -> tuple[list[int | None], float]:
    mapping: list[int | None] = []
    cursor = 0
    matched = 0
    for token in script_tokens:
        needle = normalize_token(token)
        found: int | None = None
        if needle:
            limit = min(len(words), cursor + 16)
            for index in range(cursor, limit):
                if _similar(needle, normalize_token(words[index].text)):
                    found = index
                    break
        if found is not None:
            mapping.append(found)
            cursor = found + 1
            matched += 1
        else:
            mapping.append(None)
    ratio = matched / max(len(script_tokens), 1)
    return mapping, ratio


def _times_for_tokens(
    script_tokens: list[str],
    mapping: list[int | None],
    words: list[TranscriptWord],
    duration: float,
) -> list[tuple[float, float]]:
    times: list[tuple[float, float]] = [(0.0, 0.0)] * len(script_tokens)
    for index, word_index in enumerate(mapping):
        if word_index is None:
            continue
        word = words[word_index]
        times[index] = (word.start, max(word.end, word.start + 0.04))

    known = [index for index, word_index in enumerate(mapping) if word_index is not None]
    if not known:
        if words:
            return _index_mapped_token_times(script_tokens, words, duration)
        return _proportional_token_times(script_tokens, duration)

    if known[0] != 0:
        first_start = times[known[0]][0]
        span = first_start / known[0] if known[0] else first_start
        cursor = 0.0
        for index in range(known[0]):
            end = first_start if index == known[0] - 1 else cursor + span
            times[index] = (cursor, end)
            cursor = end

    for left, right in zip(known, known[1:], strict=False):
        if right == left + 1:
            continue
        start = times[left][1]
        end = times[right][0]
        gap = right - left
        step = max(end - start, 0.04) / gap
        cursor = start
        for index in range(left + 1, right):
            nxt = cursor + step
            times[index] = (cursor, nxt)
            cursor = nxt

    if known[-1] != len(script_tokens) - 1:
        start = times[known[-1]][1]
        remaining = len(script_tokens) - known[-1] - 1
        step = max(duration - start, 0.04) / remaining
        cursor = start
        for offset, index in enumerate(range(known[-1] + 1, len(script_tokens))):
            nxt = duration if offset == remaining - 1 else cursor + step
            times[index] = (cursor, nxt)
            cursor = nxt
    return times


def _unusable_whisper_clocks(
    script_tokens: list[str], words: list[TranscriptWord], match_ratio: float
) -> bool:
    """Garbage or sparse ASR clocks cannot drive a news cut."""
    if not words:
        return True
    if match_ratio < 0.35 and len(words) < max(8, int(len(script_tokens) * 0.25)):
        return True
    return max(word.end - word.start for word in words) > 8.0


def _index_mapped_token_times(
    script_tokens: list[str],
    words: list[TranscriptWord],
    duration: float,
) -> list[tuple[float, float]]:
    """Use Whisper clocks in order when spelling is too far from the reporter script."""
    count = max(len(script_tokens), 1)
    word_count = len(words)
    times: list[tuple[float, float]] = []
    for index in range(count):
        start_index = min(int(index * word_count / count), word_count - 1)
        end_index = min(max(start_index, int((index + 1) * word_count / count) - 1), word_count - 1)
        start = words[start_index].start
        end = words[end_index].end
        if index == 0:
            start = 0.0
        if index == count - 1:
            end = max(end, duration)
        times.append((start, max(end, start + 0.04)))
    return times


def _proportional_token_times(script_tokens: list[str], duration: float) -> list[tuple[float, float]]:
    weights = [max(len(normalize_token(token)), 1) for token in script_tokens]
    total = sum(weights)
    cursor = 0.0
    times: list[tuple[float, float]] = []
    for index, weight in enumerate(weights):
        end = duration if index == len(weights) - 1 else cursor + duration * (weight / total)
        times.append((cursor, end))
        cursor = end
    return times


def _phrases_to_cues(
    phrases: list[str],
    script_tokens: list[str],
    token_times: list[tuple[float, float]],
    duration: float,
) -> list[CaptionCue]:
    token_cursor = 0
    cues: list[CaptionCue] = []
    for phrase_index, phrase in enumerate(phrases):
        count = len(_tokenize(phrase))
        if count <= 0:
            continue
        start_index = min(token_cursor, len(token_times) - 1)
        end_index = min(token_cursor + count - 1, len(token_times) - 1)
        start = token_times[start_index][0]
        end = token_times[end_index][1]
        if phrase_index == len(phrases) - 1:
            end = max(end, duration)
        if end <= start:
            end = start + 0.2
        cues.append(CaptionCue(start=round(start, 3), end=round(end, 3), text=phrase))
        token_cursor += count
    if cues:
        cues[0].start = 0.0
        cues[-1].end = round(max(cues[-1].end, duration), 3)
    return cues
