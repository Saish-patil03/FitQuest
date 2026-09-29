from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import relationship
from backend.database import Base

class UserModel(Base):
    """
    SQLAlchemy ORM Model for User accounts & personalized profiles.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    fitness_goal = Column(String(100), nullable=True, default="General Fitness")
    experience_level = Column(String(50), nullable=True, default="Beginner")
    age = Column(Integer, nullable=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    gender = Column(String(20), nullable=True)
    leaderboard_visible = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workout_sessions = relationship(
        "WorkoutSessionModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    achievements = relationship(
        "UserAchievementModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    password_reset_tokens = relationship(
        "PasswordResetTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    goals = relationship(
        "UserGoalModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    movement_fingerprints = relationship(
        "MovementFingerprintModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )




