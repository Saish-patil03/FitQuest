from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.services.adaptive_training import adaptive_training_engine

router = APIRouter(prefix="/adaptive-training", tags=["Adaptive AI Training Engine"])

@router.get("/profile", summary="Get User Derived Adaptive Training Profile")
def get_adaptive_profile(
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns user's longitudinal adaptive training profile, including primary/secondary limiters,
    biomechanical metric classifications (STRONG, ADEQUATE, NEEDS ATTENTION, HIGH PRIORITY),
    adaptation confidence score, and non-clinical summary insights.
    Strictly isolated to authenticated user.
    """
    try:
        return adaptive_training_engine.get_user_adaptive_profile(db, auth_user_id)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to generate adaptive profile: {err}")

@router.get("/recommendations", summary="Get Deterministic Exercise Recommendations")
def get_exercise_recommendations(
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Evaluates the 20-exercise catalogue and returns ranked recommendations targeting
    the user's primary and secondary biomechanical limiters with explainable rationales.
    """
    try:
        return adaptive_training_engine.get_exercise_recommendations(db, auth_user_id)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {err}")

@router.post("/generate", summary="Generate Personalized Adaptive Workout Plan")
def generate_adaptive_workout(
    target_duration_min: int = Query(default=20, ge=10, le=60),
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Generates a personalized multi-exercise workout routine tailored to the user's
    limiting biomechanical dimensions, complete with customized tempos, sets, reps, and focus cues.
    Compatible with FitQuest's structured workout execution orchestrator.
    """
    try:
        return adaptive_training_engine.generate_adaptive_workout(db, auth_user_id, target_duration_min)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to generate adaptive workout: {err}")

@router.get("/latest", summary="Get Latest Adaptive Workout Prescription")
def get_latest_adaptive_workout(
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Retrieves the latest personalized adaptive workout plan for the authenticated user.
    """
    try:
        return adaptive_training_engine.generate_adaptive_workout(db, auth_user_id)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve latest adaptive workout: {err}")

@router.get("/impact", summary="Evaluate Post-Workout Adaptation Impact")
def get_adaptation_impact(
    exercise_id: int = Query(..., description="Exercise ID evaluated"),
    session_id: Optional[int] = Query(None, description="Optional Workout Session ID"),
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Compares the newly completed workout session against historical benchmarks to quantify
    adaptation impact (stability delta, tempo delta, and progress trend).
    """
    try:
        return adaptive_training_engine.get_adaptation_impact(db, auth_user_id, exercise_id, session_id)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to compute adaptation impact: {err}")
