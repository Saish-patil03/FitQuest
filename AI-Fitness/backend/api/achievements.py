from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.schemas.achievement import AchievementResponse
from backend.services.gamification_service import gamification_service

router = APIRouter(prefix="/achievements", tags=["Gamification & Achievements"])

@router.get("/me", response_model=List[AchievementResponse], summary="Get Authenticated User Fitness Achievements & Badges")
def get_my_achievements(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns the master catalogue of 8 achievements with current user's earned status,
    earned_at timestamp, progress, and target requirements.
    """
    try:
        return gamification_service.get_user_achievements(db, user_id)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch achievements: {err}"
        )
