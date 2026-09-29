from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class StreakResponse(BaseModel):
    """
    Pydantic schema for returning current user's workout streak & activity metrics.
    """
    current_streak: int
    longest_streak: int
    total_workout_days: int
    total_valid_workouts: int
    today_completed: bool
    active_dates: List[str]  # ISO date strings: YYYY-MM-DD

class AchievementResponse(BaseModel):
    """
    Pydantic schema for returning achievement status & progress details.
    """
    id: str
    title: str
    description: str
    icon: str
    earned: bool
    earned_at: Optional[datetime] = None
    progress: int
    target: int

    model_config = ConfigDict(from_attributes=True)
