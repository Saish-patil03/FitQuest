"""
FitQuest Human Movement Intelligence Engine — Phase 6: BODY SIM™ API
Predictive Human Performance Intelligence & What-If Intervention Simulator Endpoints.
"""

from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.services.body_sim import body_sim_service, INTERVENTION_STRATEGIES

router = APIRouter(prefix="/movement-intelligence/body-sim", tags=["BODY SIM™ (Predictive Movement Intelligence)"])


class SimulateRequest(BaseModel):
    strategy: str = Field(default="TEMPO_FOCUS", description="Intervention strategy key (e.g. TEMPO_FOCUS, STABILITY_FOCUS, ROM_FOCUS, SYMMETRY_FOCUS, CONSISTENCY_FOCUS, BALANCED)")
    horizon: int = Field(default=5, ge=3, le=10, description="Forecast horizon in sessions (3, 5, or 10)")
    exercise_id: Optional[Union[int, str]] = Field(default=None, description="Optional Exercise ID")


class InterventionWorkoutRequest(BaseModel):
    strategy: str = Field(default="TEMPO_FOCUS", description="Chosen What-If intervention strategy")
    target_duration_min: int = Field(default=20, ge=10, le=60, description="Target workout duration in minutes")


@router.get("/forecast", summary="Get User Movement Performance Forecast")
def get_performance_forecast(
    horizon: int = Query(default=5, ge=3, le=10, description="Forecast horizon sessions (3, 5, 10)"),
    exercise_id: Optional[int] = Query(default=None, description="Optional Exercise ID for exercise-specific forecast"),
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns deterministic, explainable performance forecasts projecting Movement DNA score,
    5 biomechanical dimensions, trajectory vectors, future limiter risks, and confidence scores.
    Strictly scoped to the authenticated user.
    """
    try:
        return body_sim_service.get_performance_forecast(
            db=db,
            user_id=auth_user_id,
            horizon=horizon,
            exercise_id=exercise_id
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate performance forecast: {err}"
        )


@router.post("/simulate", summary="Run What-If Intervention Simulation")
def simulate_intervention(
    payload: SimulateRequest,
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Simulates projected athletic trajectory under 6 deterministic training intervention strategies.
    Computes net improvement differentials, limiter resolution timeline, and simulated trajectories.
    """
    try:
        ex_id = int(payload.exercise_id) if payload.exercise_id is not None else None
        return body_sim_service.simulate_intervention(
            db=db,
            user_id=auth_user_id,
            strategy_key=payload.strategy,
            horizon=payload.horizon,
            exercise_id=ex_id
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run What-If intervention simulation: {err}"
        )


@router.post("/intervention-workout", summary="Generate Adaptive Workout from Simulation")
def generate_intervention_workout(
    payload: InterventionWorkoutRequest,
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Bridges BODY SIM™ What-If simulations directly into the Adaptive Training Engine,
    generating a personalized structured workout routine with prescribed sets, reps, and focus cues.
    """
    try:
        return body_sim_service.generate_intervention_workout(
            db=db,
            user_id=auth_user_id,
            strategy_key=payload.strategy,
            target_duration_min=payload.target_duration_min
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate intervention workout: {err}"
        )


@router.get("/strategies", summary="List Available What-If Intervention Strategies")
def list_strategies() -> Dict[str, Any]:
    """
    Returns the catalogue of 6 deterministic What-If intervention strategies with primary/secondary boosts.
    """
    return {
        "strategies": list(INTERVENTION_STRATEGIES.values())
    }
