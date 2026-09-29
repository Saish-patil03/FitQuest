from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class NutritionProfileModel(Base):
    """
    SQLAlchemy ORM Model for User Dietary Preferences & Calculated Nutrition Targets.
    Additive model isolated to the Nutrition module.
    """
    __tablename__ = "nutrition_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    diet_type = Column(String(50), default="Non-Vegetarian", nullable=False) # 'Vegetarian', 'Vegan', 'Non-Vegetarian', 'Pescatarian', 'Keto'
    allergies = Column(Text, default="[]", nullable=False) # JSON list of strings e.g. ["Nuts", "Dairy"]
    cuisines = Column(Text, default="[\"Indian\", \"Mediterranean\"]", nullable=False) # JSON list
    budget = Column(String(20), default="Moderate", nullable=False) # 'Low', 'Moderate', 'Premium'
    meals_per_day = Column(Integer, default=4, nullable=False) # 3 or 4

    target_calories = Column(Integer, nullable=True) # Estimated daily target in kcal
    target_protein_g = Column(Float, nullable=True) # Target protein in grams
    target_carbs_g = Column(Float, nullable=True) # Target carbs in grams
    target_fat_g = Column(Float, nullable=True) # Target fat in grams

    health_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("UserModel", backref="nutrition_profile")


class NutritionPlanModel(Base):
    """
    SQLAlchemy ORM Model for storing Active and Historical 7-Day Nutrition Plans.
    """
    __tablename__ = "nutrition_plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    generator_source = Column(String(50), default="Gemini AI", nullable=False) # 'Gemini AI' or 'Deterministic Fallback'
    plan_data = Column(Text, nullable=False) # JSON serialized 7-day meal structure

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("UserModel", backref="nutrition_plans")


class NutritionMealLogModel(Base):
    """
    SQLAlchemy ORM Model for User Daily Meal & Food Logs.
    """
    __tablename__ = "nutrition_meal_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    meal_type = Column(String(30), nullable=False) # 'breakfast', 'lunch', 'snack', 'dinner'
    food_name = Column(String(200), nullable=False)
    calories = Column(Integer, default=0, nullable=False)
    protein_g = Column(Float, default=0.0, nullable=False)
    carbs_g = Column(Float, default=0.0, nullable=False)
    fat_g = Column(Float, default=0.0, nullable=False)

    image_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    logged_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    user = relationship("UserModel", backref="nutrition_meal_logs")
