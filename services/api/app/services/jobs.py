from __future__ import annotations

import json
import logging
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Job, JobStatus
from app.schemas import CaptionCue, JobAsset, JobResponse, TimelinePlan
from app.services.media import MediaProbeError, probe_media
from app.services.paths import job_dir, sanitize_filename
from app.services.uploads import validate_audio, validate_logo, validate_video

PROGRESS_STEPS = [
    "assets_uploaded",
    "voice_analysed",
    "script_aligned",
    "footage_processed",
    "scenes_analysed",
    "ai_editing_complete",
    "bengali_subtitles_created",
    "video_rendered",
]

STATUS_TO_STEPS = {
    JobStatus.UPLOADED.value: ["assets_uploaded"],
    JobStatus.TRANSCRIBING.value: ["assets_uploaded"],
    JobStatus.ALIGNING.value: ["assets_uploaded", "voice_analysed"],
    JobStatus.ALIGNED.value: ["assets_uploaded", "voice_analysed", "script_aligned"],
    JobStatus.ANALYSING_FOOTAGE.value: ["assets_uploaded", "voice_analysed", "script_aligned"],
    JobStatus.CREATING_TIMELINE.value: [
        "assets_uploaded",
        "voice_analysed",
        "script_aligned",
        "footage_processed",
        "scenes_analysed",
    ],
    JobStatus.RENDERING.value: [
        "assets_uploaded",
        "voice_analysed",
        "script_aligned",
        "footage_processed",
        "scenes_analysed",
        "ai_editing_complete",
        "bengali_subtitles_created",
    ],
    JobStatus.COMPLETED.value: PROGRESS_STEPS,
    JobStatus.FAILED.value: [],
}


class JobServiceError(RuntimeError):
    pass


def create_job(
    db: Session,
    settings: Settings,
    *,
    title: str,
    location: str,
    reporter_name: str,
    script: str,
    voice: UploadFile,
    footage: list[UploadFile],
    logo: UploadFile | None,
) -> JobResponse:
    if not title.strip():
        raise JobServiceError("news title is required")
    if not script.strip():
        raise JobServiceError("Bengali script is required")
    if not footage:
        raise JobServiceError("at least one footage file is required")

    validate_audio(voice, settings)
    for clip in footage:
        validate_video(clip, settings)
    if logo is not None:
        validate_logo(logo, settings)

    job_id = uuid.uuid4().hex[:12]
    root = job_dir(settings.jobs_dir, job_id)
    footage_dir = root / "footage"
    analysis_dir = root / "analysis"
    output_dir = root / "output"
    for folder in (footage_dir, analysis_dir, output_dir):
        folder.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("bangla.news")
    started = time.perf_counter()

    script_path = root / "script.txt"
    script_path.write_text(script.strip() + "\n", encoding="utf-8")

    voice_name = sanitize_filename(voice.filename or "voice.mp3", "voice.mp3")
    if Path(voice_name).suffix.lower() not in settings.allowed_audio_suffixes:
        voice_name = "voice.mp3"
    voice_path = root / ("voice" + Path(voice_name).suffix.lower())
    _write_upload(voice, voice_path)

    saved_clips: list[dict] = []
    for index, clip in enumerate(footage, start=1):
        original = sanitize_filename(clip.filename or f"clip{index:02d}.mp4", f"clip{index:02d}.mp4")
        suffix = Path(original).suffix.lower() or ".mp4"
        stored = f"clip{index:02d}{suffix}"
        dest = footage_dir / stored
        _write_upload(clip, dest)
        clip_meta: dict = {
            "id": f"clip{index:02d}",
            "filename": stored,
            "original_filename": original,
            "size_bytes": dest.stat().st_size,
        }
        try:
            clip_meta.update(probe_media(dest))
        except MediaProbeError as exc:
            logger.warning("footage probe failed", extra={"job_id": job_id, "error": str(exc)})
            clip_meta["probe_error"] = str(exc)
        saved_clips.append(clip_meta)

    logo_name = None
    if logo is not None:
        original = sanitize_filename(logo.filename or "logo.png", "logo.png")
        suffix = Path(original).suffix.lower()
        if suffix not in settings.allowed_logo_suffixes:
            suffix = ".png"
        logo_name = f"logo{suffix}"
        _write_upload(logo, root / logo_name)

    metadata = {
        "id": job_id,
        "title": title.strip(),
        "location": location.strip(),
        "reporter_name": reporter_name.strip(),
        "status": JobStatus.UPLOADED.value,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "crop_mode": settings.default_crop_mode,
        "voice": voice_path.name,
        "logo": logo_name,
        "footage": saved_clips,
        "script_path": "script.txt",
    }
    (root / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    record = Job(
        id=job_id,
        title=title.strip(),
        location=location.strip(),
        reporter_name=reporter_name.strip(),
        status=JobStatus.UPLOADED.value,
        completed_steps=1,
    )
    db.add(record)
    db.commit()

    duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "job created",
        extra={"job_id": job_id, "stage": "UPLOADED", "duration_ms": duration_ms},
    )
    return get_job(db, settings, job_id)


def get_job(db: Session, settings: Settings, job_id: str) -> JobResponse:
    record = db.get(Job, job_id)
    root = settings.jobs_dir / job_id
    if record is None and not root.exists():
        raise JobServiceError("job not found")

    metadata = _read_json(root / "metadata.json") if (root / "metadata.json").exists() else {}
    status = record.status if record else metadata.get("status", JobStatus.UPLOADED.value)
    title = record.title if record else metadata.get("title", "")
    location = record.location if record else metadata.get("location", "")
    reporter_name = record.reporter_name if record else metadata.get("reporter_name", "")
    error = record.error if record else metadata.get("error")
    created_at = (
        record.created_at.isoformat()
        if record and record.created_at
        else metadata.get("created_at", datetime.utcnow().isoformat())
    )

    assets: list[JobAsset] = []
    if root.exists():
        if (root / "script.txt").exists():
            assets.append(_asset("script", root / "script.txt", root))
        for audio_name in ("voice.mp3", "voice.wav", "voice.m4a"):
            if (root / audio_name).exists():
                assets.append(_asset("voice", root / audio_name, root))
        footage_dir = root / "footage"
        if footage_dir.exists():
            for clip in sorted(footage_dir.iterdir()):
                if clip.is_file():
                    assets.append(_asset("footage", clip, root))
        logo_names = {candidate.name for candidate in root.glob("logo.*")}
        meta_logo = metadata.get("logo")
        if isinstance(meta_logo, str) and meta_logo:
            logo_names.add(Path(meta_logo).name)
        for name in sorted(logo_names):
            candidate = root / name
            if candidate.is_file():
                assets.append(_asset("logo", candidate, root))

    output_file = root / "output" / "final.mp4"
    analysis = root / "analysis"
    alignment = _read_json(analysis / "alignment.json") if (analysis / "alignment.json").exists() else {}
    timeline = _read_json(analysis / "timeline.json") if (analysis / "timeline.json").exists() else {}
    captions = [CaptionCue.model_validate(item) for item in alignment.get("cues", [])]
    weak = int(timeline.get("weak_match_count") or 0)
    if not weak and timeline.get("timeline"):
        weak = sum(1 for clip in timeline["timeline"] if clip.get("needs_review"))
    return JobResponse(
        id=job_id,
        title=title,
        location=location,
        reporter_name=reporter_name,
        status=status,
        error=error,
        created_at=created_at,
        steps=_steps_for_job(root, status, output_file.exists()),
        assets=assets,
        output_url=f"/api/jobs/{job_id}/output" if output_file.exists() else None,
        captions=captions,
        transcript_available=(analysis / "transcript.json").exists(),
        alignment_available=(analysis / "alignment.json").exists(),
        semantic_available=(analysis / "semantic_debug.json").exists(),
        weak_match_count=weak,
        footage_warning=timeline.get("footage_warning"),
    )


def list_jobs(db: Session, settings: Settings) -> list[JobResponse]:
    rows = db.query(Job).order_by(Job.created_at.desc()).all()
    if rows:
        return [get_job(db, settings, row.id) for row in rows]
    jobs = []
    if settings.jobs_dir.exists():
        for folder in sorted(settings.jobs_dir.iterdir(), reverse=True):
            if folder.is_dir() and (folder / "metadata.json").exists():
                jobs.append(get_job(db, settings, folder.name))
    return jobs


def load_timeline(settings: Settings, job_id: str) -> TimelinePlan:
    path = job_dir(settings.jobs_dir, job_id) / "analysis" / "timeline.json"
    if not path.exists():
        raise JobServiceError("timeline.json is not available yet")
    return TimelinePlan.model_validate_json(path.read_text(encoding="utf-8"))


def save_timeline(settings: Settings, job_id: str, plan: TimelinePlan) -> TimelinePlan:
    path = job_dir(settings.jobs_dir, job_id) / "analysis" / "timeline.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    return plan


def _write_upload(upload: UploadFile, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)
    if dest.stat().st_size == 0:
        dest.unlink(missing_ok=True)
        raise JobServiceError(f"{dest.name} was empty")


def _asset(kind: str, path: Path, root: Path) -> JobAsset:
    return JobAsset(
        kind=kind,
        filename=path.name,
        path=str(path.relative_to(root)),
        size_bytes=path.stat().st_size,
    )


def find_voice(root: Path) -> Path | None:
    for name in ("voice.wav", "voice.mp3", "voice.m4a"):
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def set_job_status(db: Session, settings: Settings, job_id: str, status: JobStatus, error: str | None = None) -> None:
    record = db.get(Job, job_id)
    if record is None:
        record = Job(id=job_id, title="", status=status.value, error=error)
        db.add(record)
    record.status = status.value
    record.error = error
    db.commit()
    root = settings.jobs_dir / job_id
    metadata_path = root / "metadata.json"
    if metadata_path.exists():
        metadata = _read_json(metadata_path)
        metadata["status"] = status.value
        metadata["error"] = error
        write_json(metadata_path, metadata)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _steps_for_job(root: Path, status: str, rendered: bool) -> dict[str, bool]:
    completed = set(STATUS_TO_STEPS.get(status, []))
    analysis = root / "analysis"
    if (root / "script.txt").exists() and find_voice(root) is not None:
        completed.add("assets_uploaded")
    if (analysis / "transcript.json").exists():
        completed.update({"assets_uploaded", "voice_analysed"})
    if (analysis / "alignment.json").exists():
        completed.update({"assets_uploaded", "voice_analysed", "script_aligned"})
    if (analysis / "footage.json").exists():
        completed.update({"assets_uploaded", "voice_analysed", "script_aligned", "footage_processed", "scenes_analysed"})
    if (analysis / "timeline.json").exists():
        completed.update(
            {
                "assets_uploaded",
                "voice_analysed",
                "script_aligned",
                "footage_processed",
                "scenes_analysed",
                "ai_editing_complete",
                "bengali_subtitles_created",
            }
        )
    if rendered:
        completed.update(PROGRESS_STEPS)
    return {step: step in completed for step in PROGRESS_STEPS}
