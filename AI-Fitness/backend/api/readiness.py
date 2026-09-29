from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.schemas.readiness import ReadinessResponse
from backend.services.readiness_service import readiness_service

router = APIRouter(prefix="/readiness", tags=["Training Readiness"])

@router.get("/me", response_model=ReadinessResponse, summary="Get Authenticated User Training Readiness & Daily Recommendation")
def get_user_readiness(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Calculates dynamic deterministic FitQuest Training Readiness Score (0-100) and daily training recommendation.
    Evaluates recent valid workout load (repetitions >= 1), form trends, rest gap, and muscle group balance.
    Returns INSUFFICIENT_DATA status if the user has 0 valid completed workouts.
    Enforces strict user isolation via JWT authentication token.
    """
    try:
        return readiness_service.calculate_user_readiness(db=db, user_id=user_id)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate training readiness: {err}"
        )
