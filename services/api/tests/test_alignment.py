from app.schemas import Transcript, TranscriptWord
from app.services.alignment import align_script_to_transcript


def test_alignment_keeps_reporter_spelling() -> None:
    script = "দুর্গাপুরে হনুমান উঠে পড়ে"
    transcript = Transcript(
        language="bn",
        duration=1.6,
        words=[
            TranscriptWord(start=0.0, end=0.4, text="দূর্গাপুরে"),
            TranscriptWord(start=0.4, end=0.8, text="হনুমান"),
            TranscriptWord(start=0.8, end=1.2, text="উঠে"),
            TranscriptWord(start=1.2, end=1.6, text="পরে"),
        ],
    )
    result = align_script_to_transcript(script, transcript)
    text = " ".join(cue.text for cue in result.cues)
    assert "দুর্গাপুরে" in text
    assert "দূর্গাপুরে" not in text
    assert "হনুমান" in text
    assert result.cues[0].start == 0
    assert abs(result.cues[-1].end - 1.6) < 0.05


def test_alignment_maps_devanagari_whisper_to_bengali_script() -> None:
    script = "রাজ্যের অগ্নিনির্বাপণ দুর্গাপুর যুক্ত নতুন"
    transcript = Transcript(
        language="bn",
        duration=2.5,
        words=[
            TranscriptWord(start=0.0, end=0.5, text="राज्चेर"),
            TranscriptWord(start=0.5, end=1.2, text="अग्निनिर्बापन"),
            TranscriptWord(start=1.2, end=1.8, text="दुर्गापुर"),
            TranscriptWord(start=1.8, end=2.1, text="जुक्तो"),
            TranscriptWord(start=2.1, end=2.5, text="नতুন"),
        ],
    )
    result = align_script_to_transcript(script, transcript)
    text = " ".join(cue.text for cue in result.cues)
    assert "দুর্গাপুর" in text
    assert "दुर्गापुर" not in text
    assert result.match_ratio > 0.4


def test_alignment_covers_whisper_duration() -> None:
    script = "পুজোর বাজারে ঘটল এক অদ্ভুত ঘটনা।"
    transcript = Transcript(
        language="bn",
        duration=4.0,
        words=[
            TranscriptWord(start=0.0, end=0.7, text="পুজোর"),
            TranscriptWord(start=0.7, end=1.4, text="বাজারে"),
            TranscriptWord(start=1.4, end=2.0, text="ঘটল"),
            TranscriptWord(start=2.0, end=2.6, text="এক"),
            TranscriptWord(start=2.6, end=3.3, text="অদ্ভুত"),
            TranscriptWord(start=3.3, end=4.0, text="ঘটনা"),
        ],
    )
    result = align_script_to_transcript(script, transcript)
    assert result.script_authoritative is True
    assert result.match_ratio > 0.5
    assert result.cues[0].start == 0
    assert abs(result.cues[-1].end - 4.0) < 0.05
    for previous, current in zip(result.cues, result.cues[1:], strict=False):
        assert current.start >= previous.start
