from pathlib import Path

import pytest

from app.services.paths import UnsafePathError, job_dir, resolve_under, sanitize_filename


def test_sanitize_filename_strips_directories_and_odd_characters() -> None:
    assert sanitize_filename("../../etc/passwd", "fallback.mp4") == "passwd"
    assert sanitize_filename("mall interview.MP4", "clip.mp4") == "mall_interview.MP4"
    assert sanitize_filename("..", "voice.mp3") == "voice.mp3"


def test_resolve_under_blocks_path_escape(tmp_path: Path) -> None:
    root = tmp_path / "jobs"
    root.mkdir()
    safe = resolve_under(root, "abc123/footage/clip01.mp4")
    assert str(safe).startswith(str(root.resolve()))
    with pytest.raises(UnsafePathError):
        resolve_under(root, "../outside.txt")


def test_job_dir_rejects_invalid_ids(tmp_path: Path) -> None:
    with pytest.raises(UnsafePathError):
        job_dir(tmp_path, "../secret")
    with pytest.raises(UnsafePathError):
        job_dir(tmp_path, "bad id")
    assert job_dir(tmp_path, "sample-demo") == (tmp_path / "sample-demo").resolve()
