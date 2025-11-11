from pathlib import Path
from typing import Any, List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Face Recognition Service"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "face_recognition"
    media_root: Path = Path("data")
    processed_root: Path = Path("outputs")
    annotated_videos_dir: str = "videos"
    reports_dir: str = "reports"
    snapshots_dir: str = "snapshots"
    frame_sample_rate: int = 1  # process every frame by default
    face_match_threshold: float = 0.5
    face_detection_model: str = "cnn"  # 'hog' (faster) or 'cnn' (more accurate)
    face_detection_upsample: int = 2
    min_face_area_ratio: float = 0.0008  # relative to frame area
    output_video_scale: float = 0.7
    snapshot_image_format: str = "jpg"
    known_faces_collection: str = "people"
    videos_collection: str = "videos"
    detections_collection: str = "detections"
    static_dirs: List[str] = ["data", "outputs"]

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", case_sensitive=False)

    def ensure_directories(self) -> None:
        """Create directories required for storing processed artifacts."""
        (self.media_root).mkdir(parents=True, exist_ok=True)
        (self.processed_root / self.annotated_videos_dir).mkdir(parents=True, exist_ok=True)
        (self.processed_root / self.reports_dir).mkdir(parents=True, exist_ok=True)
        (self.processed_root / self.snapshots_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
