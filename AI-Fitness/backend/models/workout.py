from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class WorkoutSessionModel(Base):
    """
    SQLAlchemy ORM Model for tracking recorded exercise workout sessions.
    """
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False)
    repetitions = Column(Integer, default=0, nullable=False)
    duration_sec = Column(Integer, default=0, nullable=False)
    form_score = Column(Float, default=100.0, nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("UserModel", back_populates="workout_sessions")
    exercise = relationship("ExerciseModel", back_populates="workout_sessions")
    form_logs = relationship(
        "FormLogModel",
        back_populates="workout_session",
        cascade="all, delete-orphan"
    )
    ai_coaching_logs = relationship(
        "AICoachingLogModel",
        back_populates="workout_session",
        cascade="all, delete-orphan"
    )
    movement_fingerprint = relationship(
        "MovementFingerprintModel",
        back_populates="workout_session",
        uselist=False,
        cascade="all, delete-orphan"
    )

class FormLogModel(Base):
    """
    SQLAlchemy ORM Model for storing granular rep-by-rep form observation logs.
    """
    __tablename__ = "form_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workout_session_id = Column(Integer, ForeignKey("workout_sessions.id", ondelete="CASCADE"), nullable=False)
    form_score = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workout_session = relationship("WorkoutSessionModel", back_populates="form_logs")
