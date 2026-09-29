from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.exercise import ExerciseResponse
from backend.services.workout_service import workout_service

router = APIRouter(prefix="/exercises", tags=["Exercises"])

@router.get("", response_model=List[ExerciseResponse], summary="List all 20 Exercise Catalogue items")
@router.get("/", response_model=List[ExerciseResponse], summary="List all 20 Exercise Catalogue items")
def list_exercises(db: Session = Depends(get_db)):
    """
    Returns the list of all 20 seeded exercise trackers from Member 3 ExerciseRegistry.
    """
    return workout_service.get_exercises(db)

@router.get("/{exercise_id}", response_model=ExerciseResponse, summary="Get Exercise details by ID")
def get_exercise(exercise_id: int, db: Session = Depends(get_db)):
    """
    Retrieves exercise information by ID.
    """
    exercise = workout_service.get_exercise(db, exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail=f"Exercise with ID {exercise_id} not found.")
    return exercise
