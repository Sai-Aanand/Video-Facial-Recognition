from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
import time
import uuid

import cv2
import numpy as np
import supervision as sv
from motor.motor_asyncio import AsyncIOMotorDatabase
from ultralytics import YOLO

from ..core.config import settings


class VideoProcessor:
    _detector: YOLO | None = None

    def __init__(self, db: AsyncIOMotorDatabase, video_id: str, filename: str) -> None:
        self.db = db
        self.video_id = video_id
        self.filename = filename
        self.videos_collection = db[settings.videos_collection]
        self.detections_collection = db[settings.detections_collection]
        self.snapshot_root = settings.processed_root / settings.snapshots_dir / self.video_id
        self.snapshot_root.mkdir(parents=True, exist_ok=True)
        self.detector = self._load_detector()
        self.tracker = sv.ByteTrack()

    @classmethod
    def _load_detector(cls) -> YOLO:
        if cls._detector is None:
            weights = getattr(settings, "yolo_model_path", "yolov8n.pt")
            cls._detector = YOLO(weights)
        return cls._detector

    async def _update_progress(self, processed_frames: int, total_frames: int, progress_percent: float) -> None:
        await self.videos_collection.update_one(
            {"_id": self._to_object_id(self.video_id)},
            {
                "$set": {
                    "processed_frames": processed_frames,
                    "total_frames": total_frames,
                    "processing_progress": round(progress_percent, 2),
                    "updated_at": datetime.utcnow(),
                }
            },
        )

    def _save_snapshot(self, frame: np.ndarray, bbox: Tuple[int, int, int, int], tracker_label: str, frame_index: int) -> Path | None:
        top, right, bottom, left = bbox
        margin = 5
        height, width, _ = frame.shape
        top = max(0, top - margin)
        left = max(0, left - margin)
        bottom = min(height, bottom + margin)
        right = min(width, right + margin)

        if bottom <= top or right <= left:
            return None

        crop = frame[top:bottom, left:right]
        if crop.size == 0:
            return None

        person_dir = self.snapshot_root / tracker_label
        person_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{frame_index}_{uuid.uuid4().hex[:8]}.{settings.snapshot_image_format}"
        snapshot_path = person_dir / filename
        cv2.imwrite(str(snapshot_path), crop)
        return snapshot_path

    async def process(self, filepath: Path) -> Dict[str, Any]:
        capture = cv2.VideoCapture(str(filepath))
        if not capture.isOpened():
            raise RuntimeError(f"Could not open video {filepath}")

        fps = capture.get(cv2.CAP_PROP_FPS) or 24.0
        frame_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        start_time = time.perf_counter()

        scale = max(0.2, min(1.0, settings.output_video_scale))
        output_width = max(1, int(frame_width * scale))
        output_height = max(1, int(frame_height * scale))

        annotated_dir = settings.processed_root / settings.annotated_videos_dir
        annotated_path = annotated_dir / f"{self.video_id}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(annotated_path), fourcc, fps, (output_width, output_height))

        summary: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"name": "", "appearances": 0, "details": []})
        detection_documents: List[Dict[str, Any]] = []

        progress_update_interval = max(1, (total_frames // 20) or 1) if total_frames else 30
        frame_index = 0
        try:
            while True:
                ret, frame = capture.read()
                if not ret:
                    break

                timestamp = frame_index / fps if fps else 0.0

                results = self.detector(
                    frame,
                    conf=getattr(settings, "detection_confidence", 0.35),
                    classes=[0],
                    verbose=False,
                )[0]
                detections = sv.Detections.from_ultralytics(results)
                tracked = self.tracker.update_with_detections(detections)

                for xyxy, tracker_id, confidence in zip(tracked.xyxy, tracked.tracker_id, tracked.confidence):
                    if tracker_id is None:
                        continue

                    x1, y1, x2, y2 = xyxy.astype(int)
                    bbox = (int(y1), int(x2), int(y2), int(x1))  # top, right, bottom, left
                    label = f"Person {int(tracker_id)}"
                    person_key = str(int(tracker_id))

                    snapshot_path = self._save_snapshot(frame, bbox, person_key, frame_index)
                    snapshot_str = str(snapshot_path) if snapshot_path else None

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        label,
                        (x1, max(0, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1,
                    )

                    person_summary = summary[person_key]
                    person_summary["name"] = label
                    person_summary["appearances"] += 1
                    person_summary["details"].append(
                        {
                            "timestamp": round(timestamp, 2),
                            "frame_index": frame_index,
                            "bounding_box": [int(y1), int(x2), int(y2), int(x1)],
                            "confidence": round(float(confidence or 0), 3),
                            "snapshot_path": snapshot_str,
                        }
                    )

                    detection_documents.append(
                        {
                            "video_id": self.video_id,
                            "person_id": person_key,
                            "person_name": label,
                            "timestamp": timestamp,
                            "frame_index": frame_index,
                            "bounding_box": [int(y1), int(x2), int(y2), int(x1)],
                            "confidence": float(confidence or 0),
                            "snapshot_path": snapshot_str,
                            "created_at": datetime.utcnow(),
                        }
                    )

                annotated_frame = cv2.resize(frame, (output_width, output_height))
                writer.write(annotated_frame)
                frame_index += 1

                processed_frames = frame_index
                progress_percent = min(100.0, (processed_frames / total_frames) * 100) if total_frames else 0.0

                if processed_frames == total_frames or processed_frames % progress_update_interval == 0:
                    await self._update_progress(processed_frames, total_frames, progress_percent)
        finally:
            capture.release()
            writer.release()

        total_people = sum(value["appearances"] for value in summary.values())
        unique_people = len(summary)
        processing_time_seconds = time.perf_counter() - start_time
        summary_payload = {
            "total_faces": total_people,
            "unique_people": unique_people,
            "per_person": [
                {
                    "person_id": person_id,
                    "name": data["name"],
                    "appearances": data["appearances"],
                    "details": data["details"],
                }
                for person_id, data in summary.items()
            ],
        }

        if detection_documents:
            await self.detections_collection.insert_many(detection_documents)

        await self.videos_collection.update_one(
            {"_id": self._to_object_id(self.video_id)},
            {
                "$set": {
                    "annotated_path": str(annotated_path),
                    "summary": summary_payload,
                    "total_frames": total_frames,
                    "fps": fps,
                    "status": "processed",
                    "processing_time_seconds": processing_time_seconds,
                    "processing_progress": 100.0,
                    "processed_frames": frame_index,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        return {
            "annotated_path": annotated_path,
            "summary": summary_payload,
            "fps": fps,
            "total_frames": total_frames,
            "processing_time_seconds": processing_time_seconds,
        }

    @staticmethod
    def _to_object_id(id_str: str):
        from bson import ObjectId

        return ObjectId(id_str)
