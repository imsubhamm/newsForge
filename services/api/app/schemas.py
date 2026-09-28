from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


AudioMode = Literal["VOICEOVER_ONLY", "SOURCE_SOUNDBITE", "VOICEOVER_WITH_NAT_SOUND", "NAT_SOUND_ONLY"]
AudioType = Literal[
    "voiceover_candidate",
    "reporter_standup",
    "interview",
    "official_statement",
    "eyewitness_bite",
    "local_resident_bite",
    "reaction",
    "natural_sound",
    "ambient_sound",
    "background_chatter",
    "irrelevant_speech",
    "unusable_audio",
    "soundbite",
]


class ClipAudio(BaseModel):
    mode: AudioMode = "VOICEOVER_ONLY"
    voiceover_enabled: bool = True
    voiceover_start: float | None = None
    voiceover_end: float | None = None
    source: str | None = None
    source_start: float | None = None
    source_end: float | None = None
    voice_volume: float = 1.0
    source_volume: float = 0.0
    editorial_action: str = "KEEP_VOICEOVER"
    reason: str = ""
    audio_segment_id: str = ""
    needs_review: bool = False
    override: bool = False


class TimelineClip(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    source: str
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)
    reason: str = ""
    crop_mode: Literal["center-crop", "blur-background", "fit"] | None = None
    match_score: float = 0.0
    needs_review: bool = False
    narration_segment_id: str = ""
    scene_id: str = ""
    audio: ClipAudio = Field(default_factory=ClipAudio)

    @field_validator("source")
    @classmethod
    def source_must_be_filename(cls, value: str) -> str:
        if not value or "/" in value or "\\" in value or ".." in value:
            raise ValueError("source must be a bare footage filename")
        return value


class CaptionCue(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str
    source: Literal["REPORTER_SCRIPT", "VIDEO_SOUNDBITE"] = "REPORTER_SCRIPT"


class TimelinePlan(BaseModel):
    headline: str
    location: str = ""
    reporter_name: str = ""
    duration: float = Field(gt=0)
    crop_mode: Literal["center-crop", "blur-background", "fit"] = "center-crop"
    timeline: list[TimelineClip]
    captions: list[CaptionCue] = Field(default_factory=list)
    footage_warning: str | None = None
    editor: str = "semantic"
    weak_match_count: int = 0

    @field_validator("timeline")
    @classmethod
    def timeline_must_cover_duration(cls, clips: list[TimelineClip], info):
        if not clips:
            raise ValueError("timeline must contain at least one clip")
        cursor = 0.0
        for clip in clips:
            if clip.end <= clip.start:
                raise ValueError("clip end must be greater than start")
            if clip.source_end <= clip.source_start:
                raise ValueError("source_end must be greater than source_start")
            if abs((clip.end - clip.start) - (clip.source_end - clip.source_start)) > 0.15:
                raise ValueError("source duration must match timeline duration")
            if abs(clip.start - cursor) > 0.15:
                raise ValueError("timeline must be contiguous from 0")
            cursor = clip.end
        return clips


class TranscriptWord(BaseModel):
    start: float
    end: float
    text: str


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class Transcript(BaseModel):
    language: str = "bn"
    duration: float = Field(ge=0)
    segments: list[TranscriptSegment] = Field(default_factory=list)
    words: list[TranscriptWord] = Field(default_factory=list)
    source: str = "faster-whisper"
    model: str = ""


class AlignmentResult(BaseModel):
    script_authoritative: bool = True
    match_ratio: float = 0.0
    duration: float = Field(ge=0)
    cues: list[CaptionCue] = Field(default_factory=list)
    source: str = "whisper+script"


class NarrationSegment(BaseModel):
    id: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str
    type: str = "event"
    summary: str = ""
    entities: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    location: str | None = None
    visual_requirements: list[str] = Field(default_factory=list)
    audio_intent: Literal["script", "soundbite"] = "script"


class VisualScene(BaseModel):
    scene_id: str
    source_file: str
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)
    duration: float = Field(gt=0)
    description: str = ""
    environment: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    shot_type: str = "unknown"
    camera_motion: str = "unknown"
    quality_score: float = 0.7
    stability_score: float = 0.7
    visual_interest_score: float = 0.7
    crop_mode: Literal["center-crop", "blur-background", "fit"] = "center-crop"
    frame_paths: list[str] = Field(default_factory=list)


class SceneCandidate(BaseModel):
    scene_id: str
    source_file: str
    source_start: float
    source_end: float
    score: float
    selected: bool = False
    reason: str = ""


class NarrationMatchDebug(BaseModel):
    narration_segment_id: str
    text: str
    start: float
    end: float
    candidates: list[SceneCandidate] = Field(default_factory=list)


class AudioSegment(BaseModel):
    id: str
    source_file: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    contains_speech: bool = False
    transcript: str = ""
    speaker_type: str = "unknown"
    audio_type: AudioType = "ambient_sound"
    speech_quality: float = 0.0
    information_value: float = 0.0
    news_relevance: float = 0.0
    rms: float = 0.0
    peak: float = 0.0
    playback_gain: float = 1.0


class AudioComparison(BaseModel):
    audio_id: str
    semantic_relevance: float = 0.0
    information_overlap: float = 0.0
    unique_information: float = 0.0
    evidence_value: float = 0.0
    speaker_value: float = 0.0
    audio_quality: float = 0.0


class AudioCandidateDebug(BaseModel):
    audio_id: str
    source_file: str
    speaker_type: str = "unknown"
    audio_type: str = ""
    transcript: str = ""
    relevance: float = 0.0
    quality: float = 0.0
    decision: str = "MUTE"
    action: str = ""
    selected: bool = False


class AudioMatchDebug(BaseModel):
    narration_segment_id: str
    text: str
    start: float
    end: float
    mode: AudioMode = "VOICEOVER_ONLY"
    action: str = "KEEP_VOICEOVER"
    reason: str = ""
    candidates: list[AudioCandidateDebug] = Field(default_factory=list)


class SemanticDebug(BaseModel):
    duration: float
    threshold: float
    narration: list[NarrationSegment] = Field(default_factory=list)
    scenes: list[VisualScene] = Field(default_factory=list)
    matches: list[NarrationMatchDebug] = Field(default_factory=list)
    audio_matches: list[AudioMatchDebug] = Field(default_factory=list)


class JobAsset(BaseModel):
    kind: str
    filename: str
    path: str
    size_bytes: int


class JobResponse(BaseModel):
    id: str
    title: str
    location: str
    reporter_name: str
    status: str
    error: str | None = None
    created_at: str
    steps: dict[str, bool]
    assets: list[JobAsset] = Field(default_factory=list)
    output_url: str | None = None
    captions: list[CaptionCue] = Field(default_factory=list)
    transcript_available: bool = False
    alignment_available: bool = False
    semantic_available: bool = False
    audio_available: bool = False
    weak_match_count: int = 0
    footage_warning: str | None = None


class AudioOverrideRequest(BaseModel):
    clip_index: int = Field(ge=0)
    mode: AudioMode


class JobListResponse(BaseModel):
    jobs: list[JobResponse]


AspectRatio = Literal["16:9", "9:16"]


class FrameJobResponse(BaseModel):
    id: str
    aspect_ratio: AspectRatio
    headline: str
    header: str = ""
    footer: str = ""
    location: str = ""
    channel_name: str
    status: str
    error: str | None = None
    created_at: str
    width: int
    height: int
    output_url: str | None = None
    overlay_url: str | None = None
    source_filename: str | None = None


class FrameJobListResponse(BaseModel):
    jobs: list[FrameJobResponse]


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    job_id: str | None = None
