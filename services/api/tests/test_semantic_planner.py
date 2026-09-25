from app.schemas import AlignmentResult, CaptionCue, NarrationSegment, VisualScene
from app.services.semantic_planner import build_semantic_plan


def _scene(scene_id: str, source: str, start: float, end: float, **kwargs) -> dict:
    payload = {
        "scene_id": scene_id,
        "source_file": source,
        "source_start": start,
        "source_end": end,
        "duration": round(end - start, 3),
        "description": kwargs.get("description", ""),
        "subjects": kwargs.get("subjects", []),
        "actions": kwargs.get("actions", []),
        "environment": kwargs.get("environment", []),
        "quality_score": 0.8,
        "stability_score": 0.8,
        "visual_interest_score": 0.8,
        "crop_mode": "blur-background",
    }
    return VisualScene.model_validate(payload).model_dump()


def test_semantic_planner_selects_by_meaning_not_upload_order() -> None:
    narration = [
        NarrationSegment(
            id="narration_01",
            start=0.0,
            end=3.8,
            text="পুজোর কেনাকাটার মাঝে হঠাৎ যদি সামনে এসে পড়ে হনুমান?",
            type="hook",
            entities=["হনুমান", "শপিং"],
            visual_requirements=["হনুমান", "মল"],
        ),
        NarrationSegment(
            id="narration_02",
            start=3.8,
            end=9.0,
            text="হনুমানটি চলন্ত এসকেলেটরের হাতল ধরে উপরে ওঠার চেষ্টা করে।",
            type="event",
            entities=["হনুমান", "এসকেলেটর"],
            visual_requirements=["এসকেলেটর", "হনুমান"],
        ),
        NarrationSegment(
            id="narration_03",
            start=9.0,
            end=12.5,
            text="নিরাপত্তারক্ষীরা হনুমানটির কাছে এগোয়।",
            type="event",
            entities=["নিরাপত্তা"],
            visual_requirements=["নিরাপত্তা", "security"],
        ),
        NarrationSegment(
            id="narration_04",
            start=12.5,
            end=18.0,
            text="কেনাকাটা থেমে যায়, ভিড় তাকিয়ে থাকে।",
            type="event",
            entities=["ভিড়"],
            visual_requirements=["ভিড়", "crowd"],
        ),
    ]
    scenes = [
        _scene("video1_scene_001", "video1.mp4", 5.2, 9.0, description="হনুমান শপিং মলের ভিতরে", subjects=["হনুমান", "মল"]),
        _scene("video2_scene_001", "video2.mp4", 1.0, 5.0, description="মলের বাইরে রাস্তা", subjects=["রাস্তা"]),
        _scene("video2_scene_002", "video2.mp4", 22.0, 25.5, description="নিরাপত্তা security staff", subjects=["নিরাপত্তা", "security"]),
        _scene("video3_scene_001", "video3.mp4", 0.0, 4.0, description="মলের বাইরের ভবন", subjects=["ভবন"]),
        _scene("video4_scene_001", "video4.mp4", 12.1, 17.3, description="হনুমান এসকেলেটরে ওঠার চেষ্টা", subjects=["হনুমান", "এসকেলেটর"]),
        _scene("video5_scene_001", "video5.mp4", 2.0, 8.0, description="অপ্রাসঙ্গিক অফিস করিডোর", subjects=["অফিস"]),
        _scene("video6_scene_001", "video6.mp4", 3.2, 8.7, description="ভিড় crowd reaction", subjects=["ভিড়", "crowd"]),
    ]
    alignment = AlignmentResult(
        duration=18.0,
        cues=[CaptionCue(start=0, end=18, text="পুজোর বাজারে হনুমান")],
    )
    plan, debug = build_semantic_plan(
        {
            "metadata": {"title": "দুর্গাপুরের মলে হনুমান", "location": "দুর্গাপুর"},
            "alignment": alignment.model_dump(),
            "narration": [item.model_dump() for item in narration],
            "scenes": scenes,
        }
    )
    sources = [clip.source for clip in plan.timeline]
    assert sources == ["video1.mp4", "video4.mp4", "video2.mp4", "video6.mp4"]
    assert plan.timeline[0].source_start == 5.2
    assert plan.timeline[0].source_end == 9.0
    assert plan.timeline[1].source_start == 12.1
    assert plan.timeline[2].source_start == 22.0
    assert plan.timeline[3].source_start == 3.2
    assert plan.duration == 18.0
    assert plan.timeline[0].start == 0
    assert abs(plan.timeline[-1].end - 18.0) < 0.05
    assert debug.matches
    selected = [next(item.scene_id for item in match.candidates if item.selected) for match in debug.matches]
    assert selected == ["video1_scene_001", "video4_scene_001", "video2_scene_002", "video6_scene_001"]
