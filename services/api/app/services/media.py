from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class MediaProbeError(RuntimeError):
    pass


def probe_media(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise MediaProbeError(f"media file does not exist: {path}")
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise MediaProbeError("ffprobe is not installed") from exc
    except subprocess.CalledProcessError as exc:
        raise MediaProbeError(exc.stderr.strip() or "ffprobe failed") from exc

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise MediaProbeError("ffprobe returned invalid JSON") from exc

    video_stream = next((s for s in payload.get("streams", []) if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in payload.get("streams", []) if s.get("codec_type") == "audio"), None)
    width = int(video_stream["width"]) if video_stream and video_stream.get("width") else None
    height = int(video_stream["height"]) if video_stream and video_stream.get("height") else None
    fps = _parse_fps(video_stream.get("avg_frame_rate") if video_stream else None)
    duration = float(payload.get("format", {}).get("duration") or 0)
    orientation = "unknown"
    if width and height:
        orientation = "portrait" if height > width else "landscape" if width > height else "square"
    return {
        "filename": path.name,
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "orientation": orientation,
        "video_codec": video_stream.get("codec_name") if video_stream else None,
        "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
        "size_bytes": int(payload.get("format", {}).get("size") or path.stat().st_size),
    }


def _parse_fps(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    if "/" in value:
        num, den = value.split("/", 1)
        try:
            return round(float(num) / float(den), 3)
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(value)
    except ValueError:
        return None
