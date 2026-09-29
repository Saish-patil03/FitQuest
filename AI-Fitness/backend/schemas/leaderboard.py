from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

class LeaderboardBadge(BaseModel):
    id: str
    title: str
    icon: str

class LeaderboardEntry(BaseModel):
    """
    Publicly visible leaderboard entry for an athlete.
    Strictly excludes sensitive health/body metrics (weight, height, BMI, calories, readiness).
    """
    rank: int
    user_id: int
    display_name: str
    avatar_initial: str
    fitquest_score: int
    streak: int
    badges: List[LeaderboardBadge] = []

    model_config = ConfigDict(from_attributes=True)

class CurrentUserLeaderboardStatus(BaseModel):
    """
    Personalized ranking status for the authenticated user.
    """
    rank: Optional[int] = None
    user_id: int
    display_name: str
    avatar_initial: str
    fitquest_score: int
    streak: int
    rank_change: Optional[int] = None
    points_to_next_rank: Optional[int] = None
    is_visible: bool = True
    message: Optional[str] = None

class LeaderboardResponse(BaseModel):
    """
    Top-level payload returned by GET /api/v1/leaderboard.
    """
    period: str
    updated_at: str
    total_athletes: int
    entries: List[LeaderboardEntry]
    current_user: Optional[CurrentUserLeaderboardStatus] = None
