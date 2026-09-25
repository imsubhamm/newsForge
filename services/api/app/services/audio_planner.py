from __future__ import annotations

from app.config import Settings, get_settings
from app.schemas import (
    AlignmentResult,
    AudioCandidateDebug,
    AudioComparison,
    AudioMatchDebug,
    AudioMode,
    AudioSegment,
    CaptionCue,
    ClipAudio,
    NarrationSegment,
    SemanticDebug,
    TimelineClip,
    TimelinePlan,
)
from app.services.alignment import normalize_token


NAT_TYPES = {"natural_sound", "ambient_sound"}
BITE_TYPES = {
    "soundbite",
    "local_resident_bite",
    "eyewitness_bite",
    "official_statement",
    "reporter_standup",
    "interview",
    "reaction",
    "voiceover_candidate",
}


def apply_audio_editorial(
    plan: TimelinePlan,
    narration: list[NarrationSegment],
    segments: list[AudioSegment],
    alignment: AlignmentResult,
    settings: Settings | None = None,
) -> tuple[TimelinePlan, list[AudioMatchDebug]]:
    settings = settings or get_settings()
    used: set[str] = set()
    rebuilt: list[TimelineClip] = []
    matches: list[AudioMatchDebug] = []
    nat_break_used = False

    for segment in narration:
        originals = [clip for clip in plan.timeline if clip.narration_segment_id == segment.id]
        if not originals:
            continue
        ranked = _rank_audio(segment, segments, used)
        decision = _decide(segment, ranked, segments, settings, allow_nat_break=not nat_break_used)
        matches.append(_debug_row(segment, ranked, decision, segments))

        cursor = rebuilt[-1].end if rebuilt else 0.0
        if decision["mode"] == "SOURCE_SOUNDBITE" and decision["action"] == "REPLACE_VOICEOVER":
            bite = _by_id(segments, decision["audio_id"])
            used.add(bite.id)
            rebuilt.append(_bite_clip(cursor, originals[0], bite, segment, decision, settings, replace=True))
        elif decision["mode"] == "SOURCE_SOUNDBITE" and decision["action"] == "INSERT_AFTER":
            rebuilt.extend(_keep_voice_clips(cursor, originals, "VOICEOVER_ONLY", settings, "KEEP_VOICEOVER", decision["reason"]))
            cursor = rebuilt[-1].end
            bite = _by_id(segments, decision["audio_id"])
            used.add(bite.id)
            rebuilt.append(_bite_clip(cursor, originals[-1], bite, segment, decision, settings, replace=False))
        elif decision["mode"] == "VOICEOVER_WITH_NAT_SOUND":
            nat = _by_id(segments, decision["audio_id"]) if decision.get("audio_id") else None
            if nat:
                used.add(nat.id)
            rebuilt.extend(_nat_under_voice(cursor, originals, nat, decision, settings))
        elif decision["mode"] == "NAT_SOUND_ONLY":
            rebuilt.extend(_keep_voice_clips(cursor, originals, "VOICEOVER_ONLY", settings, "KEEP_VOICEOVER", ""))
            cursor = rebuilt[-1].end
            nat = _by_id(segments, decision["audio_id"])
            used.add(nat.id)
            nat_break_used = True
            rebuilt.append(_nat_break_clip(cursor, originals[-1], nat, segment, decision, settings))
        else:
            rebuilt.extend(_keep_voice_clips(cursor, originals, "VOICEOVER_ONLY", settings, "KEEP_VOICEOVER", decision["reason"]))

    if not rebuilt:
        return plan, matches

    duration = round(rebuilt[-1].end, 3)
    captions = _rebuild_captions(rebuilt, alignment, segments)
    updated = plan.model_copy(
        update={
            "duration": duration,
            "timeline": rebuilt,
            "captions": captions,
            "editor": "semantic+audio",
        }
    )
    return TimelinePlan.model_validate(updated.model_dump()), matches


def apply_audio_override(plan: TimelinePlan, clip_index: int, mode: AudioMode, settings: Settings | None = None) -> TimelinePlan:
    settings = settings or get_settings()
    if clip_index >= len(plan.timeline):
        raise ValueError("clip_index is out of range")
    clip = plan.timeline[clip_index]
    audio = clip.audio.model_copy()
    audio.mode = mode
    audio.override = True
    audio.editorial_action = "MANUAL_OVERRIDE"
    audio.reason = "Editor changed the audio block before render."
    if mode == "VOICEOVER_ONLY":
        audio.voiceover_enabled = True
        audio.voice_volume = 1.0
        audio.source_volume = 0.0
    elif mode == "SOURCE_SOUNDBITE":
        audio.voiceover_enabled = False
        audio.voice_volume = 0.0
        audio.source_volume = 1.0
        audio.source = clip.source
        audio.source_start = clip.source_start
        audio.source_end = clip.source_end
    elif mode == "VOICEOVER_WITH_NAT_SOUND":
        audio.voiceover_enabled = True
        audio.voice_volume = 1.0
        audio.source_volume = settings.nat_sound_volume
        audio.source = clip.source
        audio.source_start = clip.source_start
        audio.source_end = clip.source_end
    else:
        audio.voiceover_enabled = False
        audio.voice_volume = 0.0
        audio.source_volume = 0.85
        audio.source = clip.source
        audio.source_start = clip.source_start
        audio.source_end = clip.source_end
    plan.timeline[clip_index] = clip.model_copy(update={"audio": audio})
    return TimelinePlan.model_validate(plan.model_dump())


def attach_audio_debug(debug: SemanticDebug, matches: list[AudioMatchDebug]) -> SemanticDebug:
    return debug.model_copy(update={"audio_matches": matches, "duration": debug.duration})


def compare_audio(segment: NarrationSegment, item: AudioSegment) -> AudioComparison:
    overlap = _overlap(segment.text, item.transcript)
    relevance = overlap
    if overlap >= 0.15:
        relevance = min(1.0, overlap + 0.15 * item.news_relevance)
    unique = max(0.0, 1.0 - overlap) * (1.0 if item.contains_speech else 0.2)
    speaker = 0.85 if item.audio_type in BITE_TYPES else 0.2
    evidence = 0.9 if item.audio_type in BITE_TYPES and relevance >= 0.5 else relevance * 0.5
    return AudioComparison(
        audio_id=item.id,
        semantic_relevance=round(relevance, 3),
        information_overlap=round(overlap, 3),
        unique_information=round(unique, 3),
        evidence_value=round(min(1.0, evidence), 3),
        speaker_value=speaker,
        audio_quality=item.speech_quality if item.contains_speech else min(0.7, 0.35 + item.rms * 4),
    )


def _rank_audio(
    segment: NarrationSegment, items: list[AudioSegment], used: set[str]
) -> list[tuple[AudioComparison, AudioSegment]]:
    ranked: list[tuple[AudioComparison, AudioSegment]] = []
    for item in items:
        comparison = compare_audio(segment, item)
        if item.id in used:
            comparison.semantic_relevance *= 0.35
            comparison.evidence_value *= 0.35
        ranked.append((comparison, item))
    ranked.sort(key=lambda pair: pair[0].semantic_relevance + pair[0].evidence_value + pair[0].audio_quality, reverse=True)
    return ranked


def _decide(
    segment: NarrationSegment,
    ranked: list[tuple[AudioComparison, AudioSegment]],
    _segments: list[AudioSegment],
    settings: Settings,
    allow_nat_break: bool,
) -> dict:
    bite = next((pair for pair in ranked if _usable_bite(pair[0], pair[1], settings)), None)
    nat = next((pair for pair in ranked if pair[1].audio_type in NAT_TYPES and pair[1].rms > 0.01), None)

    if bite:
        comparison, item = bite
        if comparison.audio_quality < settings.bite_quality_min:
            return {
                "mode": "VOICEOVER_ONLY",
                "action": "KEEP_VOICEOVER",
                "audio_id": item.id,
                "reason": "The bite is relevant but audio quality is too poor to use automatically.",
                "needs_review": True,
            }
        if comparison.information_overlap >= settings.bite_overlap_replace:
            return {
                "mode": "SOURCE_SOUNDBITE",
                "action": "REPLACE_VOICEOVER",
                "audio_id": item.id,
                "reason": f"Primary evidence from {item.speaker_type} covers the same ground as the narration.",
                "needs_review": False,
            }
        if comparison.unique_information >= settings.bite_unique_insert and comparison.semantic_relevance >= settings.bite_relevance_min:
            return {
                "mode": "SOURCE_SOUNDBITE",
                "action": "INSERT_AFTER",
                "audio_id": item.id,
                "reason": f"The {item.speaker_type} adds information that the narration does not repeat.",
                "needs_review": False,
            }

    if nat and segment.type in {"hook", "location", "event"}:
        item = nat[1]
        return {
            "mode": "VOICEOVER_WITH_NAT_SOUND",
            "action": "MIX_NAT",
            "audio_id": item.id,
            "reason": "Keep the reporter voice and sit usable natural sound underneath.",
            "needs_review": False,
        }

    return {
        "mode": "VOICEOVER_ONLY",
        "action": "KEEP_VOICEOVER",
        "audio_id": "",
        "reason": "No usable original speech or natural sound beat this narration.",
        "needs_review": False,
    }


def _usable_bite(comparison: AudioComparison, item: AudioSegment, settings: Settings) -> bool:
    if not item.contains_speech:
        return False
    if item.audio_type in {"irrelevant_speech", "unusable_audio", "background_chatter"}:
        return False
    if comparison.semantic_relevance < settings.bite_relevance_min:
        return False
    return item.audio_type in BITE_TYPES or comparison.evidence_value >= 0.7


def _keep_voice_clips(
    cursor: float,
    originals: list[TimelineClip],
    mode: AudioMode,
    settings: Settings,
    action: str,
    reason: str,
) -> list[TimelineClip]:
    clips: list[TimelineClip] = []
    head = cursor
    for original in originals:
        span = round(original.end - original.start, 3)
        clips.append(
            original.model_copy(
                update={
                    "start": round(head, 3),
                    "end": round(head + span, 3),
                    "audio": ClipAudio(
                        mode=mode,
                        voiceover_enabled=True,
                        voiceover_start=original.start,
                        voiceover_end=original.end,
                        source=None,
                        voice_volume=1.0,
                        source_volume=0.0,
                        editorial_action=action,
                        reason=reason or "Reporter voice-over carries this beat.",
                    ),
                }
            )
        )
        head += span
    return clips


def _nat_under_voice(
    cursor: float,
    originals: list[TimelineClip],
    nat: AudioSegment | None,
    decision: dict,
    settings: Settings,
) -> list[TimelineClip]:
    clips: list[TimelineClip] = []
    head = cursor
    for original in originals:
        span = round(original.end - original.start, 3)
        audio_source = nat.source_file if nat else original.source
        audio_start = nat.start if nat else original.source_start
        audio_end = nat.end if nat else original.source_end
        clips.append(
            original.model_copy(
                update={
                    "start": round(head, 3),
                    "end": round(head + span, 3),
                    "audio": ClipAudio(
                        mode="VOICEOVER_WITH_NAT_SOUND",
                        voiceover_enabled=True,
                        voiceover_start=original.start,
                        voiceover_end=original.end,
                        source=audio_source,
                        source_start=audio_start,
                        source_end=audio_end,
                        voice_volume=1.0,
                        source_volume=settings.nat_sound_volume * (nat.playback_gain if nat else 1.0),
                        editorial_action=decision["action"],
                        reason=decision["reason"],
                        audio_segment_id=nat.id if nat else "",
                    ),
                }
            )
        )
        head += span
    return clips


def _bite_clip(
    cursor: float,
    template: TimelineClip,
    bite: AudioSegment,
    segment: NarrationSegment,
    decision: dict,
    settings: Settings,
    replace: bool,
) -> TimelineClip:
    span = round(bite.end - bite.start, 3)
    return TimelineClip(
        start=round(cursor, 3),
        end=round(cursor + span, 3),
        source=bite.source_file,
        source_start=bite.start,
        source_end=bite.end,
        reason=decision["reason"],
        crop_mode=template.crop_mode,
        match_score=max(template.match_score, 0.8),
        needs_review=bool(decision.get("needs_review") or bite.speech_quality < settings.bite_quality_min),
        narration_segment_id=segment.id,
        scene_id=template.scene_id,
        audio=ClipAudio(
            mode="SOURCE_SOUNDBITE",
            voiceover_enabled=False,
            voiceover_start=None,
            voiceover_end=None,
            source=bite.source_file,
            source_start=bite.start,
            source_end=bite.end,
            voice_volume=0.0,
            source_volume=round(min(1.0, bite.playback_gain), 3),
            editorial_action=decision["action"],
            reason=decision["reason"],
            audio_segment_id=bite.id,
            needs_review=bool(decision.get("needs_review")),
        ),
    )


def _nat_break_clip(
    cursor: float,
    template: TimelineClip,
    nat: AudioSegment,
    segment: NarrationSegment,
    decision: dict,
    settings: Settings,
) -> TimelineClip:
    span = min(2.2, nat.end - nat.start)
    return TimelineClip(
        start=round(cursor, 3),
        end=round(cursor + span, 3),
        source=nat.source_file,
        source_start=nat.start,
        source_end=round(nat.start + span, 3),
        reason=decision["reason"],
        crop_mode=template.crop_mode,
        match_score=template.match_score,
        narration_segment_id=segment.id,
        scene_id=template.scene_id,
        audio=ClipAudio(
            mode="NAT_SOUND_ONLY",
            voiceover_enabled=False,
            source=nat.source_file,
            source_start=nat.start,
            source_end=round(nat.start + span, 3),
            voice_volume=0.0,
            source_volume=round(min(0.9, 0.7 * nat.playback_gain), 3),
            editorial_action="INSERT_AFTER",
            reason=decision["reason"],
            audio_segment_id=nat.id,
        ),
    )


def _rebuild_captions(
    clips: list[TimelineClip],
    alignment: AlignmentResult,
    segments: list[AudioSegment],
) -> list[CaptionCue]:
    cues: list[CaptionCue] = []
    for clip in clips:
        audio = clip.audio
        if audio.mode == "SOURCE_SOUNDBITE":
            bite = _by_id(segments, audio.audio_segment_id) if audio.audio_segment_id else None
            text = (bite.transcript if bite else "").strip()
            if text:
                cues.append(
                    CaptionCue(
                        start=clip.start,
                        end=clip.end,
                        text=text,
                        source="VIDEO_SOUNDBITE",
                    )
                )
            continue
        if not audio.voiceover_enabled or audio.voice_volume <= 0:
            continue
        vo_start = audio.voiceover_start if audio.voiceover_start is not None else clip.start
        vo_end = audio.voiceover_end if audio.voiceover_end is not None else clip.end
        for cue in alignment.cues:
            latest = max(cue.start, vo_start)
            earliest = min(cue.end, vo_end)
            if earliest - latest <= 0.12:
                continue
            cues.append(
                CaptionCue(
                    start=round(clip.start + (latest - vo_start), 3),
                    end=round(clip.start + (earliest - vo_start), 3),
                    text=cue.text,
                    source="REPORTER_SCRIPT",
                )
            )
    return cues


def _debug_row(
    segment: NarrationSegment,
    ranked: list[tuple[AudioComparison, AudioSegment]],
    decision: dict,
    _segments: list[AudioSegment],
) -> AudioMatchDebug:
    selected_id = decision.get("audio_id") or ""
    candidates: list[AudioCandidateDebug] = []
    for comparison, item in ranked[:8]:
        if item.audio_type in {"irrelevant_speech", "unusable_audio", "background_chatter"}:
            mark = "MUTE"
        elif item.id == selected_id and decision["mode"] == "SOURCE_SOUNDBITE":
            mark = "USE_BITE"
        elif item.id == selected_id and decision["mode"] in {"VOICEOVER_WITH_NAT_SOUND", "NAT_SOUND_ONLY"}:
            mark = "USE_NAT"
        else:
            mark = "MUTE"
        candidates.append(
            AudioCandidateDebug(
                audio_id=item.id,
                source_file=item.source_file,
                speaker_type=item.speaker_type,
                audio_type=item.audio_type,
                transcript=item.transcript,
                relevance=comparison.semantic_relevance,
                quality=comparison.audio_quality,
                decision=mark,
                action=decision["action"] if item.id == selected_id else "",
                selected=item.id == selected_id,
            )
        )
    return AudioMatchDebug(
        narration_segment_id=segment.id,
        text=segment.text,
        start=segment.start,
        end=segment.end,
        mode=decision["mode"],
        action=decision["action"],
        reason=decision["reason"],
        candidates=candidates,
    )


def _by_id(segments: list[AudioSegment], audio_id: str) -> AudioSegment:
    return next(item for item in segments if item.id == audio_id)


def _overlap(left: str, right: str) -> float:
    a = _tokens(left)
    b = _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / max(len(a), 1)


def _tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in (text or "").replace(",", " ").split():
        key = normalize_token(raw)
        if len(key) >= 3:
            tokens.add(key)
    return tokens
