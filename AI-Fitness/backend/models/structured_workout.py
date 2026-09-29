from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.database import Base

class StructuredWorkoutPlanModel(Base):
    """
    SQLAlchemy ORM Model for pre-configured or custom structured workout plans.
    """
    __tablename__ = "structured_workout_plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(120), nullable=False)
    category = Column(String(80), nullable=False, index=True)
    description = Column(Text, nullable=True)
    difficulty = Column(String(50), default="Intermediate")
    estimated_duration_min = Column(Integer, default=20)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    exercises = relationship(
        "StructuredWorkoutPlanExerciseModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="StructuredWorkoutPlanExerciseModel.order_index"
    )

class StructuredWorkoutPlanExerciseModel(Base):
    """
    SQLAlchemy ORM Model mapping exercises within a structured workout plan.
    """
    __tablename__ = "structured_workout_plan_exercises"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("structured_workout_plans.id", ondelete="CASCADE"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    target_sets = Column(Integer, default=3, nullable=False)
    target_reps = Column(Integer, default=12, nullable=False)
    target_duration_sec = Column(Integer, default=0, nullable=False)
    rest_duration_sec = Column(Integer, default=30, nullable=False)

    # Relationships
    plan = relationship("StructuredWorkoutPlanModel", back_populates="exercises")
    exercise = relationship("ExerciseModel")

class StructuredWorkoutSessionModel(Base):
    """
    SQLAlchemy ORM Model for active/completed structured multi-exercise workout sessions.
    """
    __tablename__ = "structured_workout_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_title = Column(String(120), nullable=False)
    category = Column(String(80), nullable=False)
    status = Column(String(50), default="IN_PROGRESS", nullable=False) # IN_PROGRESS, COMPLETED, ABANDONED
    total_exercises = Column(Integer, default=0, nullable=False)
    total_sets = Column(Integer, default=0, nullable=False)
    completed_sets = Column(Integer, default=0, nullable=False)
    total_target_reps = Column(Integer, default=0, nullable=False)
    total_actual_reps = Column(Integer, default=0, nullable=False)
    average_form_score = Column(Float, default=0.0, nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("UserModel")
    sets = relationship(
        "StructuredWorkoutSetModel",
        back_populates="structured_session",
        cascade="all, delete-orphan"
    )

class StructuredWorkoutSetModel(Base):
    """
    SQLAlchemy ORM Model for tracking individual sets within a structured workout session.
    Linked to standard WorkoutSessionModel for 100% analytics integration.
    """
    __tablename__ = "structured_workout_sets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    structured_session_id = Column(Integer, ForeignKey("structured_workout_sessions.id", ondelete="CASCADE"), nullable=False)
    workout_session_id = Column(Integer, ForeignKey("workout_sessions.id", ondelete="SET NULL"), nullable=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False)
    exercise_name = Column(String(100), nullable=False)
    set_number = Column(Integer, nullable=False)
    target_reps = Column(Integer, default=12, nullable=False)
    actual_reps = Column(Integer, default=0, nullable=False)
    duration_sec = Column(Integer, default=0, nullable=False)
    form_score = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="COMPLETED", nullable=False) # COMPLETED, SKIPPED

    # Relationships
    structured_session = relationship("StructuredWorkoutSessionModel", back_populates="sets")
    workout_session = relationship("WorkoutSessionModel")
    exercise = relationship("ExerciseModel")
