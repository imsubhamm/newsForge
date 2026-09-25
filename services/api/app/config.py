from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(repo_root() / ".env", repo_root() / ".env.example"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Bangla News AI Editor"
    app_env: str = "development"
    log_level: str = "info"

    storage_path: Path = repo_root() / "storage"
    database_url: str = f"sqlite:///{repo_root() / 'data' / 'news_editor.db'}"

    mock_ai: bool = True
    ai_provider: str = "openai"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    openai_vision_model: str = "gpt-4.1-mini"

    whisper_model: str = "small"
    whisper_device: str = "auto"
    whisper_compute_type: str = "int8"
    mock_whisper: bool = False

    video_fps: int = 30
    video_width: int = 1080
    video_height: int = 1920
    default_crop_mode: str = "center-crop"
    match_threshold: float = 0.45
    target_cut_min: float = 2.0
    target_cut_max: float = 6.0
    nat_sound_volume: float = 0.18
    audio_fade_ms: int = 200
    bite_quality_min: float = 0.4
    bite_relevance_min: float = 0.62
    bite_overlap_replace: float = 0.55
    bite_unique_insert: float = 0.55

    max_upload_bytes: int = 2 * 1024 * 1024 * 1024
    allowed_audio_suffixes: tuple[str, ...] = (".mp3", ".wav", ".m4a")
    allowed_video_suffixes: tuple[str, ...] = (".mp4", ".mov")
    allowed_logo_suffixes: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp", ".svg")

    @property
    def jobs_dir(self) -> Path:
        return (self.storage_path if self.storage_path.is_absolute() else repo_root() / self.storage_path) / "jobs"

    @property
    def data_dir(self) -> Path:
        return repo_root() / "data"

    @property
    def sqlite_path(self) -> Path:
        raw = self.database_url
        if raw.startswith("sqlite:///"):
            path = Path(raw.removeprefix("sqlite:///"))
            return path if path.is_absolute() else repo_root() / path
        return self.data_dir / "news_editor.db"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.jobs_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
