from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
import time

import cv2
import face_recognition
import numpy as np
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from ..core.config import settings


@dataclass(slots=True)
class RecognitionResult:
    person_id: str
    name: str
    bounding_box: Tuple[int, int, int, int]
    timestamp: float
    frame_index: int


class VideoProcessor:
    def __init__(self, db: AsyncIOMotorDatabase, video_id: str, filename: str) -> None:
        self.db = db
        self.video_id = video_id
        self.filename = filename
        self.people_collection = db[settings.known_faces_collection]
        self.videos_collection = db[settings.videos_collection]
        self.detections_collection = db[settings.detections_collection]
        self.known_encodings: List[np.ndarray] = []
        self.known_ids: List[str] = []
        self.known_names: List[str] = []

    async def load_known_faces(self) -> None:
        cursor = self.people_collection.find({})
        async for person in cursor:
            for enc in person.get("encodings", []):
                self.known_encodings.append(np.array(enc))
                self.known_ids.append(str(person["_id"]))
                self.known_names.append(person["name"])

    async def _create_person(self, encoding: np.ndarray) -> Tuple[str, str]:
        auto_name = f"Person {len(self.known_ids) + 1}"
        document = {
            "name": auto_name,
            "encodings": [encoding.tolist()],
            "metadata": {"auto_generated": True},
            "created_at": datetime.utcnow(),
        }
        result = await self.people_collection.insert_one(document)
        person_id = str(result.inserted_id)

        self.known_encodings.append(encoding)
        self.known_ids.append(person_id)
        self.known_names.append(auto_name)
        return person_id, auto_name

    async def recognise_faces(self, rgb_frame: np.ndarray, locations: List[Tuple[int, int, int, int]]) -> List[RecognitionResult]:
        encodings = face_recognition.face_encodings(rgb_frame, locations)
        results: List[RecognitionResult] = []
        for idx, encoding in enumerate(encodings):
            if self.known_encodings:
                distances = face_recognition.face_distance(self.known_encodings, encoding)
                best_idx = int(np.argmin(distances))
                best_distance = distances[best_idx]
            else:
                best_idx = -1
                best_distance = 1.0

            if best_distance < settings.face_match_threshold and best_idx >= 0:
                person_id = self.known_ids[best_idx]
                name = self.known_names[best_idx]
                await self._augment_person_encoding(best_idx, encoding)
            else:
                person_id, name = await self._create_person(encoding)

            results.append(
                RecognitionResult(
                    person_id=person_id,
                    name=name,
                    bounding_box=locations[idx],
                    timestamp=0.0,  # placeholder, set by caller
                    frame_index=0,
                )
            )
        return results

    async def _augment_person_encoding(self, index: int, encoding: np.ndarray) -> None:
        person_id = self.known_ids[index]
        updated = await self.people_collection.find_one_and_update(
            {"_id": self._to_object_id(person_id)},
            {"$push": {"encodings": encoding.tolist()}},
            return_document=ReturnDocument.AFTER,
        )
        if updated is not None:
            # store the new encoding for future comparisons
            self.known_encodings.append(np.array(updated["encodings"][-1]))
            self.known_ids.append(person_id)
            self.known_names.append(updated["name"])

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

    async def process(self, filepath: Path) -> Dict[str, Any]:
        await self.load_known_faces()

        capture = cv2.VideoCapture(str(filepath))
        if not capture.isOpened():
            raise RuntimeError(f"Could not open video {filepath}")

        fps = capture.get(cv2.CAP_PROP_FPS) or 24.0
        frame_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        start_time = time.perf_counter()

        annotated_dir = settings.processed_root / settings.annotated_videos_dir
        annotated_path = annotated_dir / f"{self.video_id}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(annotated_path), fourcc, fps, (frame_width, frame_height))

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
                rgb_frame = np.ascontiguousarray(frame[:, :, ::-1])
                locations = face_recognition.face_locations(rgb_frame)

                if locations:
                    recognitions = await self.recognise_faces(rgb_frame, locations)
                else:
                    recognitions = []

                for recognition in recognitions:
                    top, right, bottom, left = recognition.bounding_box
                    recognition.timestamp = timestamp
                    recognition.frame_index = frame_index

                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        recognition.name,
                        (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1,
                    )

                    person_summary = summary[recognition.person_id]
                    person_summary["name"] = recognition.name
                    person_summary["appearances"] += 1
                    person_summary["details"].append(
                        {
                            "timestamp": round(recognition.timestamp, 2),
                            "frame_index": recognition.frame_index,
                            "bounding_box": [top, right, bottom, left],
                        }
                    )

                    detection_documents.append(
                        {
                            "video_id": self.video_id,
                            "person_id": recognition.person_id,
                            "person_name": recognition.name,
                            "timestamp": recognition.timestamp,
                            "frame_index": recognition.frame_index,
                            "bounding_box": [top, right, bottom, left],
                            "created_at": datetime.utcnow(),
                        }
                    )

                writer.write(frame)
                frame_index += 1

                processed_frames = frame_index
                if total_frames > 0:
                    progress_percent = min(100.0, (processed_frames / total_frames) * 100)
                else:
                    progress_percent = 0.0

                if (
                    processed_frames == total_frames
                    or processed_frames % progress_update_interval == 0
                ):
                    await self._update_progress(processed_frames, total_frames, progress_percent)
        finally:
            capture.release()
            writer.release()

        total_faces = sum(value["appearances"] for value in summary.values())
        unique_people = len(summary)
        processing_time_seconds = time.perf_counter() - start_time
        summary_payload = {
            "total_faces": total_faces,
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
                    "status": "processing",
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
