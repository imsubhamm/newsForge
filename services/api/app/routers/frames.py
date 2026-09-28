from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.schemas import FrameJobListResponse, FrameJobResponse
from app.services.frames import create_frame_job, get_frame_job, list_frame_jobs, render_frame_job
from app.services.jobs import JobServiceError
from app.services.paths import UnsafePathError, job_dir

router = APIRouter(prefix="/api/frames", tags=["frames"])


def settings_dep() -> Settings:
    return get_settings()


@router.post("", response_model=FrameJobResponse)
async def create_frame(
    background_tasks: BackgroundTasks,
    aspect_ratio: str = Form(...),
    headline: str = Form(""),
    header: str = Form(""),
    footer: str = Form(""),
    location: str = Form(""),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> FrameJobResponse:
    try:
        job = create_frame_job(
            db,
            settings,
            aspect_ratio=aspect_ratio,
            video=video,
            headline=headline,
            header=header,
            footer=footer,
            location=location,
        )
        background_tasks.add_task(render_frame_job, job.id)
        return job
    except JobServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=FrameJobListResponse)
def list_frames(
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> FrameJobListResponse:
    return FrameJobListResponse(jobs=list_frame_jobs(db, settings))


@router.get("/{job_id}", response_model=FrameJobResponse)
def read_frame(
    job_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> FrameJobResponse:
    try:
        return get_frame_job(db, settings, job_id)
    except (JobServiceError, UnsafePathError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.api_route("/{job_id}/output", methods=["GET", "HEAD"])
def download_frame_output(
    job_id: str,
    settings: Settings = Depends(settings_dep),
    download: bool = Query(False),
) -> FileResponse:
    try:
        output = job_dir(settings.frames_dir, job_id) / "output" / "final.mp4"
    except UnsafePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not output.exists() or output.stat().st_size < 1000:
        raise HTTPException(status_code=404, detail="framed video is not ready")
    return FileResponse(
        output,
        media_type="video/mp4",
        filename="framed.mp4",
        content_disposition_type="attachment" if download else "inline",
        headers={
            "Cache-Control": "no-store",
            "Accept-Ranges": "bytes",
        },
    )


@router.get("/{job_id}/overlay")
def download_overlay(job_id: str, settings: Settings = Depends(settings_dep)) -> FileResponse:
    try:
        overlay = job_dir(settings.frames_dir, job_id) / "overlay.png"
    except UnsafePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not overlay.exists():
        raise HTTPException(status_code=404, detail="overlay is not ready")
    return FileResponse(overlay, media_type="image/png", headers={"Cache-Control": "no-store"})
