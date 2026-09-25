from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from app.ai.provider import get_ai_provider
from app.config import Settings, get_settings
from app.db import SessionLocal
from app.models import JobStatus
from app.schemas import AlignmentResult, AudioSegment, SemanticDebug, TimelinePlan, Transcript
from app.services.alignment import align_script_to_transcript
from app.services.footage import FootageError, analyse_footage
from app.services.jobs import find_voice, set_job_status, write_json
from app.services.narration import segment_narration
from app.services.paths import job_dir
from app.services.render import RenderError, render_job
from app.services.scenes import detect_scenes
from app.services.audio_planner import apply_audio_editorial, attach_audio_debug
from app.services.semantic_planner import build_semantic_plan
from app.services.timeline_builder import TimelineBuildError
from app.services.transcription import TranscriptionError, transcribe_voice
from app.services.video_audio import analyse_video_audio, promote_speech_islands

logger = logging.getLogger("bangla.news")


def process_job(job_id: str) -> None:
    settings = get_settings()
    db = SessionLocal()
    started = time.perf_counter()
    try:
        root = job_dir(settings.jobs_dir, job_id)
        script = (root / "script.txt").read_text(encoding="utf-8")
        voice = find_voice(root)
        if voice is None:
            raise TranscriptionError("voice-over file is missing")
        metadata = _read_json(root / "metadata.json") if (root / "metadata.json").exists() else {}

        transcript = load_transcript(settings, job_id)
        if transcript is None:
            set_job_status(db, settings, job_id, JobStatus.TRANSCRIBING)
            stage_started = time.perf_counter()
            transcript = transcribe_voice(voice, settings, script=script)
            write_json(root / "analysis" / "transcript.json", transcript.model_dump())
            logger.info(
                "voice analysed",
                extra={
                    "job_id": job_id,
                    "stage": "TRANSCRIBING",
                    "duration_ms": int((time.perf_counter() - stage_started) * 1000),
                },
            )

        set_job_status(db, settings, job_id, JobStatus.ALIGNING)
        stage_started = time.perf_counter()
        alignment = align_script_to_transcript(script, transcript)
        write_json(root / "analysis" / "alignment.json", alignment.model_dump())
        logger.info(
            "script aligned",
            extra={
                "job_id": job_id,
                "stage": "ALIGNING",
                "duration_ms": int((time.perf_counter() - stage_started) * 1000),
            },
        )
        set_job_status(db, settings, job_id, JobStatus.ALIGNED)

        set_job_status(db, settings, job_id, JobStatus.ANALYSING_FOOTAGE)
        stage_started = time.perf_counter()
        footage = analyse_footage(root, settings)
        write_json(root / "analysis" / "footage.json", footage)
        logger.info(
            "footage processed",
            extra={
                "job_id": job_id,
                "stage": "ANALYSING_FOOTAGE",
                "duration_ms": int((time.perf_counter() - stage_started) * 1000),
            },
        )

        scenes = detect_scenes(root, footage, settings)
        write_json(root / "analysis" / "scenes.json", {"scenes": [scene.model_dump() for scene in scenes]})
        narration = segment_narration(script, alignment)
        write_json(root / "analysis" / "narration.json", {"segments": [item.model_dump() for item in narration]})
        audio_path = root / "analysis" / "video_audio.json"
        if audio_path.exists():
            audio_segments = [AudioSegment.model_validate(item) for item in _read_json(audio_path).get("segments") or []]
        else:
            audio_segments = analyse_video_audio(root, footage, settings, script)
        audio_segments = promote_speech_islands(root, footage, audio_segments)
        write_json(audio_path, {"segments": [item.model_dump() for item in audio_segments]})
        logger.info(
            "scenes analysed",
            extra={
                "job_id": job_id,
                "stage": "ANALYSING_FOOTAGE",
                "duration_ms": int((time.perf_counter() - stage_started) * 1000),
            },
        )

        set_job_status(db, settings, job_id, JobStatus.CREATING_TIMELINE)
        stage_started = time.perf_counter()
        payload = {
            "metadata": metadata,
            "footage": footage,
            "alignment": alignment.model_dump(),
            "narration": [item.model_dump() for item in narration],
            "scenes": [scene.model_dump() for scene in scenes],
            "audio_segments": [item.model_dump() for item in audio_segments],
        }
        raw_plan = get_ai_provider(settings).build_timeline(payload)
        plan = TimelinePlan.model_validate(raw_plan)
        _, debug = build_semantic_plan(payload, settings)
        plan, audio_debug = apply_audio_editorial(plan, narration, audio_segments, alignment, settings)
        debug = attach_audio_debug(debug, audio_debug)
        write_json(root / "analysis" / "timeline.json", plan.model_dump())
        write_json(root / "analysis" / "semantic_debug.json", debug.model_dump())
        logger.info(
            "timeline created",
            extra={
                "job_id": job_id,
                "stage": "CREATING_TIMELINE",
                "duration_ms": int((time.perf_counter() - stage_started) * 1000),
            },
        )

        set_job_status(db, settings, job_id, JobStatus.RENDERING)
        stage_started = time.perf_counter()
        render_job(root, settings)
        logger.info(
            "video rendered",
            extra={
                "job_id": job_id,
                "stage": "RENDERING",
                "duration_ms": int((time.perf_counter() - stage_started) * 1000),
            },
        )
        set_job_status(db, settings, job_id, JobStatus.COMPLETED)
        logger.info(
            "job complete",
            extra={
                "job_id": job_id,
                "stage": "COMPLETED",
                "duration_ms": int((time.perf_counter() - started) * 1000),
            },
        )
    except Exception as exc:
        logger.exception(
            "job failed",
            extra={"job_id": job_id, "stage": "FAILED", "error": str(exc)},
        )
        set_job_status(db, settings, job_id, JobStatus.FAILED, error=_public_error(exc))
    finally:
        db.close()


def load_transcript(settings: Settings, job_id: str) -> Transcript | None:
    path = job_dir(settings.jobs_dir, job_id) / "analysis" / "transcript.json"
    if not path.exists():
        return None
    return Transcript.model_validate_json(path.read_text(encoding="utf-8"))


def load_semantic_debug(settings: Settings, job_id: str) -> SemanticDebug | None:
    path = job_dir(settings.jobs_dir, job_id) / "analysis" / "semantic_debug.json"
    if not path.exists():
        return None
    return SemanticDebug.model_validate_json(path.read_text(encoding="utf-8"))


def load_alignment(settings: Settings, job_id: str) -> AlignmentResult | None:
    path = job_dir(settings.jobs_dir, job_id) / "analysis" / "alignment.json"
    if not path.exists():
        return None
    return AlignmentResult.model_validate_json(path.read_text(encoding="utf-8"))


def render_existing_job(job_id: str) -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        root = job_dir(settings.jobs_dir, job_id)
        set_job_status(db, settings, job_id, JobStatus.RENDERING, error=None)
        render_job(root, settings)
        set_job_status(db, settings, job_id, JobStatus.COMPLETED, error=None)
    except Exception as exc:
        set_job_status(db, settings, job_id, JobStatus.FAILED, error=_public_error(exc))
    finally:
        db.close()


def next_process_status(root: Path) -> JobStatus:
    analysis = root / "analysis"
    if not (analysis / "transcript.json").exists():
        return JobStatus.TRANSCRIBING
    if not (analysis / "alignment.json").exists():
        return JobStatus.ALIGNING
    if not (analysis / "timeline.json").exists():
        return JobStatus.ANALYSING_FOOTAGE
    return JobStatus.RENDERING


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _public_error(exc: Exception) -> str:
    if isinstance(exc, (TranscriptionError, FootageError, TimelineBuildError, RenderError)):
        return str(exc)
    if isinstance(exc, FileNotFoundError):
        return "A required job file is missing."
    return "Editing failed. Check the server log for details."
