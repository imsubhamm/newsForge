from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class JobStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    TRANSCRIBING = "TRANSCRIBING"
    ALIGNING = "ALIGNING"
    ALIGNED = "ALIGNED"
    ANALYSING_FOOTAGE = "ANALYSING_FOOTAGE"
    CREATING_TIMELINE = "CREATING_TIMELINE"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    location: Mapped[str] = mapped_column(String(200), default="")
    reporter_name: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(40), default=JobStatus.UPLOADED.value)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_steps: Mapped[int] = mapped_column(Integer, default=1)


class FrameJobStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FrameJob(Base):
    __tablename__ = "frame_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    aspect_ratio: Mapped[str] = mapped_column(String(8), default="16:9")
    headline: Mapped[str] = mapped_column(String(300), default="")
    channel_name: Mapped[str] = mapped_column(String(200), default="বাংলা নিউজ")
    status: Mapped[str] = mapped_column(String(40), default=FrameJobStatus.UPLOADED.value)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
