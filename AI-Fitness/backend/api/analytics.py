from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.schemas.analytics import ProgressAnalyticsResponse
from backend.services.analytics_service import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics & Progress"])

@router.get("/progress", response_model=ProgressAnalyticsResponse, summary="Get Authenticated User Progress Analytics & Metrics")
def get_user_progress(
    time_range: Optional[str] = Query("all", description="Time range filter: 7d, 30d, 90d, all"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns aggregated read-only progress analytics for the authenticated user,
    including total workouts, reps, average form, streaks, trends, exercise breakdown,
    personal records, and recent valid workouts.
    Strictly excludes zero-repetition workouts (repetitions >= 1).
    """
    try:
        return analytics_service.get_user_analytics(db=db, user_id=user_id, time_range=time_range or "all")
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate progress analytics: {err}"
        )
