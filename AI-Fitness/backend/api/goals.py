from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.schemas.goal import GoalCreate, GoalUpdate, GoalProgressResponse
from backend.services.goal_service import goal_service

router = APIRouter(prefix="/goals", tags=["Personalized Goals"])

@router.post("", response_model=GoalProgressResponse, status_code=status.HTTP_201_CREATED, summary="Create Personalized Goal")
def create_goal(
    goal_in: GoalCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Creates a personalized fitness target/goal for the authenticated user.
    Enforces user isolation via JWT token.
    """
    new_goal = goal_service.create_goal(db=db, user_id=user_id, goal_in=goal_in)
    return goal_service.calculate_goal_progress(db=db, goal=new_goal)

@router.get("/me", response_model=List[GoalProgressResponse], summary="Get Authenticated User Goals with Live Progress")
def get_user_goals(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns all personalized goals for the authenticated user with dynamically calculated live progress.
    Excludes zero-repetition workouts (repetitions >= 1).
    """
    return goal_service.get_user_goals(db=db, user_id=user_id)

@router.put("/{goal_id}", response_model=GoalProgressResponse, summary="Update Personalized Goal")
def update_goal(
    goal_id: int,
    update_in: GoalUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Updates target value or timeframe for a goal owned by the authenticated user.
    Enforces user isolation.
    """
    return goal_service.update_goal(db=db, goal_id=goal_id, user_id=user_id, update_in=update_in)

@router.delete("/{goal_id}", summary="Delete Personalized Goal")
def delete_goal(
    goal_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Deletes a goal owned by the authenticated user. Does not alter historical workout records.
    Enforces user isolation.
    """
    goal_service.delete_goal(db=db, goal_id=goal_id, user_id=user_id)
    return {"status": "success", "message": f"Goal {goal_id} deleted successfully.", "id": goal_id}
