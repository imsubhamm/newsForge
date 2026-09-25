from __future__ import annotations

from app.config import Settings, get_settings
from app.schemas import (
    AlignmentResult,
    CaptionCue,
    NarrationMatchDebug,
    NarrationSegment,
    SemanticDebug,
    TimelineClip,
    TimelinePlan,
    VisualScene,
)
from app.services.matcher import rank_candidates
from app.services.timeline_builder import TimelineBuildError


def plan_from_payload(payload: dict, settings: Settings | None = None) -> TimelinePlan:
    plan, _debug = build_semantic_plan(payload, settings)
    return plan


def build_semantic_plan(
    payload: dict, settings: Settings | None = None
) -> tuple[TimelinePlan, SemanticDebug]:
    settings = settings or get_settings()
    metadata = payload.get("metadata") or {}
    alignment = AlignmentResult.model_validate(payload.get("alignment") or {})
    narration = [NarrationSegment.model_validate(item) for item in payload.get("narration") or []]
    scenes = [VisualScene.model_validate(item) for item in payload.get("scenes") or []]
    if not narration:
        raise TimelineBuildError("no narration segments to edit against")
    if not scenes:
        raise TimelineBuildError("no visual scenes were detected")

    duration = round(max(alignment.duration, narration[-1].end, 0.01), 3)
    usage: dict[str, int] = {}
    recent: list[str] = []
    used_ranges: list[tuple[str, float, float]] = []
    clips: list[TimelineClip] = []
    matches: list[NarrationMatchDebug] = []
    warning: str | None = None
    repeats = 0

    for segment in narration:
        remaining = max(segment.end - max(segment.start, clips[-1].end if clips else 0.0), 0.0)
        cursor = clips[-1].end if clips else segment.start
        if cursor < segment.start:
            cursor = segment.start
        candidates = rank_candidates(segment, scenes, usage, recent, used_ranges)
        selected_ids: set[str] = set()
        while remaining > 0.08:
            available = [item for item in candidates if item.scene_id not in selected_ids]
            if not available:
                warning = "Footage is thinner than the voice-over; some scenes are reused."
                repeats += 1
                if repeats > 12:
                    raise TimelineBuildError("could not cover the narration with detected scenes")
                selected_ids.clear()
                available = candidates
            pick = available[0]
            scene = next(item for item in scenes if item.scene_id == pick.scene_id)
            take = _take_range(scene, remaining, settings)
            if take is None:
                selected_ids.add(scene.scene_id)
                if len(selected_ids) >= len(scenes):
                    remaining = 0
                continue
            source_start, source_end = take
            span = round(source_end - source_start, 3)
            end = duration if cursor + span >= duration - 0.05 and segment.id == narration[-1].id else round(cursor + span, 3)
            actual = round(end - cursor, 3)
            source_end = round(source_start + actual, 3)
            score = pick.score
            clips.append(
                TimelineClip(
                    start=round(cursor, 3),
                    end=end,
                    source=scene.source_file,
                    source_start=round(source_start, 3),
                    source_end=source_end,
                    reason=pick.reason,
                    crop_mode=scene.crop_mode,
                    match_score=score,
                    needs_review=score < settings.match_threshold,
                    narration_segment_id=segment.id,
                    scene_id=scene.scene_id,
                )
            )
            usage[scene.scene_id] = usage.get(scene.scene_id, 0) + 1
            recent.append(scene.scene_id)
            used_ranges.append((scene.source_file, source_start, source_end))
            selected_ids.add(scene.scene_id)
            cursor = end
            remaining = max(0.0, (segment.end if segment.id != narration[-1].id else duration) - cursor)
            candidates = rank_candidates(segment, scenes, usage, recent, used_ranges)

        if candidates:
            chosen = {clip.scene_id for clip in clips if clip.narration_segment_id == segment.id}
            for candidate in candidates:
                candidate.selected = candidate.scene_id in chosen
            matches.append(
                NarrationMatchDebug(
                    narration_segment_id=segment.id,
                    text=segment.text,
                    start=segment.start,
                    end=segment.end,
                    candidates=candidates[:8],
                )
            )

    if clips:
        clips[-1].end = duration
        clips[-1].source_end = round(clips[-1].source_start + (clips[-1].end - clips[-1].start), 3)

    plan = TimelinePlan.model_validate(
        {
            "headline": metadata.get("title") or "",
            "location": metadata.get("location") or "",
            "reporter_name": metadata.get("reporter_name") or "",
            "duration": duration,
            "crop_mode": "blur-background"
            if any(scene.crop_mode == "blur-background" for scene in scenes)
            else "center-crop",
            "timeline": [clip.model_dump() for clip in clips],
            "captions": [CaptionCue.model_validate(cue.model_dump()) for cue in alignment.cues],
            "footage_warning": warning,
            "editor": "semantic",
            "weak_match_count": sum(1 for clip in clips if clip.needs_review),
        }
    )
    debug = SemanticDebug(
        duration=duration,
        threshold=settings.match_threshold,
        narration=narration,
        scenes=scenes,
        matches=matches,
    )
    return plan, debug


def _take_range(scene: VisualScene, remaining: float, settings: Settings) -> tuple[float, float] | None:
    available = scene.source_end - scene.source_start
    if available < 0.4:
        return None
    want = remaining
    if remaining > settings.target_cut_max and available > settings.target_cut_min:
        want = min(settings.target_cut_max, remaining, available)
    elif remaining < settings.target_cut_min and available >= remaining:
        want = remaining
    else:
        want = min(max(remaining, settings.target_cut_min), available, remaining)
    want = min(max(want, remaining if remaining < 0.4 else want), available)
    if want < 0.08:
        return None
    pad = max(0.0, (available - want) * 0.2)
    start = scene.source_start + pad
    end = start + want
    if end > scene.source_end:
        end = scene.source_end
        start = end - want
    return start, end
