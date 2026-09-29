from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.schemas.leaderboard import LeaderboardResponse
from backend.services.leaderboard_service import leaderboard_service

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])

@router.get("", response_model=LeaderboardResponse, summary="Get FitQuest Leaderboard Rankings")
@router.get("/", response_model=LeaderboardResponse, include_in_schema=False)
def get_leaderboard(
    period: str = Query("weekly", description="Leaderboard mode: weekly, monthly, or all_time"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Retrieves authenticated FitQuest Leaderboard for the requested period ('weekly', 'monthly', 'all_time').
    Calculates deterministic FitQuest Score based on 5 weighted components:
      - Workout Performance (30%)
      - Consistency / Streak (25%)
      - Form Quality (20%)
      - Improvement (15%)
      - Readiness / Recovery (10%)
    Strictly excludes sensitive user body/health data (weight, height, BMI, calories, readiness details).
    Enforces user isolation and privacy settings.
    """
    clean_period = period.strip().lower()
    if clean_period not in leaderboard_service.ALLOWED_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid leaderboard period '{period}'. Supported periods are: {', '.join(leaderboard_service.ALLOWED_PERIODS)}."
        )

    try:
        return leaderboard_service.get_leaderboard(db=db, current_user_id=user_id, period=clean_period)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve leaderboard: {err}"
        )
