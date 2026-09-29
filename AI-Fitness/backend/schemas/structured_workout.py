from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class PlanExerciseResponse(BaseModel):
    id: int
    exercise_id: int
    exercise_name: str
    order_index: int
    target_sets: int
    target_reps: int
    target_duration_sec: int
    rest_duration_sec: int

    model_config = ConfigDict(from_attributes=True)

class StructuredWorkoutPlanResponse(BaseModel):
    id: int
    title: str
    category: str
    description: Optional[str] = None
    difficulty: str
    estimated_duration_min: int
    exercises: List[PlanExerciseResponse]

    model_config = ConfigDict(from_attributes=True)

class StructuredWorkoutStartRequest(BaseModel):
    user_id: Optional[int] = None
    plan_id: Optional[int] = None
    title: Optional[str] = None
    category: Optional[str] = "Full Body"
    custom_exercises: Optional[List[dict]] = None # [{exercise_id: 1, target_sets: 3, target_reps: 12}]

class StructuredWorkoutSetLogRequest(BaseModel):
    structured_session_id: int
    exercise_id: int
    set_number: int
    target_reps: int
    actual_reps: int
    duration_sec: int
    form_score: float
    form_scores_history: Optional[List[int]] = None
    feedback_events: Optional[List[str]] = None

class StructuredWorkoutSetResponse(BaseModel):
    id: int
    structured_session_id: int
    workout_session_id: Optional[int] = None
    exercise_id: int
    exercise_name: str
    set_number: int
    target_reps: int
    actual_reps: int
    duration_sec: int
    form_score: float
    status: str

    model_config = ConfigDict(from_attributes=True)

class StructuredWorkoutSummaryResponse(BaseModel):
    id: int
    user_id: int
    plan_title: str
    category: str
    status: str
    total_exercises: int
    total_sets: int
    completed_sets: int
    total_target_reps: int
    total_actual_reps: int
    average_form_score: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    sets: List[StructuredWorkoutSetResponse] = []

    model_config = ConfigDict(from_attributes=True)
