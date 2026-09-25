from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.schemas import AlignmentResult, JobListResponse, JobResponse, SemanticDebug, TimelinePlan, Transcript
from app.models import JobStatus
from app.services.jobs import JobServiceError, get_job, list_jobs, load_timeline, save_timeline, set_job_status
from app.services.jobs import create_job as create_job_record
from app.services.paths import UnsafePathError, job_dir
from app.services.pipeline import load_alignment, load_semantic_debug, load_transcript, next_process_status, process_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def settings_dep() -> Settings:
    return get_settings()


@router.post("", response_model=JobResponse)
async def create_job(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    location: str = Form(""),
    reporter_name: str = Form(""),
    script: str = Form(...),
    voice: UploadFile = File(...),
    footage: list[UploadFile] = File(...),
    logo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> JobResponse:
    if logo is not None and not logo.filename:
        logo = None
    try:
        job = create_job_record(
            db,
            settings,
            title=title,
            location=location,
            reporter_name=reporter_name,
            script=script,
            voice=voice,
            footage=footage,
            logo=logo,
        )
        background_tasks.add_task(process_job, job.id)
        return job
    except JobServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=JobListResponse)
def list_all_jobs(
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> JobListResponse:
    return JobListResponse(jobs=list_jobs(db, settings))


@router.get("/{job_id}", response_model=JobResponse)
def read_job(
    job_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> JobResponse:
    try:
        return get_job(db, settings, job_id)
    except (JobServiceError, UnsafePathError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{job_id}/process", response_model=JobResponse)
def start_process(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> JobResponse:
    try:
        get_job(db, settings, job_id)
    except (JobServiceError, UnsafePathError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    set_job_status(db, settings, job_id, next_process_status(job_dir(settings.jobs_dir, job_id)), error=None)
    background_tasks.add_task(process_job, job_id)
    return get_job(db, settings, job_id)


@router.get("/{job_id}/transcript", response_model=Transcript)
def read_transcript(job_id: str, settings: Settings = Depends(settings_dep)) -> Transcript:
    transcript = load_transcript(settings, job_id)
    if transcript is None:
        raise HTTPException(status_code=404, detail="transcript is not ready yet")
    return transcript


@router.get("/{job_id}/alignment", response_model=AlignmentResult)
def read_alignment(job_id: str, settings: Settings = Depends(settings_dep)) -> AlignmentResult:
    alignment = load_alignment(settings, job_id)
    if alignment is None:
        raise HTTPException(status_code=404, detail="alignment is not ready yet")
    return alignment


@router.get("/{job_id}/semantic-debug", response_model=SemanticDebug)
def read_semantic_debug(job_id: str, settings: Settings = Depends(settings_dep)) -> SemanticDebug:
    debug = load_semantic_debug(settings, job_id)
    if debug is None:
        raise HTTPException(status_code=404, detail="semantic debug is not ready yet")
    return debug


@router.get("/{job_id}/timeline", response_model=TimelinePlan)
def read_timeline(job_id: str, settings: Settings = Depends(settings_dep)) -> TimelinePlan:
    try:
        return load_timeline(settings, job_id)
    except (JobServiceError, UnsafePathError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{job_id}/timeline", response_model=TimelinePlan)
def update_timeline(
    job_id: str,
    plan: TimelinePlan,
    settings: Settings = Depends(settings_dep),
) -> TimelinePlan:
    try:
        return save_timeline(settings, job_id, plan)
    except (JobServiceError, UnsafePathError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{job_id}/output")
def download_output(job_id: str, settings: Settings = Depends(settings_dep)) -> FileResponse:
    try:
        output = job_dir(settings.jobs_dir, job_id) / "output" / "final.mp4"
    except UnsafePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not output.exists():
        raise HTTPException(status_code=404, detail="rendered video is not ready")
    return FileResponse(
        output,
        media_type="video/mp4",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": "inline",
            "Accept-Ranges": "bytes",
        },
    )
