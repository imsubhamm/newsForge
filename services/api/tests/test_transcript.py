import json

from app.schemas import Transcript


def test_transcript_schema_accepts_word_timestamps() -> None:
    payload = {
        "language": "bn",
        "duration": 42.8,
        "source": "faster-whisper",
        "model": "small",
        "segments": [{"start": 0.0, "end": 3.8, "text": "পুজোর বাজারে ঘটল এক অদ্ভুত ঘটনা"}],
        "words": [{"start": 0.0, "end": 0.45, "text": "পুজোর"}],
    }
    transcript = Transcript.model_validate(payload)
    assert transcript.language == "bn"
    assert transcript.words[0].text == "পুজোর"
    assert json.loads(transcript.model_dump_json())["duration"] == 42.8
