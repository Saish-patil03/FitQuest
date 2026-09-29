import time
from typing import Optional
from utils import calculate_angle, get_body_inclination, AngleSmoother, BaseExerciseTracker
from exercises import (
    ExerciseRegistry,
    PushUpTracker,
    SquatTracker,
    SitUpsTracker as SitUpTracker,
)
from assistant import WorkoutSessionData, UserProfile, AIFitnessAssistant

class ExerciseController:
    """
    Unified Exercise Controller supporting all 20 exercise trackers via ExerciseRegistry
    and integrated with Member 4 AI Fitness Assistant.
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

    def finish_session(self, user_profile: Optional[UserProfile] = None, assistant: Optional[AIFitnessAssistant] = None) -> str:
        """
        Ends the workout session, generates CV summary, and appends AI coaching feedback.
        """
        self.end_time = time.time()
        session_data = self.create_session_data()

        duration_str = session_data.duration_formatted
        form_score = session_data.form_score

        # 1. Base CV Workout Summary (Unchanged existing behavior)
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

        # 2. Addition: AI Assistant Coaching Section
        try:
            ai_coach = assistant or AIFitnessAssistant()
            ai_feedback = ai_coach.generate_workout_feedback(session_data, user_profile)

            summary += f"""
================================================
                  AI COACHING
================================================

{ai_feedback}

================================================
"""
        except Exception as e:
            # Fault-tolerant safety net: never crash if AI generation fails
            summary += f"\n[INFO] AI Coaching feedback unavailable ({e})\n================================================\n"

        return summary

