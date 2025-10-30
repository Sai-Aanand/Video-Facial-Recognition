from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
import shutil
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..core.config import settings
from ..core.database import get_database, get_client
from ..pdf.report import build_report
from ..schemas.video import VideoListItem, VideoSummary, VideoUploadResponse
from ..services.video_processor import VideoProcessor

router = APIRouter(prefix="/api/videos", tags=["videos"])

EMPTY_SUMMARY = VideoSummary(total_faces=0, unique_people=0, per_person=[])


async def _save_upload(file: UploadFile, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = await file.read()
    destination.write_bytes(data)
    return destination


def _object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=400, detail="Invalid identifier")
    return ObjectId(value)


async def _process_video_async(video_id_str: str, filename: str, saved_path: Path) -> None:
    client = get_client()
    db = client[settings.mongo_db]
    videos_collection = db[settings.videos_collection]

    oid = _object_id(video_id_str)

    try:
        processor = VideoProcessor(db, video_id_str, filename)
        result = await processor.process(saved_path)

        report_dir = settings.processed_root / settings.reports_dir
        report_path = report_dir / f"{video_id_str}.pdf"
        build_report(
            {
                "video_id": video_id_str,
                "filename": filename,
                "summary": result["summary"],
            },
            report_path,
        )

        await videos_collection.update_one(
            {"_id": oid},
            {
                "$set": {
                    "report_path": str(report_path),
                    "status": "completed",
                    "processing_time_seconds": result.get("processing_time_seconds"),
                    "processing_progress": 100.0,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
    except Exception as exc:  # pragma: no cover - background failure logging
        await videos_collection.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": "failed",
                    "error": str(exc),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        raise


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(file: Optional[UploadFile] = File(None), video_path: Optional[str] = Form(None), db=Depends(get_database)):
    if file is None and not video_path:
        raise HTTPException(status_code=400, detail="Provide either an uploaded file or a video_path.")

    video_id = ObjectId()
    video_id_str = str(video_id)

    if file is not None:
        filename = file.filename or "uploaded_video.mp4"
        stored_filename = f"{video_id_str}_{filename}"
        saved_path = settings.media_root / stored_filename
        await _save_upload(file, saved_path)
    else:
        source = Path(video_path).expanduser()
        if not source.exists():
            raise HTTPException(status_code=404, detail=f"Provided video path {video_path} does not exist.")
        filename = source.name
        stored_filename = f"{video_id_str}_{filename}"
        saved_path = settings.media_root / stored_filename
        shutil.copy2(source, saved_path)

    videos_collection = db[settings.videos_collection]
    created_at = datetime.utcnow()
    video_doc = {
        "_id": video_id,
        "filename": filename,
        "stored_filename": stored_filename,
        "original_path": str(saved_path),
        "annotated_path": None,
        "report_path": None,
        "status": "processing",
        "processing_time_seconds": None,
        "processing_progress": 0.0,
        "processed_frames": 0,
        "total_frames": None,
        "summary": EMPTY_SUMMARY.model_dump(),
        "created_at": created_at,
        "updated_at": created_at,
    }
    await videos_collection.insert_one(video_doc)

    asyncio.create_task(_process_video_async(video_id_str, filename, saved_path))

    return VideoUploadResponse(
        video_id=video_id_str,
        filename=filename,
        created_at=created_at,
        status="processing",
        processing_time_seconds=None,
        processing_progress=0.0,
        annotated_video_url=None,
        report_url=None,
        summary=EMPTY_SUMMARY.model_copy(),
    )


@router.get("/", response_model=List[VideoListItem])
async def list_videos(db=Depends(get_database)):
    videos_collection = db[settings.videos_collection]
    cursor = videos_collection.find().sort("created_at", -1)
    videos: List[VideoListItem] = []
    async for video in cursor:
        summary = video.get("summary") or {"total_faces": 0, "unique_people": 0, "per_person": []}
        videos.append(
            VideoListItem(
                video_id=str(video["_id"]),
                filename=video["filename"],
                created_at=video["created_at"],
                status=video.get("status", "unknown"),
                processing_time_seconds=video.get("processing_time_seconds"),
                processing_progress=video.get("processing_progress"),
                summary=VideoSummary(**summary),
            )
        )
    return videos


@router.get("/{video_id}", response_model=VideoUploadResponse)
async def get_video(video_id: str, db=Depends(get_database)):
    videos_collection = db[settings.videos_collection]
    oid = _object_id(video_id)
    video = await videos_collection.find_one({"_id": oid})
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    summary = video.get("summary") or {"total_faces": 0, "unique_people": 0, "per_person": []}

    annotated_url = None
    report_url = None
    if video.get("annotated_path"):
        annotated_url = f"/api/videos/{video_id}/annotated"
    if video.get("report_path"):
        report_url = f"/api/videos/{video_id}/report"

    return VideoUploadResponse(
        video_id=video_id,
        filename=video["filename"],
        created_at=video["created_at"],
        status=video.get("status", "unknown"),
        processing_time_seconds=video.get("processing_time_seconds"),
        processing_progress=video.get("processing_progress"),
        annotated_video_url=annotated_url,
        report_url=report_url,
        summary=VideoSummary(**summary),
    )


@router.get("/{video_id}/annotated")
async def download_annotated(video_id: str, db=Depends(get_database)):
    oid = _object_id(video_id)
    video = await db[settings.videos_collection].find_one({"_id": oid})
    if not video or not video.get("annotated_path"):
        raise HTTPException(status_code=404, detail="Annotated video not available")
    path = Path(video["annotated_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Annotated video file missing on server")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@router.get("/{video_id}/report")
async def download_report(video_id: str, db=Depends(get_database)):
    oid = _object_id(video_id)
    video = await db[settings.videos_collection].find_one({"_id": oid})
    if not video or not video.get("report_path"):
        raise HTTPException(status_code=404, detail="Report not available")
    path = Path(video["report_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file missing on server")
    return FileResponse(path, media_type="application/pdf", filename=path.name)
