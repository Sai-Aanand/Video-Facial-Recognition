export interface AppearanceDetail {
  timestamp: number;
  frame_index: number;
  bounding_box: number[];
}

export interface PersonSummary {
  person_id: string;
  name: string;
  appearances: number;
  details: AppearanceDetail[];
}

export interface VideoSummary {
  total_faces: number;
  unique_people: number;
  per_person: PersonSummary[];
}

export interface VideoRecord {
  video_id: string;
  filename: string;
  created_at: string;
  status: string;
  processing_time_seconds?: number | null;
  processing_progress?: number | null;
  annotated_video_url?: string | null;
  report_url?: string | null;
  summary: VideoSummary;
}

export interface UploadResponse extends VideoRecord {}

export interface ApiError {
  detail: string;
}
