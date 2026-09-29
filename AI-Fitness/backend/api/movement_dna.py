from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.services.movement_dna import movement_dna_service

router = APIRouter(prefix="/movement-intelligence", tags=["Movement DNA & Movement Intelligence"])


@router.get("/dna", summary="Get User Movement DNA Profile")
def get_user_movement_dna(
    exercise_id: Optional[int] = Query(None, description="Optional Exercise ID for exercise-specific Movement DNA"),
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retrieves the complete Movement DNA™ profile for the authenticated user.
    Includes overall DNA score, 5 biomechanical dimensions (ROM, Stability, Tempo,
    Consistency, Symmetry), baseline vs recent metrics, velocity, directional trends,
    strongest trait, primary/secondary limiters, timeline series, and an explainable AI report.
    Strictly scoped to authenticated user ID.
    """
    try:
        return movement_dna_service.get_user_movement_dna(db, auth_user_id, exercise_id)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Movement DNA profile: {err}"
        )
