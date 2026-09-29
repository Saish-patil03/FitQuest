from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

class FormLogCreate(BaseModel):
    form_score: Optional[float] = None
    feedback: Optional[str] = None

class FormLogResponse(BaseModel):
    id: int
    workout_session_id: int
    form_score: Optional[float] = None
    feedback: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkoutSessionCreate(BaseModel):
    user_id: Optional[int] = None
    exercise_id: int
    repetitions: int = Field(default=0, ge=0)
    duration_sec: int = Field(default=0, ge=0)
    form_score: float = Field(default=100.0, ge=0.0, le=100.0)
    completed_at: Optional[datetime] = None

from backend.schemas.exercise import ExerciseResponse
from backend.schemas.coaching import AICoachingLogResponse

class WorkoutSessionResponse(BaseModel):
    id: int
    user_id: int
    exercise_id: int
    repetitions: int
    duration_sec: int
    form_score: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    exercise: Optional[ExerciseResponse] = None
    form_logs: List[FormLogResponse] = []
    ai_coaching_logs: List[AICoachingLogResponse] = []

    model_config = ConfigDict(from_attributes=True)
