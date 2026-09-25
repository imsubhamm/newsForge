from __future__ import annotations

from app.schemas import AlignmentResult, CaptionCue, TimelineClip, TimelinePlan

TARGET_CUT = 6.0
MIN_CUT = 1.0


class TimelineBuildError(RuntimeError):
    pass


def plan_from_payload(payload: dict) -> TimelinePlan:
    metadata = payload.get("metadata") or {}
    footage = payload.get("footage") or {}
    alignment = AlignmentResult.model_validate(payload.get("alignment") or {})
    return build_edit_plan(metadata, footage, alignment)


def build_edit_plan(metadata: dict, footage: dict, alignment: AlignmentResult) -> TimelinePlan:
    duration = round(max(alignment.duration, 0.01), 3)
    clips = [clip for clip in footage.get("clips", []) if _usable_length(clip) >= MIN_CUT]
    if not clips:
        raise TimelineBuildError("no usable footage remains for the voice-over")

    pools = [_ClipWindow(clip) for clip in clips]
    timeline: list[TimelineClip] = []
    cursor = 0.0
    warning: str | None = None
    repeats = 0
    rotate = 0

    while cursor < duration - 0.02:
        remaining = duration - cursor
        want = remaining if remaining <= TARGET_CUT * 1.35 else min(TARGET_CUT, remaining)
        window = _next_window(pools, want, rotate)
        if window is None:
            for pool in pools:
                pool.reset()
            repeats += 1
            if repeats > 8:
                raise TimelineBuildError("could not cover the voice-over with the uploaded clips")
            warning = "Footage is shorter than the voice-over, so some uploaded clips are repeated."
            window = _next_window(pools, want, 0)
            if window is None:
                raise TimelineBuildError("uploaded clips are too short to edit")
        pool, source_start, source_end, rotate = window
        span = round(source_end - source_start, 3)
        end = duration if remaining - span <= 0.02 else round(cursor + span, 3)
        actual = round(end - cursor, 3)
        source_end = round(source_start + actual, 3)
        timeline.append(
            TimelineClip(
                start=round(cursor, 3),
                end=end,
                source=pool.filename,
                source_start=round(source_start, 3),
                source_end=source_end,
                reason=pool.reason,
                crop_mode=pool.crop_mode,
            )
        )
        cursor = end

    crop_mode = "blur-background" if any(pool.orientation == "landscape" for pool in pools) else "center-crop"
    captions = [
        CaptionCue(start=cue.start, end=cue.end, text=cue.text)
        for cue in alignment.cues
        if cue.text.strip()
    ]
    return TimelinePlan.model_validate(
        {
            "headline": metadata.get("title") or "",
            "location": metadata.get("location") or "",
            "reporter_name": metadata.get("reporter_name") or "",
            "duration": duration,
            "crop_mode": crop_mode,
            "timeline": [clip.model_dump() for clip in timeline],
            "captions": [cue.model_dump() for cue in captions],
            "footage_warning": warning,
        }
    )


def _usable_length(clip: dict) -> float:
    return max(0.0, float(clip.get("usable_end") or 0) - float(clip.get("usable_start") or 0))


class _ClipWindow:
    def __init__(self, clip: dict):
        self.filename = clip["filename"]
        self.orientation = clip.get("orientation") or "unknown"
        self.crop_mode = clip.get("crop_mode") or "center-crop"
        self.usable_start = float(clip["usable_start"])
        self.usable_end = float(clip["usable_end"])
        self.cursor = self.usable_start
        duration = float(clip.get("duration") or self.usable_end)
        self.reason = (
            f"Uploaded clip {self.filename} ({self.orientation}, {duration:.1f}s). "
            "No invented scene description."
        )

    def remaining(self) -> float:
        return max(0.0, self.usable_end - self.cursor)

    def take(self, want: float) -> tuple[float, float] | None:
        left = self.remaining()
        if left < MIN_CUT and left < want:
            return None
        span = min(max(want, MIN_CUT), left)
        if span < 0.4:
            return None
        start = self.cursor
        end = start + span
        self.cursor = end
        return start, end

    def reset(self) -> None:
        self.cursor = self.usable_start


def _next_window(
    pools: list[_ClipWindow], want: float, rotate: int
) -> tuple[_ClipWindow, float, float, int] | None:
    count = len(pools)
    for offset in range(count):
        index = (rotate + offset) % count
        taken = pools[index].take(want)
        if taken is None:
            continue
        return pools[index], taken[0], taken[1], index + 1
    return None
