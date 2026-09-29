from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.models.structured_workout import StructuredWorkoutSessionModel
from backend.schemas.structured_workout import (
    StructuredWorkoutPlanResponse,
    StructuredWorkoutStartRequest,
    StructuredWorkoutSetLogRequest,
    StructuredWorkoutSetResponse,
    StructuredWorkoutSummaryResponse,
)
from backend.services.structured_workout_service import structured_workout_service

router = APIRouter(prefix="/structured-workouts", tags=["Structured Workouts"])

@router.get("/templates", summary="List Preset Structured Workout Plans")
def list_workout_templates(db: Session = Depends(get_db)):
    """
    Returns preset structured multi-exercise workout routines (Full Body, Upper Body, Lower Body, Core, Cardio).
    """
    return structured_workout_service.list_preset_plans(db)

@router.post("/start", response_model=StructuredWorkoutSummaryResponse, status_code=status.HTTP_201_CREATED, summary="Start New Structured Workout Session")
def start_structured_workout(
    payload: StructuredWorkoutStartRequest,
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Initializes a new structured workout session for the authenticated user.
    """
    try:
        session = structured_workout_service.start_structured_workout(
            db=db,
            user_id=auth_user_id,
            plan_id=payload.plan_id,
            title=payload.title,
            category=payload.category,
            custom_exercises=payload.custom_exercises
        )
        return session
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to start structured workout: {err}")

@router.post("/log-set", response_model=StructuredWorkoutSetResponse, status_code=status.HTTP_201_CREATED, summary="Log Set Result in Structured Workout")
def log_workout_set(
    payload: StructuredWorkoutSetLogRequest,
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Logs set telemetry for a structured workout, creating standard WorkoutSessionModel entry for 100% analytics integration.
    Enforces authorization: verifying the structured workout session belongs to authenticated user.
    """
    struct_sess = db.query(StructuredWorkoutSessionModel).filter(StructuredWorkoutSessionModel.id == payload.structured_session_id).first()
    if not struct_sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Structured workout session {payload.structured_session_id} not found.")
    if struct_sess.user_id != auth_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Cannot log sets for another user's session.")

    try:
        set_record = structured_workout_service.log_set_result(
            db=db,
            structured_session_id=payload.structured_session_id,
            exercise_id=payload.exercise_id,
            set_number=payload.set_number,
            target_reps=payload.target_reps,
            actual_reps=payload.actual_reps,
            duration_sec=payload.duration_sec,
            form_score=payload.form_score,
            form_scores_history=payload.form_scores_history,
            feedback_events=payload.feedback_events
        )
        return set_record
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to log workout set: {err}")

@router.post("/complete/{session_id}", response_model=StructuredWorkoutSummaryResponse, summary="Complete Structured Workout Session")
def complete_structured_workout(
    session_id: int,
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Finalizes structured workout session and returns combined summary telemetry.
    Enforces authorization: verifying the session belongs to authenticated user.
    """
    struct_sess = db.query(StructuredWorkoutSessionModel).filter(StructuredWorkoutSessionModel.id == session_id).first()
    if not struct_sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Structured workout session {session_id} not found.")
    if struct_sess.user_id != auth_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Cannot modify another user's workout session.")

    try:
        session = structured_workout_service.complete_structured_workout(db, session_id)
        return session
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to complete structured workout: {err}")

@router.get("/summary/{session_id}", response_model=StructuredWorkoutSummaryResponse, summary="Get Structured Workout Summary")
def get_structured_summary(
    session_id: int,
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Retrieves full structured workout summary.
    Enforces authorization: verifying the session belongs to authenticated user.
    """
    summary = structured_workout_service.get_structured_session_summary(db, session_id)
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Structured workout session {session_id} not found.")
    if summary.user_id != auth_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Cannot view another user's workout session summary.")
    return summary

@router.get("/user/{user_id}", response_model=List[StructuredWorkoutSummaryResponse], summary="Get User Structured Workout History")
def get_user_structured_history(
    user_id: int,
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Retrieves historical structured workouts for a given user.
    Enforces authorization: verifying requested user_id matches authenticated user.
    """
    if auth_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Cannot view another user's workout history.")
    return structured_workout_service.get_user_structured_history(db, user_id)

