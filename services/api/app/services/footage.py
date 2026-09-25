from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.services.media import MediaProbeError, probe_media

HANDLE_HEAD = 0.25
HANDLE_TAIL = 0.15


class FootageError(RuntimeError):
    pass


def analyse_footage(root: Path, settings: Settings) -> dict:
    footage_dir = root / "footage"
    if not footage_dir.exists():
        raise FootageError("footage folder is missing")

    clips: list[dict] = []
    for path in sorted(footage_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in settings.allowed_video_suffixes:
            continue
        try:
            probe = probe_media(path)
        except MediaProbeError as exc:
            raise FootageError(f"{path.name} could not be read: {exc}") from exc
        duration = float(probe.get("duration") or 0)
        if duration < 0.4:
            continue
        usable_start = HANDLE_HEAD if duration > 1.0 else 0.0
        usable_end = max(usable_start + 0.4, duration - (HANDLE_TAIL if duration > 1.0 else 0.0))
        orientation = probe.get("orientation") or "unknown"
        clips.append(
            {
                "id": path.stem,
                "filename": path.name,
                "duration": round(duration, 3),
                "width": probe.get("width"),
                "height": probe.get("height"),
                "fps": probe.get("fps"),
                "orientation": orientation,
                "usable_start": round(usable_start, 3),
                "usable_end": round(usable_end, 3),
                "crop_mode": "blur-background" if orientation == "landscape" else settings.default_crop_mode,
                "source": "ffprobe",
                "description": "Reporter-uploaded clip. No invented scene labels.",
            }
        )

    if not clips:
        raise FootageError("no usable footage clips were found")

    return {
        "clip_count": len(clips),
        "total_usable": round(sum(clip["usable_end"] - clip["usable_start"] for clip in clips), 3),
        "clips": clips,
        "source": "ffprobe",
    }
