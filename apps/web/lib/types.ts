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
