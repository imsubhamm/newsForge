import json
from pathlib import Path

from app.services.render import _find_logo


def test_find_logo_uses_metadata_filename(tmp_path: Path) -> None:
    logo = tmp_path / "ChatGPT_channel.png"
    logo.write_bytes(b"png")
    (tmp_path / "metadata.json").write_text(
        json.dumps({"logo": "ChatGPT_channel.png"}),
        encoding="utf-8",
    )
    assert _find_logo(tmp_path) == logo


def test_find_logo_falls_back_to_logo_prefix(tmp_path: Path) -> None:
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"png")
    assert _find_logo(tmp_path) == logo
