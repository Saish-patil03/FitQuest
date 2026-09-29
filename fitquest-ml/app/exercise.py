import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from utils import calculate_angle, get_body_inclination, AngleSmoother, BaseExerciseTracker
from exercises import (
    ExerciseRegistry,
    PushUpTracker,
    SquatTracker,
    SitUpsTracker as SitUpTracker,
)

@dataclass
class WorkoutSessionData:
    """
    Structured data payload representing a completed exercise session.
    Captured from ExerciseController & BaseExerciseTracker.
    Decoupled from AI Assistant.
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

class ExerciseController:
    """
    Unified Exercise Controller supporting all 20 exercise trackers via ExerciseRegistry.
    Decoupled standalone service edition.
    """
    def __init__(self, exercise_choice="1"):
        self.exercise_key = str(exercise_choice).strip()
        self.tracker = ExerciseRegistry.get_tracker(exercise_choice)
        self.start_time = time.time()
        self.end_time = None

    def process(self, keypoints):
        return self.tracker.process(keypoints)

    def create_session_data(self) -> WorkoutSessionData:
        """
        Extracts actual CV tracking metrics into a WorkoutSessionData payload.
        """
        end = self.end_time if self.end_time is not None else time.time()
        duration_sec = int(end - self.start_time)
        form_score = self.tracker.get_form_score()
        feedback_events = getattr(self.tracker, "feedback_events", [])

        return WorkoutSessionData(
            exercise_name=self.tracker.name,
            rep_count=self.tracker.rep_count,
            duration_sec=duration_sec,
            form_score=form_score,
            form_scores_history=list(self.tracker.form_scores),
            feedback_events=list(feedback_events)
        )

    def finish_session(self) -> str:
        """
        Ends the workout session and generates the CV workout summary.
        """
        self.end_time = time.time()
        session_data = self.create_session_data()

        duration_str = session_data.duration_formatted
        form_score = session_data.form_score

        summary = f"""
================================================
                WORKOUT SUMMARY
================================================

Exercise:       {self.tracker.name}

Repetitions:    {self.tracker.rep_count}
Duration:       {duration_str}

Form Score:     {form_score}%

Feedback Summary:
- Live joint tracking completed
- Modular exercise evaluation recorded cleanly
"""
        return summary
