from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class ReadinessSupportingMetrics(BaseModel):
    valid_workouts_last_7_days: int = 0
    valid_workouts_last_14_days: int = 0
    recent_total_reps_last_7_days: int = 0
    recent_average_form: Optional[float] = None
    days_since_last_workout: Optional[int] = None
    form_trend: str = "NEUTRAL" # 'IMPROVING', 'STABLE', 'DECLINING', 'INSUFFICIENT_DATA'
    most_recent_exercise: Optional[str] = None
    least_trained_muscle_group: Optional[str] = None

class ReadinessResponse(BaseModel):
    readiness_score: Optional[int] = Field(None, description="Score 0-100 or null if insufficient data")
    status: str = Field(..., description="READY_TO_TRAIN, GOOD_TO_TRAIN, LIGHT_TRAINING, RECOVERY_RECOMMENDED, INSUFFICIENT_DATA")
    recommended_intensity: Optional[str] = Field(None, description="HIGH, MODERATE_TO_HIGH, MODERATE, LOW, or null")
    recommended_focus: Optional[str] = Field(None, description="LOWER_BODY, UPPER_BODY, CORE, FULL_BODY, RECOVERY_LIGHT_MOVEMENT, or null")
    recommended_exercise_id: Optional[int] = Field(None, description="Recommended exercise ID for Start Workout button")
    recommended_exercise_name: Optional[str] = Field(None, description="Recommended exercise name")
    explanation: str = Field(..., description="Deterministic explanation of readiness and recommendations")
    supporting_metrics: ReadinessSupportingMetrics

    model_config = ConfigDict(from_attributes=True)
