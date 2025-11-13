# Person Recognition CCTV Processing Suite

Full-stack system for processing CCTV footage with automated person detection/tracking, annotated exports, and PDF reporting. The stack pairs a FastAPI backend (Python) with a React dashboard and persists data in MongoDB. Detection relies on the open-source [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) model with ByteTrack-based ID assignment so every person in view is captured, timestamped, and documented with snapshots.

## Features
- Upload CCTV recordings or reference a server-side video path.
- Detect every person in each frame using the YOLOv8 model (with ByteTrack ID association), draw bounding boxes, and annotate the video output.
- Auto-build a roster of tracked people per video, storing their timestamps, snapshots, and bounding boxes for reporting.
- Produce a PDF report summarising identified individuals, appearance counts, timestamps, bounding boxes, and embedded image evidence for every detection.
- Persist face snapshots per detection so investigations have visual proof per person.
- React dashboard to trigger processing, inspect summaries, watch live progress, and download deliverables (detailed logs live only inside the downloadable PDF to keep the UI concise).

## Project Layout
```
backend/
  app/
    api/                 # FastAPI routes
    core/                # Settings and database connectors
    pdf/                 # Report generator (ReportLab)
    services/            # Video processing + recognition pipeline
    schemas/             # Pydantic response models
  requirements.txt
  .env.example
frontend/
  src/                   # React UI (Vite + TypeScript)
  package.json
outputs/
  videos/                # Annotated MP4 exports (auto-created)
  reports/               # Generated PDF reports (auto-created)
  snapshots/             # Cropped evidence images grouped by video/person
data/                    # Uploaded/source videos (auto-created)
```

## Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB (local or remote)
- PyTorch runtime for YOLOv8 (CPU-only is fine; install `torch` automatically via `ultralytics` when running `pip install -r requirements.txt`). GPU accelerates processing but is optional.

## Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # adjust Mongo URI, storage paths, or thresholds
python -m uvicorn app.main:app --reload
```

Environment variables (via `.env` / OS vars):
- `APP_MONGO_URI` – Mongo connection string (default `mongodb://localhost:27017`).
- `APP_MONGO_DB` – Database name (default `face_recognition`).
- `APP_MEDIA_ROOT` – Directory for uploaded videos (default `data`).
- `APP_PROCESSED_ROOT` – Directory for processed assets (default `outputs`).
- `APP_SNAPSHOTS_DIR` – Subdirectory (under `APP_PROCESSED_ROOT`) for cropped evidence images (default `snapshots`).
- `APP_OUTPUT_VIDEO_SCALE` – Scale factor for exported annotated video resolution (default `0.7` for smaller, faster MP4s).
- `APP_SNAPSHOT_IMAGE_FORMAT` – Image format for saved face crops (default `jpg`).
- `APP_YOLO_MODEL_PATH` (optional) – Path/name of the YOLOv8 weights file (default `yolov8n.pt`, auto-downloaded).
- `APP_DETECTION_CONFIDENCE` – Confidence threshold for YOLO detections (default `0.35`).

### Processing Workflow
1. Client uploads footage or provides a file path.
2. Video saved under `APP_MEDIA_ROOT` with a unique prefix.
3. `VideoProcessor` iterates through frames, runs YOLOv8 person detection + ByteTrack tracking, and stores bounding boxes/timestamps for every tracked individual.
4. Cropped snapshots are saved per person to provide visual evidence, and detections (including confidences) are logged to MongoDB.
5. Bounding boxes are drawn using OpenCV; progress is persisted so the dashboard can poll and render live status updates.
6. Progress (frames processed, percent complete) is persisted so the dashboard can poll and render live status updates.
7. Summary and metadata stored in the `videos` collection.
8. A PDF report (with embedded thumbnails and timestamps) is produced with ReportLab under `outputs/reports/<video_id>.pdf`.

API endpoints:
- `POST /api/videos/upload` – Upload/process video (multipart form with `file` or `video_path`).
- `GET /api/videos` – List processed videos.
- `GET /api/videos/{video_id}` – Fetch summary & download links.
- `GET /api/videos/{video_id}/annotated` – Download annotated MP4.
- `GET /api/videos/{video_id}/report` – Download PDF report.
- `GET /health` – Service health check.

## Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The Vite dev server proxies `/api` requests to `http://localhost:8000`, so run FastAPI on port 8000 (default for `uvicorn`).

### Dashboard Highlights
- Upload panel supporting both file uploads and server-side path submission.
- Processing history table (latest-first) with quick access to prior results.
- UI stays lightweight; per-person timelines and evidence live exclusively in the downloadable PDF report.
- Download buttons for annotated video and PDF report.

## Data Model (MongoDB)
- `videos`: `{ _id, filename, stored_filename, original_path, annotated_path, report_path, status, processing_time_seconds, processing_progress, processed_frames, total_frames, summary, created_at, updated_at }`
- `detections`: `{ video_id, person_id, person_name, timestamp, frame_index, bounding_box[], confidence, snapshot_path, created_at }`

## Testing & Verification
- Run `uvicorn app.main:app --reload` and `npm run dev`; process sample videos to confirm annotated outputs and reports.
- Inspect MongoDB collections to verify new people and detection logs are persisted.
- Generated assets reside under `outputs/videos` and `outputs/reports`.

## Future Enhancements
- Offload video processing to background workers (Celery/RQ) for long-running tasks.
- Add authentication and role-based dashboard access.
- Integrate web-based face enrollment and manual identity corrections.
- Implement WebSocket progress updates for live processing status.
