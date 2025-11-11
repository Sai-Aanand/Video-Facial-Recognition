from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class PersonCount(BaseModel):
    person_id: str
    name: str
    appearances: int


class AppearanceDetail(BaseModel):
    timestamp: float
    frame_index: int
    bounding_box: List[int]
    snapshot_path: Optional[str] = None


class PersonSummary(BaseModel):
    person_id: str
    name: str
    appearances: int
    details: List[AppearanceDetail]


class VideoSummary(BaseModel):
    total_faces: int
    unique_people: int
    per_person: List[PersonSummary]


class VideoUploadResponse(BaseModel):
    video_id: str
    filename: str
    created_at: datetime
    status: str
    processing_time_seconds: Optional[float] = None
    processing_progress: Optional[float] = None
    annotated_video_url: Optional[str] = None
    report_url: Optional[str] = None
    summary: VideoSummary


class VideoListItem(BaseModel):
    video_id: str
    filename: str
    created_at: datetime
    status: str
    processing_time_seconds: Optional[float] = None
    processing_progress: Optional[float] = None
    summary: VideoSummary
