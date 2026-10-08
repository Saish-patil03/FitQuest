import os
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload, selectinload


from backend.models import (
    UserModel,
    ExerciseModel,
    WorkoutSessionModel,
    FormLogModel,
    AICoachingLogModel
)
from backend.schemas import UserCreate, WorkoutSessionCreate
from backend.services.ai_service import ai_service
from assistant import WorkoutSessionData, UserProfile

class WorkoutService:
    """
    Business logic & persistence orchestration for Users, Exercises, Workouts, and AI Coaching.
    """

    # --- User Operations ---
    @staticmethod
    def create_user(db: Session, user_in: UserCreate) -> UserModel:
        existing = db.query(UserModel).filter(UserModel.email == user_in.email).first()
        if existing:
            return existing

        user = UserModel(
            name=user_in.name,
            email=user_in.email,
            fitness_goal=user_in.fitness_goal or "General Fitness",
            experience_level=user_in.experience_level or "Beginner",
            age=user_in.age,
            height=user_in.height,
            weight=user_in.weight,
            gender=user_in.gender
        )
        if user_in.password:
            from backend.utils.auth import hash_password
            user.password_hash = hash_password(user_in.password)

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def register_user(db: Session, reg_in) -> UserModel:
        existing = db.query(UserModel).filter(UserModel.email == reg_in.email).first()
        if existing:
            raise ValueError(f"An account with email '{reg_in.email}' already exists.")

        from backend.utils.auth import hash_password
        user = UserModel(
            name=reg_in.name,
            email=reg_in.email,
            password_hash=hash_password(reg_in.password),
            fitness_goal=reg_in.fitness_goal or "General Fitness",
            experience_level=reg_in.experience_level or "Beginner",
            age=reg_in.age,
            height=reg_in.height,
            weight=reg_in.weight,
            gender=reg_in.gender
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[UserModel]:
        user = db.query(UserModel).filter(UserModel.email == email).first()
        if not user or not user.password_hash:
            return None
        from backend.utils.auth import verify_password
        if verify_password(password, user.password_hash):
            return user
        return None

    @staticmethod
    def update_user_profile(db: Session, user_id: int, profile_in) -> UserModel:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found.")

        if profile_in.name is not None:
            user.name = profile_in.name
        if profile_in.fitness_goal is not None:
            user.fitness_goal = profile_in.fitness_goal
        if profile_in.experience_level is not None:
            user.experience_level = profile_in.experience_level
        if profile_in.age is not None:
            user.age = profile_in.age
        if profile_in.height is not None:
            user.height = profile_in.height
        if profile_in.weight is not None:
            user.weight = profile_in.weight
        if profile_in.gender is not None:
            user.gender = profile_in.gender
        if getattr(profile_in, "leaderboard_visible", None) is not None:
            user.leaderboard_visible = profile_in.leaderboard_visible

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user(db: Session, user_id: int) -> Optional[UserModel]:
        return db.query(UserModel).filter(UserModel.id == user_id).first()

    @staticmethod
    def get_users(db: Session) -> List[UserModel]:
        return db.query(UserModel).all()


    # --- Exercise Catalogue Operations ---
    @staticmethod
    def get_exercises(db: Session) -> List[ExerciseModel]:
        return db.query(ExerciseModel).all()

    @staticmethod
    def get_exercise(db: Session, exercise_id: int) -> Optional[ExerciseModel]:
        return db.query(ExerciseModel).filter(ExerciseModel.id == exercise_id).first()

    @staticmethod
    def get_exercise_by_name(db: Session, name: str) -> Optional[ExerciseModel]:
        return db.query(ExerciseModel).filter(ExerciseModel.name == name).first()

    # --- Workout Session & AI Orchestration ---
    @staticmethod
    def create_workout_session(
        db: Session,
        session_in: WorkoutSessionCreate,
        form_scores_history: Optional[List[int]] = None,
        feedback_events: Optional[List[str]] = None
    ) -> WorkoutSessionModel:
        user = db.query(UserModel).filter(UserModel.id == session_in.user_id).first()
        exercise = db.query(ExerciseModel).filter(ExerciseModel.id == session_in.exercise_id).first()

        if not user:
            raise ValueError(f"User with ID {session_in.user_id} not found.")
        if not exercise:
            raise ValueError(f"Exercise with ID {session_in.exercise_id} not found.")

        actual_form_score = 0.0 if session_in.repetitions == 0 else session_in.form_score

        # 1. Create WorkoutSession Record
        workout_session = WorkoutSessionModel(
            user_id=session_in.user_id,
            exercise_id=session_in.exercise_id,
            repetitions=session_in.repetitions,
            duration_sec=session_in.duration_sec,
            form_score=actual_form_score,
            started_at=datetime.now(timezone.utc),
            completed_at=session_in.completed_at or datetime.now(timezone.utc)
        )
        db.add(workout_session)
        db.flush()  # Generate workout_session.id

        # 2. Add Form Logs if provided
        events = feedback_events or []
        for event in events:
            form_log = FormLogModel(
                workout_session_id=workout_session.id,
                form_score=actual_form_score,
                feedback=event
            )
            workout_session.form_logs.append(form_log)

        # 3. Build Telemetry Payload for Member 4 AI Assistant
        telemetry = WorkoutSessionData(
            exercise_name=exercise.name,
            rep_count=session_in.repetitions,
            duration_sec=session_in.duration_sec,
            form_score=actual_form_score,
            form_scores_history=form_scores_history or [],
            feedback_events=events
        )

        user_profile = UserProfile(
            user_id=str(user.id),
            fitness_goal=user.fitness_goal or "General Fitness",
            experience_level=user.experience_level or "Intermediate"
        )

        # 4. Trigger AI Assistant & Store Coaching Log
        ai_response_text, provider = ai_service.generate_coaching_for_session(telemetry, user_profile)
        coaching_log = AICoachingLogModel(
            workout_session_id=workout_session.id,
            response=ai_response_text,
            provider=provider
        )
        workout_session.ai_coaching_logs.append(coaching_log)

        # 5. Automatically evaluate & award gamification achievements for valid workouts (reps >= 1)
        if session_in.repetitions >= 1:
            from backend.services.gamification_service import gamification_service
            gamification_service.evaluate_and_award_achievements(db, user.id)

        # Commit transaction
        db.commit()
        return WorkoutService.get_workout_session(db, workout_session.id) or workout_session


    @staticmethod
    def get_workout_session(db: Session, session_id: int) -> Optional[WorkoutSessionModel]:
        return (
            db.query(WorkoutSessionModel)
            .options(
                joinedload(WorkoutSessionModel.user),
                joinedload(WorkoutSessionModel.exercise),
                selectinload(WorkoutSessionModel.form_logs),
                selectinload(WorkoutSessionModel.ai_coaching_logs)
            )
            .filter(WorkoutSessionModel.id == session_id)
            .first()
        )

    @staticmethod
    def get_user_workouts(db: Session, user_id: int) -> List[WorkoutSessionModel]:
        return (
            db.query(WorkoutSessionModel)
            .options(
                joinedload(WorkoutSessionModel.exercise),
                joinedload(WorkoutSessionModel.ai_coaching_logs)
            )
            .filter(WorkoutSessionModel.user_id == user_id)
            .order_by(WorkoutSessionModel.started_at.desc())
            .all()
        )

    # --- Password Reset Operations ---
    @staticmethod
    def create_password_reset_token(db: Session, email: str) -> Optional[str]:
        """
        Creates a temporary single-use password reset token for the given email address.
        Stores only the SHA-256 hash in the database and outputs development reset link.
        """
        if not email or not email.strip():
            return None

        clean_email = email.strip().lower()
        from sqlalchemy import func
        user = db.query(UserModel).filter(func.lower(UserModel.email) == clean_email).first()
        if not user:
            # Do NOT reveal user absence for security (anti-enumeration)
            return None

        from datetime import timedelta
        from backend.models import PasswordResetTokenModel
        from backend.utils.auth import generate_reset_token, hash_reset_token

        raw_token = generate_reset_token()
        token_hash = hash_reset_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=20)

        reset_obj = PasswordResetTokenModel(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            used=False
        )
        db.add(reset_obj)
        db.commit()

        # Dispatch email via EmailService (handles SMTP or Development mode based on settings/env)
        from backend.config import settings
        from backend.services.email_service import email_service

        frontend_url = os.environ.get("FITQUEST_FRONTEND_URL", settings.FITQUEST_FRONTEND_URL).rstrip("/")
        dev_link = f"{frontend_url}/?token={raw_token}"

        email_service.send_password_reset_email(user.email, dev_link)

        return raw_token



    @staticmethod
    def reset_password_with_token(db: Session, token: str, new_password: str) -> bool:
        """
        Validates reset token, checks expiration and single-use status, and updates user password_hash.
        """
        if not new_password or len(new_password) < 6:
            raise ValueError("Password must be at least 6 characters long.")

        if not token or not token.strip():
            raise ValueError("This password reset link is invalid or has expired. Please request a new one.")

        from backend.models import PasswordResetTokenModel
        from backend.utils.auth import hash_reset_token, hash_password

        token_hash = hash_reset_token(token.strip())
        reset_obj = (
            db.query(PasswordResetTokenModel)
            .filter(
                PasswordResetTokenModel.token_hash == token_hash,
                PasswordResetTokenModel.used == False
            )
            .first()
        )

        if not reset_obj:
            raise ValueError("This password reset link is invalid or has expired. Please request a new one.")

        # Check expiration
        now = datetime.now(timezone.utc)
        expires_at = reset_obj.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            raise ValueError("This password reset link is invalid or has expired. Please request a new one.")

        # Update user password
        user = db.query(UserModel).filter(UserModel.id == reset_obj.user_id).first()
        if not user:
            raise ValueError("This password reset link is invalid or has expired. Please request a new one.")

        user.password_hash = hash_password(new_password)
        reset_obj.used = True
        db.commit()
        return True

workout_service = WorkoutService()

