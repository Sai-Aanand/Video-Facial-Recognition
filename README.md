# Facial Recognition CCTV Processing Suite

Full-stack system for processing CCTV footage with automated face detection, recognition, annotated exports, and PDF reporting. The stack pairs a FastAPI backend (Python) with a React dashboard and persists data in MongoDB. Face detection/recognition uses the open-source [`face_recognition`](https://github.com/ageitgey/face_recognition) library built on top of dlib.

## Features
- Upload CCTV recordings or reference a server-side video path.
- Detect faces in each frame, draw bounding boxes, and annotate the video output.
- Auto-build a roster of seen people (known faces are stored in MongoDB and re-used for future uploads).
- Produce a PDF report summarising identified individuals, appearance counts, timestamps, and bounding boxes.
- React dashboard to trigger processing, inspect summaries, watch live progress, and download deliverables.

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
data/                    # Uploaded/source videos (auto-created)
```

## Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB (local or remote)
- System requirements for `face_recognition` / `dlib`:
  - CMake, Boost, and build tools (macOS: `brew install cmake`, Ubuntu: `sudo apt install build-essential cmake`)
  - `libopenblas-dev` and `liblapack-dev` on Linux for faster numerical routines

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
- `APP_FACE_MATCH_THRESHOLD` – Distance threshold for matching encodings (default `0.45`).

### Processing Workflow
1. Client uploads footage or provides a file path.
2. Video saved under `APP_MEDIA_ROOT` with a unique prefix.
3. `VideoProcessor` iterates through frames, detects faces (`face_recognition.face_locations`) and computes embeddings.
4. Embeddings are matched against MongoDB `people` collection. Unknown faces create new auto-labelled entries (e.g., "Person 3").
5. Bounding boxes and labels are drawn using OpenCV; detections logged to `detections` collection.
6. Progress (frames processed, percent complete) is persisted so the dashboard can poll and render live status updates.
7. Summary and metadata stored in the `videos` collection.
8. A PDF report is produced with ReportLab under `outputs/reports/<video_id>.pdf`.

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
- Detailed per-person cards showing timestamped appearances and bounding boxes.
- Download buttons for annotated video and PDF report.

## Data Model (MongoDB)
- `people`: `{ _id, name, encodings[], metadata, created_at }`
- `videos`: `{ _id, filename, stored_filename, original_path, annotated_path, report_path, status, processing_time_seconds, processing_progress, processed_frames, total_frames, summary, created_at, updated_at }`
- `detections`: `{ video_id, person_id, person_name, timestamp, frame_index, bounding_box[], created_at }`

Known faces added automatically when new individuals appear. To seed identities with real names, insert documents into `people` with `name` and `encodings` captured via the same `face_recognition` API.

## Generating Known Face Encodings (Optional)
```python
import face_recognition
from pathlib import Path

image = face_recognition.load_image_file(Path('known_faces/john_doe.jpg'))
encoding = face_recognition.face_encodings(image)[0]
# Store `encoding.tolist()` inside the `people` collection for person metadata
```

## Testing & Verification
- Run `uvicorn app.main:app --reload` and `npm run dev`; process sample videos to confirm annotated outputs and reports.
- Inspect MongoDB collections to verify new people and detection logs are persisted.
- Generated assets reside under `outputs/videos` and `outputs/reports`.

## Future Enhancements
- Offload video processing to background workers (Celery/RQ) for long-running tasks.
- Add authentication and role-based dashboard access.
- Integrate web-based face enrollment and manual identity corrections.
- Implement WebSocket progress updates for live processing status.
