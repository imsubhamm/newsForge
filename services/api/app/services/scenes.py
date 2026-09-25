from __future__ import annotations

import re
import subprocess
from pathlib import Path

from app.config import Settings
from app.schemas import VisualScene

PTS = re.compile(r"pts_time:([0-9.]+)")
MIN_SCENE = 1.2
FALLBACK_WINDOW = 5.0


def detect_scenes(root: Path, footage: dict, settings: Settings) -> list[VisualScene]:
    footage_dir = root / "footage"
    frame_dir = root / "analysis" / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    scenes: list[VisualScene] = []
    for clip in footage.get("clips", []):
        path = footage_dir / clip["filename"]
        if not path.exists():
            continue
        usable_start = float(clip.get("usable_start") or 0)
        usable_end = float(clip.get("usable_end") or clip.get("duration") or 0)
        if usable_end - usable_start < 0.4:
            continue
        bounds = _cut_points(path, usable_start, usable_end)
        crop = clip.get("crop_mode") or settings.default_crop_mode
        for index, (start, end) in enumerate(bounds, start=1):
            scene_id = f"{path.stem}_scene_{index:03d}"
            frames = _extract_frames(path, scene_id, start, end, frame_dir)
            detected = len(bounds) > 1 and (end - start) < (usable_end - usable_start) * 0.85
            scenes.append(
                VisualScene(
                    scene_id=scene_id,
                    source_file=path.name,
                    source_start=round(start, 3),
                    source_end=round(end, 3),
                    duration=round(end - start, 3),
                    description="Unlabeled reporter footage. Content is not invented.",
                    environment=["uploaded clip"],
                    subjects=[],
                    actions=[],
                    shot_type="unknown",
                    camera_motion="handheld" if clip.get("orientation") == "landscape" else "unknown",
                    quality_score=0.72,
                    stability_score=0.7,
                    visual_interest_score=0.86 if detected else 0.64,
                    crop_mode=crop,
                    frame_paths=[str(frame.relative_to(root)) for frame in frames],
                )
            )
    if not scenes:
        raise RuntimeError("no visual scenes could be detected")
    return scenes


def _cut_points(path: Path, start: float, end: float) -> list[tuple[float, float]]:
    detected = _ffmpeg_scene_times(path, start, end)
    points = [start, *detected, end]
    unique: list[float] = []
    for point in sorted(points):
        if not unique or point - unique[-1] >= 0.35:
            unique.append(point)
    windows = [(left, right) for left, right in zip(unique, unique[1:], strict=False) if right - left >= MIN_SCENE]
    if len(windows) >= 2:
        return windows
    return _time_windows(start, end)


def _ffmpeg_scene_times(path: Path, start: float, end: float) -> list[float]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        str(path),
        "-filter:v",
        "select='gt(scene,0.18)',showinfo",
        "-an",
        "-f",
        "null",
        "-",
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        return []
    times = []
    for match in PTS.finditer(completed.stderr or ""):
        stamp = float(match.group(1))
        if start + 0.4 < stamp < end - 0.4:
            times.append(stamp)
    return times


def _time_windows(start: float, end: float) -> list[tuple[float, float]]:
    windows: list[tuple[float, float]] = []
    cursor = start
    while cursor < end - 0.4:
        nxt = min(cursor + FALLBACK_WINDOW, end)
        if end - nxt < MIN_SCENE:
            nxt = end
        windows.append((cursor, nxt))
        cursor = nxt
    return windows or [(start, end)]


def _extract_frames(path: Path, scene_id: str, start: float, end: float, frame_dir: Path) -> list[Path]:
    stamps = [start + (end - start) * 0.35]
    if end - start >= 3:
        stamps.append(start + (end - start) * 0.7)
    frames: list[Path] = []
    for index, stamp in enumerate(stamps, start=1):
        dest = frame_dir / f"{scene_id}_{index:02d}.jpg"
        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{stamp:.3f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-q:v",
            "4",
            str(dest),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
        if dest.exists() and dest.stat().st_size > 0:
            frames.append(dest)
    return frames
