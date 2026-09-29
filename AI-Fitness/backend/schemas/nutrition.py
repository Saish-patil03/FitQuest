from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class NutritionProfileUpdate(BaseModel):
    diet_type: Optional[str] = Field(None, description="Diet style: Vegetarian, Vegan, Non-Vegetarian, Pescatarian, Keto")
    allergies: Optional[List[str]] = Field(None, description="List of declared allergens e.g. ['Nuts', 'Dairy']")
    cuisines: Optional[List[str]] = Field(None, description="Preferred cuisines e.g. ['Indian', 'Mediterranean']")
    budget: Optional[str] = Field(None, description="Budget tier: Low, Moderate, Premium")
    meals_per_day: Optional[int] = Field(None, ge=3, le=5, description="Number of meals per day (3-5)")
    health_notes: Optional[str] = Field(None, description="Optional custom health or dietary notes")

class NutritionProfileResponse(BaseModel):
    id: int
    user_id: int
    diet_type: str
    allergies: List[str]
    cuisines: List[str]
    budget: str
    meals_per_day: int
    target_calories: Optional[int] = None
    target_protein_g: Optional[float] = None
    target_carbs_g: Optional[float] = None
    target_fat_g: Optional[float] = None
    bmr_estimate: Optional[int] = None
    tdee_estimate: Optional[int] = None
    fitness_goal: Optional[str] = None
    health_notes: Optional[str] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MealItemSchema(BaseModel):
    type: str = Field(..., description="Meal type: breakfast, lunch, snack, dinner")
    name: str = Field(..., description="Descriptive meal title")
    calories: int = Field(..., ge=0, description="Approximate calorie content")
    protein_g: float = Field(..., ge=0, description="Protein in grams")
    carbs_g: float = Field(0.0, ge=0, description="Carbohydrates in grams")
    fat_g: float = Field(0.0, ge=0, description="Fats in grams")
    ingredients: List[str] = Field(default_factory=list, description="List of ingredients with quantities")
    instructions: List[str] = Field(default_factory=list, description="Simple step-by-step preparation steps")
    tags: List[str] = Field(default_factory=list, description="Allergen/Diet tags e.g. High Protein, Gluten-Free")

class DayMealPlanSchema(BaseModel):
    day: int = Field(..., ge=1, le=7, description="Day index 1-7")
    day_name: str = Field(..., description="Day title e.g. Day 1 (Monday)")
    meals: List[MealItemSchema] = Field(..., description="List of meals for the day")
    daily_calories: int = Field(0, description="Total day calories")
    daily_protein_g: float = Field(0.0, description="Total day protein in grams")
    daily_carbs_g: float = Field(0.0, description="Total day carbs in grams")
    daily_fat_g: float = Field(0.0, description="Total day fat in grams")

class NutritionPlanResponse(BaseModel):
    id: int
    user_id: int
    is_active: bool
    generator_source: str
    target_summary: Dict[str, Any]
    days: List[DayMealPlanSchema]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MealRegenerateRequest(BaseModel):
    day: int = Field(..., ge=1, le=7, description="Day number 1 to 7")
    meal_type: str = Field(..., description="breakfast, lunch, snack, or dinner")
    reason: Optional[str] = Field(None, description="Optional preference/reason e.g. 'prefer something quick'")

class MealLogCreate(BaseModel):
    meal_type: str = Field(..., description="breakfast, lunch, snack, dinner")
    food_name: str = Field(..., min_length=1, max_length=200, description="Food item or meal description")
    calories: Optional[int] = Field(None, ge=0, description="Calories (auto-estimated if omitted)")
    protein_g: Optional[float] = Field(None, ge=0, description="Protein in grams (auto-estimated if omitted)")
    carbs_g: Optional[float] = Field(None, ge=0, description="Carbs in grams (auto-estimated if omitted)")
    fat_g: Optional[float] = Field(None, ge=0, description="Fat in grams (auto-estimated if omitted)")
    notes: Optional[str] = Field(None, description="Optional notes")

class MealLogResponse(BaseModel):
    id: int
    user_id: int
    meal_type: str
    food_name: str
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    notes: Optional[str] = None
    image_url: Optional[str] = None
    logged_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TodayNutritionSummaryResponse(BaseModel):
    date: str
    fitness_goal: str
    daily_calorie_target: int
    daily_protein_target: float
    daily_carbs_target: float
    daily_fat_target: float

    calories_logged: int
    protein_logged: float
    carbs_logged: float
    fat_logged: float

    calories_remaining: int
    protein_remaining: float
    calorie_progress_pct: float
    protein_progress_pct: float

    meals_logged_count: int
    meals_total_target: int
    meal_types_logged: List[str]

    bmr_estimate: int
    tdee_estimate: int
    logged_meals: List[MealLogResponse]

class FoodAnalysisRequest(BaseModel):
    image_base64: Optional[str] = Field(None, description="Base64 encoded image string (JPEG/PNG/WebP)")
    text_description: Optional[str] = Field(None, description="Text description of the food item")

class FoodAnalysisResponse(BaseModel):
    food_name: str
    estimated_calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence: float
    detected_items: List[str]
    allergen_warnings: List[str]
    recommendations: str
    provider: str
