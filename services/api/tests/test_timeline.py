import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas import TimelinePlan


SAMPLE = Path(__file__).resolve().parents[3] / "storage" / "jobs" / "sample-demo" / "analysis" / "timeline.json"


def _valid_payload() -> dict:
    return {
        "headline": "দুর্গাপুরের মলে হঠাৎ হনুমান",
        "location": "দুর্গাপুর",
        "reporter_name": "রিয়া সেন",
        "duration": 8.0,
        "crop_mode": "center-crop",
        "timeline": [
            {
                "start": 0,
                "end": 3.2,
                "source": "clip01.mp4",
                "source_start": 1.0,
                "source_end": 4.2,
                "reason": "Mall exterior",
            },
            {
                "start": 3.2,
                "end": 8.0,
                "source": "clip02.mp4",
                "source_start": 0.5,
                "source_end": 5.3,
                "reason": "Crowd reaction",
            },
        ],
        "captions": [{"start": 0, "end": 8, "text": "দুর্গাপুরের মলে হঠাৎ হনুমান"}],
    }


def test_timeline_schema_accepts_well_formed_plan() -> None:
    plan = TimelinePlan.model_validate(_valid_payload())
    assert plan.duration == 8.0
    assert plan.timeline[0].source == "clip01.mp4"


def test_timeline_rejects_path_escape_in_source() -> None:
    payload = _valid_payload()
    payload["timeline"][0]["source"] = "../secret.mp4"
    with pytest.raises(ValidationError):
        TimelinePlan.model_validate(payload)


def test_timeline_rejects_mismatched_source_duration() -> None:
    payload = _valid_payload()
    payload["timeline"][0]["source_end"] = 9.0
    with pytest.raises(ValidationError):
        TimelinePlan.model_validate(payload)


def test_timeline_duration_matches_last_clip() -> None:
    plan = TimelinePlan.model_validate(_valid_payload())
    assert plan.timeline[-1].end == plan.duration


def test_sample_timeline_json_is_valid() -> None:
    if not SAMPLE.exists():
        pytest.skip("sample timeline has not been generated yet")
    plan = TimelinePlan.model_validate(json.loads(SAMPLE.read_text(encoding="utf-8")))
    assert plan.timeline
    assert plan.duration > 0
    assert abs(plan.timeline[-1].end - plan.duration) < 0.05
