"""The AI editor must return a validated timeline plan, never free-form text."""

import json

from pydantic import ValidationError

from app.schemas import TimelinePlan


def test_parser_extracts_strict_json_object() -> None:
    raw = """
    Here is the edit.
    {
      "headline": "মলে হনুমান",
      "location": "দুর্গাপুর",
      "duration": 4.0,
      "timeline": [
        {
          "start": 0,
          "end": 4.0,
          "source": "clip01.mp4",
          "source_start": 0,
          "source_end": 4.0,
          "reason": "Establishes the mall"
        }
      ]
    }
    """
    start = raw.find("{")
    end = raw.rfind("}")
    plan = TimelinePlan.model_validate(json.loads(raw[start : end + 1]))
    assert plan.headline == "মলে হনুমান"


def test_parser_rejects_invented_clip_paths() -> None:
    payload = {
        "headline": "মলে হনুমান",
        "duration": 4.0,
        "timeline": [
            {
                "start": 0,
                "end": 4.0,
                "source": "https://example.com/fake.mp4",
                "source_start": 0,
                "source_end": 4.0,
                "reason": "Invented footage",
            }
        ],
    }
    try:
        TimelinePlan.model_validate(payload)
    except ValidationError:
        return
    raise AssertionError("remote/invented footage paths must be rejected")
