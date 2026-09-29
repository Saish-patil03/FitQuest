# FitQuest Computer Vision / ML Standalone Service

Independent microservice providing real-time pose tracking, joint angle calculation, repetition counting, form scoring, and movement intelligence for FitQuest workouts.

## Architecture

- **Engine:** YOLOv8 Pose (`ultralytics`) + OpenCV
- **Framework:** FastAPI + Uvicorn
- **Supported Trackers:** 20 modular exercise trackers
- **Data Footprint:** In-memory session tracking, zero database dependencies, zero AI assistant dependencies

## Directory Structure

```
fitquest-ml/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI service entrypoint
│   ├── cv_service.py            # CV live session & telemetry service
│   ├── pose.py                  # YOLO pose detector & HUD renderer
│   ├── exercise.py              # ExerciseController & session data
│   ├── movement_intelligence.py # Biomechanical metrics & fingerprint buffer
│   ├── exercises/               # 20 modular exercise trackers
│   └── utils/                   # Angles, smoothing, counters, keypoint validation
├── models/
│   ├── pose_model.pt            # Pretrained YOLOv8 pose weights
│   └── yolov8n-pose.pt          # Fallback weights
├── requirements-ml.txt
└── README.md
```

## Running Locally

```bash
cd fitquest-ml
uvicorn app.main:app --host 127.0.0.1 --port 8100
```

## Endpoints

- `GET /health` - Lightweight health check
- `POST /live/start-session` - Start fresh session for exercise
- `POST /live/process-frame` - Process base64 JPEG webcam frame
- `POST /live/stop-session` - Complete workout session & return movement intelligence
