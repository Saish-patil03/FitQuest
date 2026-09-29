from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AICoachingLogCreate(BaseModel):
    workout_session_id: int
    response: str
    provider: str  # "Gemini" or "Offline/Rule-Based"

class AICoachingLogResponse(BaseModel):
    id: int
    workout_session_id: int
    response: str
    provider: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
