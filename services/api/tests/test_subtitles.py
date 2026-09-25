from app.services.subtitles import cues_from_script, segment_bengali_script


SCRIPT = "পুজোর বাজারে ঘটল এক অদ্ভুত ঘটনা। দুর্গাপুরের একটি মলে হঠাৎ হনুমান উঠে পড়ে। কেনাকাটা থেমে যায়।"


def test_segments_prefer_short_readable_phrases() -> None:
    chunks = segment_bengali_script(SCRIPT, max_chars=28)
    assert len(chunks) >= 3
    assert all(len(chunk) <= 40 for chunk in chunks)
    assert "হনুমান" in "".join(chunks)


def test_cues_cover_full_duration_without_gaps() -> None:
    cues = cues_from_script(SCRIPT, duration=8.0, max_chars=28)
    assert cues[0].start == 0
    assert abs(cues[-1].end - 8.0) < 0.001
    for previous, current in zip(cues, cues[1:], strict=False):
        assert current.start == previous.end
        assert current.end > current.start


def test_empty_script_returns_no_cues() -> None:
    assert segment_bengali_script("   ") == []
    assert cues_from_script("   ", duration=5) == []
