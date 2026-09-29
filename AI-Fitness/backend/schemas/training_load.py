from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class TrainingLoadSupportingMetrics(BaseModel):
    valid_workouts_7d: int = 0
    total_reps_7d: int = 0
    days_since_last_workout: Optional[int] = None
    recent_avg_form: Optional[float] = None
    form_trend: str = "INSUFFICIENT_DATA" # 'IMPROVING', 'STABLE', 'DECLINING', 'INSUFFICIENT_DATA'
    acute_load_7d: float = 0.0
    chronic_load_28d: float = 0.0
    training_load_ratio: float = 0.0

class TrainingLoadResponse(BaseModel):
    acute_load_7d: float = Field(0.0, description="Total 7-day acute workload")
    chronic_load_28d: float = Field(0.0, description="Average weekly workload over 28 days")
    training_load_ratio: float = Field(0.0, description="ATL / max(1.0, CTL)")
    training_load_zone: str = Field(..., description="UNDER_TRAINING, OPTIMAL, HIGH_LOAD, OVER_REACHING, INSUFFICIENT_DATA")
    recovery_score: Optional[int] = Field(None, description="Recovery score 0-100 or null if insufficient data")
    recovery_status: str = Field(..., description="FULLY_RECOVERED, MODERATELY_RECOVERED, PARTIALLY_RECOVERED, FATIGUE_ACCUMULATED, INSUFFICIENT_DATA")
    recommended_action: str = Field(..., description="TRAIN_NORMAL, REDUCE_INTENSITY, REST_OR_RECOVER, TRAIN_MODERATELY, COMPLETE_FIRST_WORKOUT")
    supporting_metrics: TrainingLoadSupportingMetrics
    explanation: str = Field(..., description="Deterministic explanation based on verified workout telemetry")

    model_config = ConfigDict(from_attributes=True)
