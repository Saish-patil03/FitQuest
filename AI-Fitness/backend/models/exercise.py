from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from backend.database import Base

class ExerciseModel(Base):
    """
    SQLAlchemy ORM Model for Exercise catalogue (seeded from ExerciseRegistry).
    """
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    muscle_group = Column(String(100), nullable=True)
    difficulty = Column(String(50), nullable=True)

    # Relationships
    workout_sessions = relationship(
        "WorkoutSessionModel",
        back_populates="exercise"
    )
