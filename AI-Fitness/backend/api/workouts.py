import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.workout import WorkoutSessionCreate, WorkoutSessionResponse
from backend.services.workout_service import workout_service
from backend.services.cv_service import cv_live_service
from backend.services.movement_fingerprint_service import movement_fingerprint_service
from backend.services.movement_intelligence import MovementAnalyzer, FrameTelemetrySample

from backend.api.auth import get_current_user_id

router = APIRouter(prefix="/workouts", tags=["Workouts"])

class WorkoutSessionIngestRequest(BaseModel):
    session_data: WorkoutSessionCreate
    form_scores_history: Optional[List[int]] = None
    feedback_events: Optional[List[str]] = None
    movement_intelligence: Optional[Dict[str, Any]] = None

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

@router.post("/live/start-session", summary="Explicitly Start/Reset Live CV Workout Session")
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

@router.post("", response_model=WorkoutSessionResponse, status_code=status.HTTP_201_CREATED, summary="Ingest Workout Session & Generate AI Coaching")
@router.post("/", response_model=WorkoutSessionResponse, status_code=status.HTTP_201_CREATED, summary="Ingest Workout Session & Generate AI Coaching")
def ingest_workout_session(
    payload: WorkoutSessionIngestRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Receives completed CV workout telemetry payload, persists workout session & form logs,
    triggers Member 4 AI Fitness Assistant, stores AI coaching log, and returns full details.
    Enforces authentication and overrides client user_id with authenticated user_id.
    Automatically persists Movement Fingerprint to database.
    """
    try:
        payload.session_data.user_id = user_id
        session = workout_service.create_workout_session(
            db=db,
            session_in=payload.session_data,
            form_scores_history=payload.form_scores_history,
            feedback_events=payload.feedback_events
        )

        # Automatic Movement Fingerprint Persistence (Phase 2)
        try:
            m_intel = payload.movement_intelligence
            if not m_intel and session.repetitions > 0:
                m_intel = MovementAnalyzer.analyze_session(
                    exercise_id=str(session.exercise_id),
                    exercise_name=session.exercise.name if session.exercise else "Exercise",
                    rep_count=session.repetitions,
                    duration_sec=session.duration_sec,
                    form_score=session.form_score
                )
            if m_intel:
                movement_fingerprint_service.save_fingerprint(
                    db=db,
                    user_id=user_id,
                    exercise_id=session.exercise_id,
                    exercise_name=session.exercise.name if session.exercise else "Exercise",
                    movement_intelligence=m_intel,
                    workout_session_id=session.id,
                    form_score=session.form_score,
                    repetition_count=session.repetitions,
                    session_duration=session.duration_sec
                )
        except Exception as fp_err:
            # Safe non-fatal logging so workout ingestion never fails due to telemetry persistence
            print(f"[FitQuest Warning]: Non-fatal movement fingerprint persistence error: {fp_err}")

        return session
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to ingest workout session: {err}")


class MovementTelemetryIngestRequest(BaseModel):
    exercise_id: Any = "1"
    exercise_name: Optional[str] = "Exercise"
    rep_count: int = 0
    duration_sec: int = 0
    form_score: float = 100.0
    rep_durations: Optional[List[float]] = None
    rep_rom_deltas: Optional[List[float]] = None
    angles: Optional[List[float]] = None
    left_angles: Optional[List[float]] = None
    right_angles: Optional[List[float]] = None
    torso_angles: Optional[List[float]] = None

@router.post("/live/process-frame", summary="Process Live Camera Frame with CV Engine")
def process_live_frame(payload: LiveFrameProcessRequest):
    """
    HTTP endpoint processing a single base64 camera frame through Member 3 YOLO Pose Engine.
    Validates exercise_choice and returns real-time telemetry + optional skeleton overlay frame.
    """
    try:
        controller = cv_live_service.get_or_create_session(
            session_id=payload.session_id,
            exercise_choice=payload.exercise_choice
        )
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

@router.post("/live/stop-session", summary="Stop Live CV Workout Session")
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

@router.post("/movement-intelligence/analyze", summary="Analyze Telemetry & Generate Movement Fingerprint")
def analyze_movement_telemetry(payload: MovementTelemetryIngestRequest):
    """
    Direct endpoint for analyzing workout movement telemetry and computing
    Movement Fingerprints, Movement Signatures, and Biomechanical Movement Profiles.
    """
    try:
        samples = []
        angles = payload.angles or []
        left_angles = payload.left_angles or []
        right_angles = payload.right_angles or []
        torso_angles = payload.torso_angles or []

        num_samples = max(len(angles), len(left_angles), len(right_angles), len(torso_angles), 0)
        for i in range(num_samples):
            primary_a = angles[i] if i < len(angles) else None
            left_a = left_angles[i] if i < len(left_angles) else None
            right_a = right_angles[i] if i < len(right_angles) else None
            torso_a = torso_angles[i] if i < len(torso_angles) else None

            sample = FrameTelemetrySample(
                timestamp=float(i * 0.12),
                primary_angle=primary_a,
                left_angle=left_a,
                right_angle=right_a,
                torso_angle=torso_a,
                rep_count=payload.rep_count,
                valid=True
            )
            samples.append(sample)

        analysis = MovementAnalyzer.analyze_session(
            exercise_id=payload.exercise_id,
            exercise_name=payload.exercise_name or "Exercise",
            rep_count=payload.rep_count,
            duration_sec=payload.duration_sec,
            form_score=payload.form_score,
            samples=samples if samples else None
        )
        return {
            "status": "success",
            "movement_intelligence": analysis
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Movement analysis failed: {err}")

@router.get("/movement-intelligence/history", summary="Get Authenticated User Movement Fingerprint History")
def get_movement_fingerprint_history(
    exercise_id: Optional[int] = None,
    limit: int = 50,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns the authenticated user's historical movement fingerprints.
    Guarantees strict multi-user data isolation.
    """
    fingerprints = movement_fingerprint_service.get_user_fingerprints(
        db=db,
        user_id=user_id,
        exercise_id=exercise_id,
        limit=limit
    )
    return {
        "items": [
            {
                "id": fp.id,
                "workout_session_id": fp.workout_session_id,
                "exercise_id": fp.exercise_id,
                "exercise_name": fp.exercise_name,
                "range_of_motion": fp.range_of_motion,
                "movement_stability": fp.movement_stability,
                "tempo_control": fp.tempo_control,
                "repetition_consistency": fp.repetition_consistency,
                "bilateral_symmetry": fp.bilateral_symmetry,
                "overall_movement_quality": fp.overall_movement_quality,
                "form_score": fp.form_score,
                "repetition_count": fp.repetition_count,
                "session_duration": fp.session_duration,
                "created_at": fp.created_at.isoformat() if fp.created_at else None
            }
            for fp in fingerprints
        ]
    }

@router.get("/movement-intelligence/evolution", summary="Get Longitudinal Movement Evolution & Trends")
def get_movement_evolution(
    exercise_id: Optional[int] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns longitudinal movement evolution comparing baseline vs latest performance,
    metric-by-metric change percentages, trend classifications, and explainable AI insights.
    Guarantees strict multi-user data isolation.
    """
    return movement_fingerprint_service.calculate_evolution(
        db=db,
        user_id=user_id,
        exercise_id=exercise_id
    )

@router.get("/movement-intelligence/comparison", summary="Compare Workout Session With Historical Average")
def get_movement_session_comparison(
    exercise_id: int,
    quality_score: float = 85.0,
    session_id: Optional[int] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Compares current session movement quality score with historical average for that exercise.
    Guarantees strict multi-user data isolation.
    """
    return movement_fingerprint_service.get_session_comparison(
        db=db,
        user_id=user_id,
        exercise_id=exercise_id,
        current_quality_score=quality_score,
        current_session_id=session_id
    )


@router.websocket("/live-ws/{exercise_choice}")
async def live_workout_websocket(websocket: WebSocket, exercise_choice: str):
    """
    WebSocket endpoint for real-time live webcam frame streaming and telemetry.
    """
    await websocket.accept()
    session_id = f"ws_session_{id(websocket)}"

    try:
        controller = cv_live_service.get_or_create_session(
            session_id=session_id,
            exercise_choice=exercise_choice
        )
    except ValueError as err:
        await websocket.send_json({"status": "error", "message": str(err)})
        await websocket.close(code=1008)
        return

    try:
        while True:
            data = await websocket.receive_text()
            if not data:
                continue

            # Handle incoming frame payload
            frame_data = data
            if data.startswith("{"):
                try:
                    parsed = json.loads(data)
                    frame_data = parsed.get("frame_data", "")
                except json.JSONDecodeError:
                    pass

            if not frame_data:
                continue

            telemetry = cv_live_service.process_base64_frame(
                controller=controller,
                base64_str=frame_data,
                include_annotated_image=True
            )
            await websocket.send_json(telemetry)

    except WebSocketDisconnect:
        print(f"[INFO] WebSocket disconnected for session {session_id}")
    finally:
        cv_live_service.close_session(session_id)

@router.get("/{session_id}", response_model=WorkoutSessionResponse, summary="Get Workout Session details by ID")
def get_workout_session(
    session_id: int,
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Retrieves full workout session details including form logs and AI coaching history.
    Enforces authorization: users can only view their own workout sessions.
    """
    session = workout_service.get_workout_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workout session with ID {session_id} not found.")
    if session.user_id != auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Cannot access another user's workout session."
        )
    return session

@router.get("/user/{user_id}", response_model=List[WorkoutSessionResponse], summary="Get Workout History for a User")
def get_user_workouts(
    user_id: int,
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Retrieves historical workout sessions for a given user.
    Enforces authorization: users can only view their own workout history.
    """
    if auth_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Cannot access another user's workout history."
        )
    return workout_service.get_user_workouts(db, user_id)

