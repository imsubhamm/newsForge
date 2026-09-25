from io import BytesIO

from fastapi import UploadFile

from app.config import Settings
from app.services.uploads import UploadValidationError, validate_audio, validate_logo, validate_video


def _file(name: str, content_type: str) -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(b"data"), headers={"content-type": content_type})


def test_accepts_supported_media_types() -> None:
    settings = Settings()
    validate_audio(_file("voice.mp3", "audio/mpeg"), settings)
    validate_audio(_file("AUD-20260925-WA00007.m4a", "audio/mp4"), settings)
    validate_video(_file("clip01.mp4", "video/mp4"), settings)
    validate_video(_file("clip02.mov", "video/quicktime"), settings)
    validate_logo(_file("logo.png", "image/png"), settings)


def test_accepts_whatsapp_export_with_odd_mime() -> None:
    settings = Settings()
    validate_audio(_file("voice.m4a", "audio/aac"), settings)
    validate_video(_file("WhatsApp Video 2026-09-25 at 13.40.34.mp4", "application/mp4"), settings)
    validate_video(_file("clip03.mp4", "application/octet-stream"), settings)


def test_rejects_unsupported_script_disguised_as_video() -> None:
    settings = Settings()
    try:
        validate_video(_file("notes.txt", "text/plain"), settings)
    except UploadValidationError as exc:
        assert "unsupported footage" in str(exc)
    else:
        raise AssertionError("expected UploadValidationError")


def test_rejects_missing_filename() -> None:
    settings = Settings()
    upload = UploadFile(filename="", file=BytesIO(b"x"), headers={"content-type": "audio/mpeg"})
    try:
        validate_audio(upload, settings)
    except UploadValidationError as exc:
        assert "missing a name" in str(exc)
    else:
        raise AssertionError("expected UploadValidationError")
