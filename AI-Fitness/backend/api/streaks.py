from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.schemas.achievement import StreakResponse
from backend.services.gamification_service import gamification_service

router = APIRouter(prefix="/streaks", tags=["Gamification & Streaks"])

@router.get("/me", response_model=StreakResponse, summary="Get Authenticated User Workout Streak & Calendar Metrics")
def get_my_streak(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns current streak, longest streak, total active workout days, total valid workouts,
    today completion status, and active date array for the authenticated user.
    """
    try:
        return gamification_service.get_user_streak(db, user_id)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate streak metrics: {err}"
        )
