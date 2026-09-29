from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class AICoachingLogModel(Base):
    """
    SQLAlchemy ORM Model for storing generated AI coaching feedback logs.
    """
    __tablename__ = "ai_coaching_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workout_session_id = Column(Integer, ForeignKey("workout_sessions.id", ondelete="CASCADE"), nullable=False)
    response = Column(Text, nullable=False)
    provider = Column(String(50), nullable=False)  # "Gemini" or "Offline/Rule-Based"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workout_session = relationship("WorkoutSessionModel", back_populates="ai_coaching_logs")
