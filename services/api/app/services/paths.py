from __future__ import annotations

import re
from pathlib import Path

SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


class UnsafePathError(ValueError):
    pass


def sanitize_filename(name: str, fallback: str) -> str:
    raw = Path(name).name.strip()
    if not raw or raw in {".", ".."}:
        return fallback
    cleaned = SAFE_FILENAME.sub("_", raw)
    cleaned = cleaned.lstrip(".")
    return cleaned or fallback


def resolve_under(root: Path, relative: str | Path) -> Path:
    candidate = (root / relative).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise UnsafePathError("path escapes storage root")
    return candidate


def job_dir(jobs_root: Path, job_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,32}", job_id):
        raise UnsafePathError("invalid job id")
    return resolve_under(jobs_root, job_id)
