"""
FitQuest Human Movement Intelligence Engine — Phase 5: MOVEMENT COPILOT™ API
Lightweight real-time endpoint for session telemetry ingestion, degradation alerts, and recovery confirmation.
"""

from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.services.movement_copilot import movement_copilot_engine


router = APIRouter(prefix="/movement-intelligence/copilot", tags=["Movement Copilot™"])


class CopilotFrameRequest(BaseModel):
    session_id: str = Field(..., description="Active workout session ID")
    exercise_id: Union[int, str] = Field(..., description="Exercise ID (1-20)")
    rep_count: int = Field(default=0, ge=0, description="Current repetition count")
    form_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Current form score (0-100)")
    state: Optional[str] = Field(default="START", description="Exercise tracker kinematic state")
    primary_angle: Optional[float] = Field(default=None, description="Primary joint angle (degrees)")
    left_angle: Optional[float] = Field(default=None, description="Left joint angle (degrees)")
    right_angle: Optional[float] = Field(default=None, description="Right joint angle (degrees)")
    torso_angle: Optional[float] = Field(default=None, description="Torso inclination angle (degrees)")
    valid: bool = Field(default=True, description="Landmarks validity flag")
    feedback_code: Optional[str] = Field(default="GOOD_FORM", description="Tracker feedback code")
    dna_primary_limiter: Optional[str] = Field(default=None, description="Phase 4 Movement DNA primary limiter")
    adaptive_tempo_target: Optional[str] = Field(default=None, description="Phase 3 Adaptive Training tempo target (e.g. '3-1-2')")


class CopilotResetRequest(BaseModel):
    session_id: str = Field(..., description="Workout session ID to reset")
    exercise_id: Optional[Union[int, str]] = Field(default=None, description="New exercise ID if switching")


@router.post("/frame", summary="Process Live Movement Telemetry with Movement Copilot™")
def process_copilot_frame(
    payload: CopilotFrameRequest,
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Real-time endpoint evaluating rolling movement telemetry.
    Detects biomechanical degradation, context-aware coaching cues, and closed-loop recovery.
    """
    try:
        result = movement_copilot_engine.process_frame_telemetry(
            session_id=payload.session_id,
            user_id=current_user_id,
            exercise_id=str(payload.exercise_id),
            rep_count=payload.rep_count,
            form_score=payload.form_score,
            state=payload.state or "START",
            primary_angle=payload.primary_angle,
            left_angle=payload.left_angle,
            right_angle=payload.right_angle,
            torso_angle=payload.torso_angle,
            valid=payload.valid,
            feedback_code=payload.feedback_code or "GOOD_FORM",
            dna_primary_limiter=payload.dna_primary_limiter,
            adaptive_tempo_target=payload.adaptive_tempo_target
        )
        return result
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Copilot processing error: {e}")


@router.post("/reset", summary="Reset Copilot State for Session / Exercise Transition")
def reset_copilot_session(
    payload: CopilotResetRequest,
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Resets Copilot rolling window and active state on exercise change.
    """
    try:
        success = movement_copilot_engine.reset_session(
            session_id=payload.session_id,
            user_id=current_user_id,
            new_exercise_id=str(payload.exercise_id) if payload.exercise_id else None
        )
        return {"status": "success", "reset": success, "session_id": payload.session_id}
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/summary/{session_id}", summary="Get Post-Workout Movement Copilot Session Intelligence")
def get_copilot_summary(
    session_id: str,
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Fetches the final Copilot session intelligence summary for the completed workout.
    """
    try:
        summary = movement_copilot_engine.get_session_summary(
            session_id=session_id,
            user_id=current_user_id
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
