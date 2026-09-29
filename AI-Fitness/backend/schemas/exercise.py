from typing import Optional
from pydantic import BaseModel, ConfigDict

class ExerciseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    muscle_group: Optional[str] = None
    difficulty: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
