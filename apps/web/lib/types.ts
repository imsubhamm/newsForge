export type JobAsset = {
  kind: string;
  filename: string;
  path: string;
  size_bytes: number;
};

export type CaptionCue = {
  start: number;
  end: number;
  text: string;
  source?: "REPORTER_SCRIPT" | "VIDEO_SOUNDBITE";
};

export type AudioMode = "VOICEOVER_ONLY" | "SOURCE_SOUNDBITE" | "VOICEOVER_WITH_NAT_SOUND" | "NAT_SOUND_ONLY";

export type ClipAudio = {
  mode: AudioMode;
  voiceover_enabled: boolean;
  voice_volume: number;
  source_volume: number;
  editorial_action: string;
  reason: string;
  audio_segment_id: string;
  needs_review: boolean;
  override?: boolean;
};

export type TimelineClip = {
  start: number;
  end: number;
  source: string;
  source_start: number;
  source_end: number;
  narration_segment_id: string;
  audio: ClipAudio;
};

export type TimelinePlan = {
  duration: number;
  timeline: TimelineClip[];
  captions: CaptionCue[];
};

export type Job = {
  id: string;
  title: string;
  location: string;
  reporter_name: string;
  status: string;
  error: string | null;
  created_at: string;
  steps: Record<string, boolean>;
  assets: JobAsset[];
  output_url: string | null;
  captions: CaptionCue[];
  transcript_available: boolean;
  alignment_available: boolean;
  semantic_available: boolean;
  audio_available: boolean;
  weak_match_count: number;
  footage_warning: string | null;
};

export type SceneCandidate = {
  scene_id: string;
  source_file: string;
  source_start: number;
  source_end: number;
  score: number;
  selected: boolean;
  reason: string;
};

export type SemanticDebug = {
  duration: number;
  threshold: number;
  matches: {
    narration_segment_id: string;
    text: string;
    start: number;
    end: number;
    candidates: SceneCandidate[];
  }[];
  audio_matches?: {
    narration_segment_id: string;
    text: string;
    start: number;
    end: number;
    mode: AudioMode;
    action: string;
    reason: string;
    candidates: {
      audio_id: string;
      source_file: string;
      speaker_type: string;
      audio_type: string;
      transcript: string;
      relevance: number;
      quality: number;
      decision: string;
      action: string;
      selected: boolean;
    }[];
  }[];
};

export const STEP_LABELS: Record<string, string> = {
  assets_uploaded: "Assets uploaded",
  voice_analysed: "Voice analysed",
  script_aligned: "Script aligned",
  footage_processed: "Footage processed",
  scenes_analysed: "Scenes analysed",
  ai_editing_complete: "AI editing complete",
  bengali_subtitles_created: "Bengali subtitles created",
  video_rendered: "Video rendered",
};

export const TERMINAL_STATUSES = new Set(["COMPLETED", "FAILED"]);
