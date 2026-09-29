from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.database import Base

class MovementFingerprintModel(Base):
    """
    SQLAlchemy ORM Model for persistent storage of multi-dimensional
    biomechanical Movement Fingerprints calculated per completed workout session.
    """
    __tablename__ = "movement_fingerprints"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workout_session_id = Column(Integer, ForeignKey("workout_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True)
    exercise_name = Column(String(100), nullable=False)

    # Core Biomechanical Fingerprint Metrics (Normalized 0.0 - 100.0)
    range_of_motion = Column(Float, nullable=False)
    movement_stability = Column(Float, nullable=False)
    tempo_control = Column(Float, nullable=False)
    repetition_consistency = Column(Float, nullable=False)
    bilateral_symmetry = Column(Float, nullable=True)  # Nullable for unilateral / axial exercises
    overall_movement_quality = Column(Float, nullable=False)

    # Contextual Session Metadata
    form_score = Column(Float, default=100.0, nullable=False)
    repetition_count = Column(Integer, default=0, nullable=False)
    session_duration = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # ORM Relationships
    user = relationship("UserModel", back_populates="movement_fingerprints")
    workout_session = relationship("WorkoutSessionModel", back_populates="movement_fingerprint")
    exercise = relationship("ExerciseModel")

    __table_args__ = (
        Index("ix_movement_fingerprints_user_exercise", "user_id", "exercise_id"),
        Index("ix_movement_fingerprints_user_created", "user_id", "created_at"),
    )
