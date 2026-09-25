from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from app.config import Settings, repo_root
from app.schemas import TimelinePlan
from app.services.jobs import find_voice
from app.services.media import MediaProbeError, probe_media


class RenderError(RuntimeError):
    pass


def render_job(root: Path, settings: Settings) -> Path:
    timeline_path = root / "analysis" / "timeline.json"
    if not timeline_path.exists():
        raise RenderError("timeline.json is missing")
    plan = TimelinePlan.model_validate_json(timeline_path.read_text(encoding="utf-8"))
    voice = find_voice(root)
    if voice is None:
        raise RenderError("voice-over file is missing")

    job_id = root.name
    video_dir = repo_root() / "video"
    public_job = video_dir / "public" / "jobs" / job_id
    if public_job.exists():
        shutil.rmtree(public_job)
    public_job.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root / "footage", public_job / "footage")
    shutil.copy2(voice, public_job / voice.name)
    logo = _find_logo(root)
    if logo is not None:
        shutil.copy2(logo, public_job / logo.name)

    prefix = f"/jobs/{job_id}"
    props = {
        "headline": plan.headline,
        "location": plan.location,
        "reporterName": plan.reporter_name,
        "duration": plan.duration,
        "cropMode": plan.crop_mode,
        "audioSrc": f"{prefix}/{voice.name}",
        "logoSrc": f"{prefix}/{logo.name}" if logo is not None else None,
        "clips": [
            {
                "start": clip.start,
                "end": clip.end,
                "src": f"{prefix}/footage/{clip.source}",
                "sourceStart": clip.source_start,
                "sourceEnd": clip.source_end,
                "cropMode": clip.crop_mode or plan.crop_mode,
            }
            for clip in plan.timeline
        ],
        "captions": [cue.model_dump() for cue in plan.captions],
    }
    props_path = root / "analysis" / "remotion-props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    output = root / "output" / "final.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TMPDIR"] = "/tmp"
    env["npm_config_cache"] = str(Path.home() / ".npm")
    command = [
        "npx",
        "remotion",
        "render",
        "src/index.ts",
        "NewsVideo",
        str(output),
        f"--props={props_path}",
        f"--public-dir={video_dir / 'public'}",
        "--codec=h264",
        "--pixel-format=yuv420p",
        "--image-format=jpeg",
        "--overwrite",
        "--concurrency=1",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=video_dir,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=2400,
        )
    except FileNotFoundError as exc:
        raise RenderError("npx is required to render with Remotion") from exc
    except subprocess.TimeoutExpired as exc:
        raise RenderError("Remotion render timed out") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "Remotion render failed").strip()
        raise RenderError(detail[-1500:]) from exc

    if not output.exists() or output.stat().st_size == 0:
        raise RenderError("render finished without writing final.mp4")
    try:
        probe = probe_media(output)
    except MediaProbeError as exc:
        raise RenderError(f"rendered file could not be verified: {exc}") from exc
    if probe.get("width") != settings.video_width or probe.get("height") != settings.video_height:
        raise RenderError("rendered video is not 1080×1920")
    _ = completed
    return output


def ensure_news_bed(video_dir: Path, force: bool = False) -> Path:
    """Generate an original news underscore so renders never pull copyrighted music."""
    path = video_dir / "public" / "audio" / "news-bed.mp3"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not force and path.exists() and path.stat().st_size > 1000:
        return path
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "anoisesrc=color=brown:duration=20:amplitude=0.2,lowpass=f=260,highpass=f=40",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=73.42:duration=20",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=110:duration=20",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=164.81:duration=20",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=246.94:duration=20",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1760:duration=20",
        "-filter_complex",
        "[0]volume=0.5[pad];"
        "[1]volume=0.3,tremolo=f=1.375:d=0.62[bass];"
        "[2]volume=0.18,tremolo=f=0.28:d=0.42[fifth];"
        "[3]volume=0.1,tremolo=f=0.2:d=0.35[mid];"
        "[4]volume=0.055,lowpass=f=900[air];"
        "[5]highpass=f=1400,apulsator=mode=sine:hz=2:width=0.12,volume=0.16[tick];"
        "[pad][bass][fifth][mid][air][tick]amix=inputs=6:duration=longest:normalize=0,"
        "highpass=f=50,lowpass=f=5200,"
        "acompressor=threshold=-18dB:ratio=2.8:attack=15:release=180,"
        "afade=t=in:st=0:d=0.7,afade=t=out:st=18.7:d=1.2,volume=1.05",
        "-ar",
        "44100",
        "-ac",
        "2",
        str(path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RenderError("ffmpeg is required to create the news bed") from exc
    except subprocess.CalledProcessError as exc:
        raise RenderError(exc.stderr.strip() or "could not create the news bed") from exc
    if not path.exists() or path.stat().st_size == 0:
        raise RenderError("news bed was not written")
    return path


def _find_logo(root: Path) -> Path | None:
    meta_path = root / "metadata.json"
    if meta_path.exists():
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        name = payload.get("logo")
        if isinstance(name, str) and name:
            candidate = root / Path(name).name
            if candidate.is_file():
                return candidate
    for candidate in sorted(root.glob("logo.*")):
        if candidate.is_file():
            return candidate
    return None
