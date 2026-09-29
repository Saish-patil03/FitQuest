from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

VALID_GOAL_TYPES = {"REPETITION", "FREQUENCY", "FORM_SCORE", "EXERCISE_PR"}
VALID_TIME_FRAMES = {"WEEKLY", "MONTHLY", "ALL_TIME"}

class GoalCreate(BaseModel):
    goal_type: str = Field(..., description="Goal type: REPETITION, FREQUENCY, FORM_SCORE, EXERCISE_PR")
    exercise_id: Optional[int] = Field(None, description="Exercise ID if exercise-specific")
    target_value: float = Field(..., gt=0, description="Numeric target value (must be > 0)")
    time_frame: Optional[str] = Field("WEEKLY", description="Timeframe: WEEKLY, MONTHLY, ALL_TIME")
    end_date: Optional[datetime] = Field(None, description="Optional deadline date")

    @field_validator("goal_type")
    @classmethod
    def validate_goal_type(cls, v: str) -> str:
        v_upper = v.upper().strip()
        if v_upper not in VALID_GOAL_TYPES:
            raise ValueError(f"Invalid goal_type '{v}'. Must be one of: {', '.join(sorted(VALID_GOAL_TYPES))}")
        return v_upper

    @field_validator("time_frame")
    @classmethod
    def validate_time_frame(cls, v: Optional[str]) -> str:
        if not v:
            return "WEEKLY"
        v_upper = v.upper().strip()
        if v_upper not in VALID_TIME_FRAMES:
            raise ValueError(f"Invalid time_frame '{v}'. Must be one of: {', '.join(sorted(VALID_TIME_FRAMES))}")
        return v_upper

class GoalUpdate(BaseModel):
    target_value: Optional[float] = Field(None, gt=0)
    time_frame: Optional[str] = None
    end_date: Optional[datetime] = None

    @field_validator("time_frame")
    @classmethod
    def validate_time_frame(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_upper = v.upper().strip()
        if v_upper not in VALID_TIME_FRAMES:
            raise ValueError(f"Invalid time_frame '{v}'. Must be one of: {', '.join(sorted(VALID_TIME_FRAMES))}")
        return v_upper

class GoalResponse(BaseModel):
    id: int
    user_id: int
    exercise_id: Optional[int] = None
    goal_type: str
    target_value: float
    time_frame: str
    start_date: datetime
    end_date: Optional[datetime] = None
    is_completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class GoalProgressResponse(BaseModel):
    id: int
    user_id: int
    exercise_id: Optional[int] = None
    exercise_name: Optional[str] = None
    goal_type: str
    target_value: float
    current_value: float
    progress_percentage: float
    time_frame: str
    start_date: datetime
    end_date: Optional[datetime] = None
    is_completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime
    days_remaining: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
