from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.schemas.training_load import TrainingLoadResponse
from backend.services.training_load_service import training_load_service

router = APIRouter(prefix="/training-load", tags=["Recovery & Training Load"])

@router.get("/me", response_model=TrainingLoadResponse, summary="Get Authenticated User Recovery & Training Load Insights")
def get_user_training_load(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Calculates dynamic software-based Acute Training Load (7d), Chronic Training Load (28d), Training Load Ratio (ATL/CTL),
    and Recovery Status (0-100%) for the authenticated user.
    Strictly excludes zero-repetition workouts (repetitions >= 1).
    Enforces user isolation via JWT bearer authentication.
    """
    try:
        return training_load_service.calculate_user_training_load(db=db, user_id=user_id)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate training load and recovery insights: {err}"
        )
