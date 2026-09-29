from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class OverviewStats(BaseModel):
    total_valid_workouts: int
    total_repetitions: int
    average_form_score: float
    current_streak: int
    longest_streak: int
    best_form_score: float
    highest_repetition_count: int

class ProgressTrendPoint(BaseModel):
    date: str
    total_reps: int
    avg_form_score: float
    workout_count: int

class ExercisePerformance(BaseModel):
    exercise_id: int
    exercise_name: str
    muscle_group: Optional[str] = None
    workout_count: int
    total_reps: int
    average_form_score: float
    best_rep_count: int

class PersonalRecord(BaseModel):
    exercise_id: int
    exercise_name: str
    max_reps: int
    best_form_score: float
    achieved_at: Optional[datetime] = None

class RecentWorkoutItem(BaseModel):
    id: int
    exercise_name: str
    repetitions: int
    duration_sec: int
    form_score: float
    started_at: datetime

class ProgressAnalyticsResponse(BaseModel):
    overview: OverviewStats
    progress_trends: List[ProgressTrendPoint]
    exercise_performance: List[ExercisePerformance]
    personal_records: List[PersonalRecord]
    recent_activity: List[RecentWorkoutItem]
