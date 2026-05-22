export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: "draft" | "processing" | "ready" | "exported";
  speaker_count: number;
  silence_threshold_ms: number;
  filler_words: string[];
  created_at: string;
  updated_at: string;
}

export interface Clip {
  id: string;
  project_id: string;
  filename: string;
  storage_path: string;
  sequence_order: number;
  duration_ms: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  file_size_bytes: number | null;
  status: "uploaded" | "transcribing" | "transcribed" | "analyzed" | "error";
  created_at: string;
}

export interface Speaker {
  id: string;
  project_id: string;
  label: string;
  color: string;
}

export interface TranscriptSegment {
  id: string;
  clip_id: string;
  speaker_id: string | null;
  start_ms: number;
  end_ms: number;
  text: string;
  confidence: number | null;
  word_timestamps: WordTimestamp[] | null;
  segment_type: "speech" | "filler" | "silence" | "repeated_take";
  cut_decision: "keep" | "cut" | "user_restored" | "user_cut";
  cut_reason: string | null;
  duplicate_group_id: string | null;
  quality_score: number | null;
}

export interface WordTimestamp {
  word: string;
  start_ms: number;
  end_ms: number;
}

export interface ProcessingJob {
  id: string;
  project_id: string;
  job_type: "transcribe" | "analyze" | "render";
  status: "queued" | "running" | "completed" | "failed";
  progress_pct: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at?: string;
}

export interface VideoExport {
  id: string;
  project_id: string;
  storage_path: string;
  format: string;
  resolution: string | null;
  file_size_bytes: number | null;
  duration_ms: number | null;
  created_at: string;
}
