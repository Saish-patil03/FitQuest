from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class UserGoalModel(Base):
    """
    SQLAlchemy ORM Model for personalized fitness targets and goals.
    """
    __tablename__ = "user_goals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id", ondelete="SET NULL"), nullable=True)

    goal_type = Column(String(50), nullable=False) # 'REPETITION', 'FREQUENCY', 'FORM_SCORE', 'EXERCISE_PR'
    target_value = Column(Float, nullable=False)   # e.g., 100.0 (reps), 4.0 (workout days), 90.0 (form %)
    time_frame = Column(String(20), default="WEEKLY", nullable=False) # 'WEEKLY', 'MONTHLY', 'ALL_TIME'

    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)

    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("UserModel", back_populates="goals")
    exercise = relationship("ExerciseModel")
