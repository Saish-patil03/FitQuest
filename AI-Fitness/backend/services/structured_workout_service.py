from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.models.exercise import ExerciseModel
from backend.models.workout import WorkoutSessionModel
from backend.models.structured_workout import (
    StructuredWorkoutPlanModel,
    StructuredWorkoutPlanExerciseModel,
    StructuredWorkoutSessionModel,
    StructuredWorkoutSetModel,
)
from backend.schemas.workout import WorkoutSessionCreate
from backend.services.workout_service import workout_service

PRESET_WORKOUT_PLANS = [
    {
        "id": 1,
        "title": "Full Body Foundation",
        "category": "Full Body",
        "description": "Comprehensive full body workout targeting major muscle groups with compound movements.",
        "difficulty": "Intermediate",
        "estimated_duration_min": 25,
        "exercises": [
            {"exercise_id": 3, "exercise_name": "Push-up", "order_index": 1, "target_sets": 3, "target_reps": 12, "rest_duration_sec": 30},
            {"exercise_id": 2, "exercise_name": "Squat", "order_index": 2, "target_sets": 3, "target_reps": 15, "rest_duration_sec": 30},
            {"exercise_id": 4, "exercise_name": "Lunges", "order_index": 3, "target_sets": 3, "target_reps": 10, "rest_duration_sec": 30},
            {"exercise_id": 12, "exercise_name": "Crunches", "order_index": 4, "target_sets": 3, "target_reps": 15, "rest_duration_sec": 30},
        ]
    },
    {
        "id": 2,
        "title": "Upper Body Power",
        "category": "Upper Body",
        "description": "Upper body push & pull sequence building chest, shoulders, biceps, and triceps.",
        "difficulty": "Intermediate",
        "estimated_duration_min": 20,
        "exercises": [
            {"exercise_id": 3, "exercise_name": "Push-up", "order_index": 1, "target_sets": 3, "target_reps": 12, "rest_duration_sec": 30},
            {"exercise_id": 5, "exercise_name": "Shoulder Press", "order_index": 2, "target_sets": 3, "target_reps": 10, "rest_duration_sec": 30},
            {"exercise_id": 1, "exercise_name": "Bicep Curl", "order_index": 3, "target_sets": 3, "target_reps": 12, "rest_duration_sec": 30},
            {"exercise_id": 20, "exercise_name": "Tricep Extensions", "order_index": 4, "target_sets": 3, "target_reps": 12, "rest_duration_sec": 30},
        ]
    },
    {
        "id": 3,
        "title": "Lower Body Strength",
        "category": "Lower Body",
        "description": "Legs & glutes developer focusing on squats, lunges, bridges, and calf raises.",
        "difficulty": "Intermediate",
        "estimated_duration_min": 22,
        "exercises": [
            {"exercise_id": 2, "exercise_name": "Squat", "order_index": 1, "target_sets": 4, "target_reps": 15, "rest_duration_sec": 30},
            {"exercise_id": 4, "exercise_name": "Lunges", "order_index": 2, "target_sets": 3, "target_reps": 12, "rest_duration_sec": 30},
            {"exercise_id": 10, "exercise_name": "Glute Bridge", "order_index": 3, "target_sets": 3, "target_reps": 15, "rest_duration_sec": 30},
            {"exercise_id": 17, "exercise_name": "Calf Raises", "order_index": 4, "target_sets": 3, "target_reps": 20, "rest_duration_sec": 30},
        ]
    },
    {
        "id": 4,
        "title": "Core & Abs Sculptor",
        "category": "Core",
        "description": "Targeted abdominal circuit strengthening upper abs, lower abs, and obliques.",
        "difficulty": "Intermediate",
        "estimated_duration_min": 18,
        "exercises": [
            {"exercise_id": 11, "exercise_name": "Sit-ups", "order_index": 1, "target_sets": 3, "target_reps": 15, "rest_duration_sec": 30},
            {"exercise_id": 12, "exercise_name": "Crunches", "order_index": 2, "target_sets": 3, "target_reps": 20, "rest_duration_sec": 30},
            {"exercise_id": 13, "exercise_name": "Leg Raises", "order_index": 3, "target_sets": 3, "target_reps": 12, "rest_duration_sec": 30},
            {"exercise_id": 14, "exercise_name": "Russian Twists", "order_index": 4, "target_sets": 3, "target_reps": 16, "rest_duration_sec": 30},
        ]
    },
    {
        "id": 5,
        "title": "Fat Loss & Cardio Burn",
        "category": "Cardio",
        "description": "High-intensity calorie-burning conditioning routine combining explosive full body movements.",
        "difficulty": "Advanced",
        "estimated_duration_min": 20,
        "exercises": [
            {"exercise_id": 6, "exercise_name": "Jumping Jacks", "order_index": 1, "target_sets": 3, "target_reps": 30, "rest_duration_sec": 30},
            {"exercise_id": 7, "exercise_name": "High Knees", "order_index": 2, "target_sets": 3, "target_reps": 25, "rest_duration_sec": 30},
            {"exercise_id": 8, "exercise_name": "Mountain Climbers", "order_index": 3, "target_sets": 3, "target_reps": 20, "rest_duration_sec": 30},
            {"exercise_id": 2, "exercise_name": "Squat", "order_index": 4, "target_sets": 3, "target_reps": 15, "rest_duration_sec": 30},
        ]
    }
]

class StructuredWorkoutService:
    def list_preset_plans(self, db: Session) -> List[Dict[str, Any]]:
        """
        Returns list of preset structured workout plans with verified exercise names.
        """
        ex_map = {ex.id: ex.name for ex in db.query(ExerciseModel).all()}
        plans = []
        for p in PRESET_WORKOUT_PLANS:
            plan_copy = dict(p)
            ex_list = []
            for ex in p["exercises"]:
                ex_copy = dict(ex)
                if ex_copy["exercise_id"] in ex_map:
                    ex_copy["exercise_name"] = ex_map[ex_copy["exercise_id"]]
                ex_list.append(ex_copy)
            plan_copy["exercises"] = ex_list
            plans.append(plan_copy)
        return plans

    def start_structured_workout(
        self,
        db: Session,
        user_id: int,
        plan_id: Optional[int] = None,
        title: Optional[str] = None,
        category: Optional[str] = "Full Body",
        custom_exercises: Optional[List[dict]] = None
    ) -> StructuredWorkoutSessionModel:
        """
        Initializes a fresh structured workout session.
        """
        plan_title = title or "Custom Structured Workout"
        plan_category = category or "Full Body"
        exercises_list = []

        if plan_id:
            preset = next((p for p in PRESET_WORKOUT_PLANS if p["id"] == plan_id), None)
            if preset:
                plan_title = preset["title"]
                plan_category = preset["category"]
                exercises_list = preset["exercises"]

        if custom_exercises:
            exercises_list = custom_exercises

        total_exercises = len(exercises_list)
        total_sets = sum(e.get("target_sets", 3) for e in exercises_list)
        total_target_reps = sum(e.get("target_sets", 3) * e.get("target_reps", 12) for e in exercises_list)

        session = StructuredWorkoutSessionModel(
            user_id=user_id,
            plan_title=plan_title,
            category=plan_category,
            status="IN_PROGRESS",
            total_exercises=total_exercises,
            total_sets=total_sets,
            completed_sets=0,
            total_target_reps=total_target_reps,
            total_actual_reps=0,
            average_form_score=0.0,
            started_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def log_set_result(
        self,
        db: Session,
        structured_session_id: int,
        exercise_id: int,
        set_number: int,
        target_reps: int,
        actual_reps: int,
        duration_sec: int,
        form_score: float,
        form_scores_history: Optional[List[int]] = None,
        feedback_events: Optional[List[str]] = None
    ) -> StructuredWorkoutSetModel:
        """
        Logs set result in structured_workout_sets AND creates standard WorkoutSessionModel record
        so Analytics, Readiness, Training Load, Goals, and Gamification automatically consume telemetry.
        """
        struct_sess = db.query(StructuredWorkoutSessionModel).filter(StructuredWorkoutSessionModel.id == structured_session_id).first()
        if not struct_sess:
            raise ValueError(f"Structured workout session {structured_session_id} not found.")

        ex = db.query(ExerciseModel).filter(ExerciseModel.id == exercise_id).first()
        ex_name = ex.name if ex else "Exercise"

        # 1. Create standard workout session telemetry entry
        standard_session_in = WorkoutSessionCreate(
            user_id=struct_sess.user_id,
            exercise_id=exercise_id,
            repetitions=actual_reps,
            duration_sec=duration_sec,
            form_score=0.0 if actual_reps == 0 else form_score
        )
        
        standard_sess = workout_service.create_workout_session(
            db=db,
            session_in=standard_session_in,
            form_scores_history=form_scores_history,
            feedback_events=feedback_events
        )

        # 2. Record set entry in structured_workout_sets
        set_record = StructuredWorkoutSetModel(
            structured_session_id=structured_session_id,
            workout_session_id=standard_sess.id,
            exercise_id=exercise_id,
            exercise_name=ex_name,
            set_number=set_number,
            target_reps=target_reps,
            actual_reps=actual_reps,
            duration_sec=duration_sec,
            form_score=0.0 if actual_reps == 0 else form_score,
            status="COMPLETED"
        )
        db.add(set_record)

        # 3. Update structured workout aggregate statistics
        struct_sess.completed_sets += 1
        struct_sess.total_actual_reps += actual_reps

        # Recalculate average form score for sets with reps >= 1
        valid_sets = [s for s in struct_sess.sets if s.actual_reps >= 1]
        if actual_reps >= 1:
            valid_sets.append(set_record)

        if valid_sets:
            struct_sess.average_form_score = round(sum(s.form_score for s in valid_sets) / len(valid_sets), 1)
        else:
            struct_sess.average_form_score = 0.0

        db.commit()
        db.refresh(set_record)
        return set_record

    def complete_structured_workout(self, db: Session, structured_session_id: int) -> StructuredWorkoutSessionModel:
        """
        Finalizes structured workout session.
        """
        struct_sess = db.query(StructuredWorkoutSessionModel).filter(StructuredWorkoutSessionModel.id == structured_session_id).first()
        if not struct_sess:
            raise ValueError(f"Structured workout session {structured_session_id} not found.")

        struct_sess.status = "COMPLETED"
        struct_sess.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(struct_sess)
        return struct_sess

    def get_structured_session_summary(self, db: Session, structured_session_id: int) -> StructuredWorkoutSessionModel:
        """
        Retrieves full structured session summary.
        """
        return db.query(StructuredWorkoutSessionModel).filter(StructuredWorkoutSessionModel.id == structured_session_id).first()

    def get_user_structured_history(self, db: Session, user_id: int) -> List[StructuredWorkoutSessionModel]:
        """
        Retrieves historical structured workouts for a user.
        """
        return db.query(StructuredWorkoutSessionModel).filter(StructuredWorkoutSessionModel.user_id == user_id).order_by(StructuredWorkoutSessionModel.started_at.desc()).all()

structured_workout_service = StructuredWorkoutService()
