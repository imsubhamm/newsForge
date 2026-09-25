from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from app.config import Settings

AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mp4",
    "audio/x-m4a",
    "audio/m4a",
    "audio/aac",
    "audio/3gpp",
    "video/mp4",  # some browsers label AAC/M4A this way
}
VIDEO_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-m4v",
    "video/3gpp",
    "application/mp4",
}
LOGO_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/svg+xml"}


class UploadValidationError(ValueError):
    pass


def suffix_of(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_audio(file: UploadFile, settings: Settings) -> None:
    _validate_named_file(file, settings.allowed_audio_suffixes, AUDIO_TYPES, "voice-over")


def validate_video(file: UploadFile, settings: Settings) -> None:
    _validate_named_file(file, settings.allowed_video_suffixes, VIDEO_TYPES, "footage")


def validate_logo(file: UploadFile, settings: Settings) -> None:
    _validate_named_file(file, settings.allowed_logo_suffixes, LOGO_TYPES, "logo")


def _validate_named_file(
    file: UploadFile,
    allowed_suffixes: tuple[str, ...],
    allowed_types: set[str],
    label: str,
) -> None:
    if not file.filename:
        raise UploadValidationError(f"{label} file is missing a name")
    suffix = suffix_of(file.filename)
    content_type = (file.content_type or "").lower()
    if suffix not in allowed_suffixes:
        raise UploadValidationError(
            f"unsupported {label} type '{suffix or 'unknown'}'. allowed: {', '.join(allowed_suffixes)}"
        )
    # Reporter phones (WhatsApp, iPhone) often send odd or empty MIME types.
    # The file extension is authoritative; unknown MIME is allowed.
    if content_type and content_type not in allowed_types and content_type not in {
        "application/octet-stream",
        "binary/octet-stream",
        "",
    }:
        if suffix in allowed_suffixes:
            return
        raise UploadValidationError(f"unsupported {label} content type '{content_type}'")
