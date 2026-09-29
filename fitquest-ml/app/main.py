import os
import sys
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure app directory is on sys.path for direct module imports
_app_dir = str(Path(__file__).resolve().parent)
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

from cv_service import cv_live_service

# Process-level inference lock preventing overlapping YOLO forward passes
_inference_lock = threading.Lock()

app = FastAPI(
    title="FitQuest ML Engine",
    description="Standalone Computer Vision and Pose Telemetry Service",
    version="1.0.0"
)

# CORS configuration: default local development origins + optional environment origins
_DEFAULT_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8100",
    "https://ai-fitness-i18hx47gt-ai-fitness2.vercel.app",
    "https://ai-fitness2.vercel.app",
    "https://ai-fitness-ai-fitness2.vercel.app",
    "https://ai-fitness-git-migration-multi-service-architecture-ai-fitness2.vercel.app",
]

def _get_allowed_origins() -> List[str]:
    origins = list(_DEFAULT_ORIGINS)
    env_origins = os.getenv("CORS_ORIGINS") or os.getenv("ALLOWED_ORIGINS")
    if env_origins:
        for o in env_origins.split(","):
            cleaned = o.strip()
            if cleaned and cleaned not in origins:
                origins.append(cleaned)
    return origins

# CORS middleware for frontend and backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------
class LiveSessionStartRequest(BaseModel):
    session_id: str
    exercise_choice: str = "1"

class LiveFrameProcessRequest(BaseModel):
    session_id: str = "default_session"
    exercise_choice: str = "1"
    frame_data: str
    include_annotated_image: Optional[bool] = True

class LiveSessionStopRequest(BaseModel):
    session_id: str = "default_session"

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", summary="Service Health Check")
def health_check():
    """
    Lightweight health check endpoint for liveness and readiness monitoring.
    Does not trigger YOLO inference.
    """
    return {
        "status": "ok",
        "service": "FitQuest ML Engine"
    }

@app.post("/live/start-session", summary="Start/Reset Live CV Workout Session")
@app.post("/workouts/live/start-session", summary="Start/Reset Live CV Workout Session (Compatibility Route)")
def start_live_session(payload: LiveSessionStartRequest):
    """
    Explicitly starts a fresh live CV session for session_id, purging any prior session state.
    """
    try:
        controller = cv_live_service.start_session(
            session_id=payload.session_id,
            exercise_choice=payload.exercise_choice
        )
        return {
            "status": "success",
            "session_id": payload.session_id,
            "exercise": controller.tracker.name,
            "rep_count": controller.tracker.rep_count,
            "form_score": controller.tracker.get_form_score()
        }
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to start live session: {err}")

@app.post("/live/process-frame", summary="Process Live Camera Frame with CV Engine")
@app.post("/workouts/live/process-frame", summary="Process Live Camera Frame with CV Engine (Compatibility Route)")
def process_live_frame(payload: LiveFrameProcessRequest):
    """
    HTTP endpoint processing a single base64 camera frame through YOLO Pose Engine.
    Validates exercise_choice and returns real-time telemetry + optional skeleton overlay frame.
    """
    try:
        controller = cv_live_service.get_or_create_session(
            session_id=payload.session_id,
            exercise_choice=payload.exercise_choice
        )
        with _inference_lock:
            telemetry = cv_live_service.process_base64_frame(
                controller=controller,
                base64_str=payload.frame_data,
                include_annotated_image=payload.include_annotated_image,
                session_id=payload.session_id
            )
        return telemetry
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Live frame processing error: {err}")

@app.post("/live/stop-session", summary="Stop Live CV Workout Session")
@app.post("/workouts/live/stop-session", summary="Stop Live CV Workout Session (Compatibility Route)")
def stop_live_session(payload: LiveSessionStopRequest):
    """
    Stops a live CV session and returns final summary telemetry including Movement Intelligence.
    """
    summary, movement_intel = cv_live_service.close_session_with_movement(payload.session_id)
    if not summary:
        return {"status": "info", "message": "No active session found"}
    return {
        "status": "success",
        "exercise": summary.exercise_name,
        "total_reps": summary.rep_count,
        "duration_sec": summary.duration_sec,
        "form_score": summary.form_score,
        "movement_intelligence": movement_intel
    }
