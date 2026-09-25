import pytest

from app.schemas import AlignmentResult, CaptionCue
from app.services.timeline_builder import TimelineBuildError, build_edit_plan


def _alignment(duration: float = 12.0) -> AlignmentResult:
    return AlignmentResult(
        duration=duration,
        script_authoritative=True,
        match_ratio=0.8,
        cues=[
            CaptionCue(start=0, end=6, text="দুর্গাপুরে নতুন ফায়ার টেন্ডার"),
            CaptionCue(start=6, end=duration, text="সক্ষমতা আরও বাড়ল"),
        ],
    )


def _clip(name: str, duration: float, orientation: str = "landscape") -> dict:
    return {
        "filename": name,
        "duration": duration,
        "orientation": orientation,
        "usable_start": 0.25,
        "usable_end": duration - 0.15,
        "crop_mode": "blur-background" if orientation == "landscape" else "center-crop",
    }


def test_timeline_covers_voice_with_uploaded_clips_only() -> None:
    plan = build_edit_plan(
        {"title": "দুর্গাপুরে নতুন টেন্ডার", "location": "দুর্গাপুর", "reporter_name": ""},
        {"clips": [_clip("clip01.mp4", 8), _clip("clip02.mp4", 9)]},
        _alignment(12),
    )
    assert plan.duration == 12
    assert abs(plan.timeline[-1].end - 12) < 0.02
    assert {clip.source for clip in plan.timeline} <= {"clip01.mp4", "clip02.mp4"}
    assert plan.captions[0].text == "দুর্গাপুরে নতুন ফায়ার টেন্ডার"
    assert all(clip.crop_mode == "blur-background" for clip in plan.timeline)
    assert plan.crop_mode == "blur-background"
    for clip in plan.timeline:
        assert abs((clip.end - clip.start) - (clip.source_end - clip.source_start)) < 0.15
        assert clip.source_start >= 0.25


def test_timeline_does_not_invent_missing_sources() -> None:
    plan = build_edit_plan(
        {"title": "শিরোনাম"},
        {"clips": [_clip("clip01.mp4", 20)]},
        _alignment(10),
    )
    assert all(clip.source == "clip01.mp4" for clip in plan.timeline)


def test_timeline_warns_when_footage_must_repeat() -> None:
    plan = build_edit_plan(
        {"title": "শিরোনাম"},
        {"clips": [_clip("clip04.mp4", 4)]},
        _alignment(10),
    )
    assert plan.footage_warning
    assert plan.timeline[-1].end == 10


def test_timeline_rejects_empty_footage() -> None:
    with pytest.raises(TimelineBuildError):
        build_edit_plan({"title": "শিরোনাম"}, {"clips": []}, _alignment(8))
