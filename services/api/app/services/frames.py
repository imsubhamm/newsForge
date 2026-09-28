from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import FrameJob, FrameJobStatus
from app.schemas import FrameJobResponse
from app.services.frame_overlay import (
    DEFAULT_LOCATION,
    FrameOverlayError,
    banner_overlay_path,
    build_text_layer,
    canvas_size,
    overlay_filter,
)
from app.services.jobs import JobServiceError, _write_upload
from app.services.media import MediaProbeError, probe_media
from app.services.paths import UnsafePathError, job_dir, sanitize_filename
from app.services.uploads import UploadValidationError, validate_video

logger = logging.getLogger("bangla.news")


def create_frame_job(
    db: Session,
    settings: Settings,
    *,
    aspect_ratio: str,
    video: UploadFile,
    headline: str = "",
    header: str = "",
    footer: str = "",
    location: str = "",
) -> FrameJobResponse:
    if aspect_ratio not in {"16:9", "9:16"}:
        raise JobServiceError("aspect ratio must be 16:9 or 9:16")
    try:
        validate_video(video, settings)
    except UploadValidationError as exc:
        raise JobServiceError(str(exc)) from exc
    banner_overlay_path()

    job_id = uuid.uuid4().hex[:12]
    root = job_dir(settings.frames_dir, job_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / "output").mkdir(parents=True, exist_ok=True)

    original = sanitize_filename(video.filename or "source.mp4", "source.mp4")
    suffix = Path(original).suffix.lower() or ".mp4"
    source_name = f"source{suffix}"
    source_path = root / source_name
    _write_upload(video, source_path)

    place = location.strip() or DEFAULT_LOCATION
    top_line = header.strip()
    bottom_line = footer.strip() or headline.strip()
    metadata = {
        "id": job_id,
        "kind": "frame",
        "aspect_ratio": aspect_ratio,
        "header": top_line,
        "footer": bottom_line,
        "headline": bottom_line,
        "location": place,
        "channel_name": "আমার কথা",
        "source": source_name,
        "status": FrameJobStatus.UPLOADED.value,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    (root / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    record = FrameJob(
        id=job_id,
        aspect_ratio=aspect_ratio,
        headline=bottom_line,
        channel_name="আমার কথা",
        status=FrameJobStatus.UPLOADED.value,
    )
    db.add(record)
    db.commit()
    return get_frame_job(db, settings, job_id)


def get_frame_job(db: Session, settings: Settings, job_id: str) -> FrameJobResponse:
    record = db.get(FrameJob, job_id)
    root = settings.frames_dir / job_id
    if record is None and not root.exists():
        raise JobServiceError("frame job not found")
    metadata = _read_json(root / "metadata.json") if (root / "metadata.json").exists() else {}
    aspect = (record.aspect_ratio if record else metadata.get("aspect_ratio")) or "16:9"
    width, height = canvas_size(aspect)
    output = root / "output" / "final.mp4"
    overlay = root / "overlay.png"
    source_name = metadata.get("source")
    status = record.status if record else metadata.get("status", FrameJobStatus.UPLOADED.value)
    output_ready = (
        status == FrameJobStatus.COMPLETED.value
        and output.exists()
        and output.stat().st_size > 1000
    )
    return FrameJobResponse(
        id=job_id,
        aspect_ratio=aspect,  # type: ignore[arg-type]
        headline=str(metadata.get("headline") or metadata.get("footer") or ""),
        header=str(metadata.get("header") or ""),
        footer=str(metadata.get("footer") or metadata.get("headline") or ""),
        location=str(metadata.get("location") or ""),
        channel_name=record.channel_name if record else metadata.get("channel_name", "আমার কথা"),
        status=status,
        error=record.error if record else metadata.get("error"),
        created_at=(
            record.created_at.isoformat()
            if record and record.created_at
            else metadata.get("created_at", datetime.utcnow().isoformat())
        ),
        width=width,
        height=height,
        output_url=f"/api/frames/{job_id}/output" if output_ready else None,
        overlay_url=f"/api/frames/{job_id}/overlay" if overlay.exists() else None,
        source_filename=source_name if isinstance(source_name, str) else None,
    )


def list_frame_jobs(db: Session, settings: Settings) -> list[FrameJobResponse]:
    rows = db.query(FrameJob).order_by(FrameJob.created_at.desc()).all()
    if rows:
        return [get_frame_job(db, settings, row.id) for row in rows]
    jobs: list[FrameJobResponse] = []
    if settings.frames_dir.exists():
        for folder in sorted(settings.frames_dir.iterdir(), reverse=True):
            if folder.is_dir() and (folder / "metadata.json").exists():
                jobs.append(get_frame_job(db, settings, folder.name))
    return jobs


def set_frame_status(db: Session, settings: Settings, job_id: str, status: FrameJobStatus, error: str | None = None) -> None:
    record = db.get(FrameJob, job_id)
    if record is None:
        record = FrameJob(id=job_id, status=status.value, error=error)
        db.add(record)
    record.status = status.value
    record.error = error
    db.commit()
    root = settings.frames_dir / job_id
    metadata_path = root / "metadata.json"
    if metadata_path.exists():
        metadata = _read_json(metadata_path)
        metadata["status"] = status.value
        metadata["error"] = error
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_frame_job(job_id: str) -> None:
    from app.config import get_settings
    from app.db import SessionLocal

    settings = get_settings()
    db = SessionLocal()
    started = time.perf_counter()
    try:
        root = job_dir(settings.frames_dir, job_id)
        set_frame_status(db, settings, job_id, FrameJobStatus.RENDERING)
        overlay = _composite_frame(root, settings)
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info("frame render complete", extra={"job_id": job_id, "stage": "FRAME", "duration_ms": duration_ms})
        set_frame_status(db, settings, job_id, FrameJobStatus.COMPLETED)
        _ = overlay
    except (JobServiceError, FrameOverlayError, UnsafePathError, MediaProbeError, OSError) as exc:
        logger.exception("frame render failed", extra={"job_id": job_id, "error": str(exc)})
        set_frame_status(db, settings, job_id, FrameJobStatus.FAILED, error=str(exc)[-800:])
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "ffmpeg frame render failed").strip()
        logger.exception("frame ffmpeg failed", extra={"job_id": job_id, "error": detail[-800:]})
        set_frame_status(db, settings, job_id, FrameJobStatus.FAILED, error=detail[-800:])
    finally:
        db.close()


def _composite_frame(root: Path, settings: Settings) -> Path:
    metadata = _read_json(root / "metadata.json")
    aspect = metadata.get("aspect_ratio") or "16:9"
    width, height = canvas_size(aspect)
    source_name = metadata.get("source")
    if not isinstance(source_name, str) or not source_name:
        raise JobServiceError("source video is missing")
    source = root / Path(source_name).name
    if not source.is_file():
        raise JobServiceError("source video is missing")

    banner = banner_overlay_path()
    text_layer = build_text_layer(
        root / "overlay.png",
        aspect_ratio=aspect,
        header=str(metadata.get("header") or ""),
        footer=str(metadata.get("footer") or metadata.get("headline") or ""),
        location=str(metadata.get("location") or DEFAULT_LOCATION),
    )
    has_text = text_layer is not None

    output = root / "output" / "final.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    probe = probe_media(source)
    has_audio = bool(probe.get("audio_codec"))
    filters = overlay_filter(aspect, width, height, has_text)
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-stream_loop",
        "-1",
        "-i",
        str(banner),
    ]
    if has_text:
        command += ["-i", str(text_layer)]
    command += [
        "-filter_complex",
        filters,
        "-map",
        "[vout]",
    ]
    if has_audio:
        command += ["-map", "0:a", "-c:a", "aac", "-b:a", "192k"]
    else:
        command += ["-an"]
    command += [
        "-shortest",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "fast",
        "-crf",
        "20",
        "-movflags",
        "+faststart",
        str(output),
    ]
    env = os.environ.copy()
    env["TMPDIR"] = "/tmp"
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=1200, env=env)
    except FileNotFoundError as exc:
        raise JobServiceError("ffmpeg is required to add the news frame") from exc
    except subprocess.TimeoutExpired as exc:
        raise JobServiceError("frame render timed out") from exc

    if not output.exists() or output.stat().st_size == 0:
        raise JobServiceError("frame render finished without writing a video")
    result = probe_media(output)
    if result.get("width") != width or result.get("height") != height:
        raise JobServiceError(f"framed video is not {width}×{height}")
    return output


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
