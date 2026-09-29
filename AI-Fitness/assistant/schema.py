from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class WorkoutSessionData:
    """
    Structured data payload representing a completed exercise session.
    Captured from ExerciseController & BaseExerciseTracker.
    """
    exercise_name: str
    rep_count: int
    duration_sec: int
    form_score: float
    form_scores_history: List[int] = field(default_factory=list)
    feedback_events: List[str] = field(default_factory=list)

    @property
    def duration_formatted(self) -> str:
        mins, secs = divmod(self.duration_sec, 60)
        return f"{mins:02d}:{secs:02d}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exercise_name": self.exercise_name,
            "rep_count": self.rep_count,
            "duration_sec": self.duration_sec,
            "duration_formatted": self.duration_formatted,
            "form_score": self.form_score,
            "form_scores_history": self.form_scores_history,
            "feedback_events": self.feedback_events
        }

@dataclass
class UserProfile:
    """
    Structured user profile context for personalizing assistant recommendations.
    """
    user_id: Optional[str] = "guest"
    fitness_goal: str = "General Fitness"  # e.g., "Strength", "Hypertrophy", "Endurance", "Weight Loss"
    experience_level: str = "Intermediate"  # e.g., "Beginner", "Intermediate", "Advanced"
    target_focus: Optional[str] = None
