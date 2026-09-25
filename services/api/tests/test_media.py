from pathlib import Path

import pytest

from app.services.media import MediaProbeError, probe_media


def test_probe_sample_clip_when_present() -> None:
    clip = Path(__file__).resolve().parents[3] / "storage" / "jobs" / "sample-demo" / "footage" / "clip01.mp4"
    if not clip.exists():
        pytest.skip("sample footage has not been generated yet")
    meta = probe_media(clip)
    assert meta["duration"] > 1
    assert meta["width"] == 1920
    assert meta["height"] == 1080
    assert meta["orientation"] == "landscape"
    assert meta["video_codec"] in {"h264", "av1", "hevc"}


def test_probe_missing_file() -> None:
    with pytest.raises(MediaProbeError):
        probe_media(Path("/tmp/does-not-exist-bangla-news.mp4"))
