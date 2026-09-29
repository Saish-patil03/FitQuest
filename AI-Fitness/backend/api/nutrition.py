"""
FastAPI Router for FITQUEST NUTRITION™
Provides RESTful APIs for personalized dietary planning, meal generation,
single-meal regeneration, meal logging, today's summary, and food analysis.
"""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.services.nutrition_service import nutrition_service
from backend.schemas.nutrition import (
    NutritionProfileUpdate,
    NutritionProfileResponse,
    NutritionPlanResponse,
    MealRegenerateRequest,
    MealLogCreate,
    MealLogResponse,
    TodayNutritionSummaryResponse,
    FoodAnalysisRequest,
    FoodAnalysisResponse
)

router = APIRouter(prefix="/nutrition", tags=["Nutrition & Diet Recommendations"])


@router.get("/profile", response_model=NutritionProfileResponse, summary="Get User Nutrition Profile & Targets")
def get_nutrition_profile(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    try:
        profile, user = nutrition_service.get_or_create_profile(db, user_id)
        allergies_list = json.loads(profile.allergies) if profile.allergies else []
        cuisines_list = json.loads(profile.cuisines) if profile.cuisines else []

        return NutritionProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            diet_type=profile.diet_type,
            allergies=allergies_list,
            cuisines=cuisines_list,
            budget=profile.budget,
            meals_per_day=profile.meals_per_day,
            target_calories=profile.target_calories,
            target_protein_g=profile.target_protein_g,
            target_carbs_g=profile.target_carbs_g,
            target_fat_g=profile.target_fat_g,
            bmr_estimate=int((profile.target_calories or 2000) / 1.4),
            tdee_estimate=profile.target_calories,
            fitness_goal=user.fitness_goal,
            health_notes=profile.health_notes,
            updated_at=profile.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch profile: {e}")


@router.put("/profile", response_model=NutritionProfileResponse, summary="Update Nutrition Preferences & Recalculate Targets")
def update_nutrition_profile(
    payload: NutritionProfileUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    try:
        profile = nutrition_service.update_profile(db, user_id, payload)
        user = profile.user
        allergies_list = json.loads(profile.allergies) if profile.allergies else []
        cuisines_list = json.loads(profile.cuisines) if profile.cuisines else []

        return NutritionProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            diet_type=profile.diet_type,
            allergies=allergies_list,
            cuisines=cuisines_list,
            budget=profile.budget,
            meals_per_day=profile.meals_per_day,
            target_calories=profile.target_calories,
            target_protein_g=profile.target_protein_g,
            target_carbs_g=profile.target_carbs_g,
            target_fat_g=profile.target_fat_g,
            bmr_estimate=int((profile.target_calories or 2000) / 1.4),
            tdee_estimate=profile.target_calories,
            fitness_goal=user.fitness_goal if user else "General Fitness",
            health_notes=profile.health_notes,
            updated_at=profile.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update profile: {e}")


@router.get("/today", response_model=TodayNutritionSummaryResponse, summary="Get Today's Nutrition Summary & Progress")
def get_today_nutrition(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    try:
        summary = nutrition_service.get_today_summary(db, user_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch today's nutrition: {e}")


@router.get("/plan", response_model=NutritionPlanResponse, summary="Get Active 7-Day Meal Plan")
def get_active_nutrition_plan(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    try:
        plan = nutrition_service.get_active_plan(db, user_id)
        if not plan:
            # Auto-generate on first visit
            plan = nutrition_service.generate_7day_plan(db, user_id)
        return plan
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch plan: {e}")


@router.post("/plan/generate", response_model=NutritionPlanResponse, summary="Generate / Refresh 7-Day Meal Plan")
def generate_nutrition_plan(
    user_id: int = Depends(get_current_user_id),
    force: bool = True,
    db: Session = Depends(get_db)
):
    try:
        plan = nutrition_service.generate_7day_plan(db, user_id, force_regenerate=force)
        return plan
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Plan generation failed: {e}")


@router.post("/meal/regenerate", response_model=NutritionPlanResponse, summary="Regenerate Single Meal in 7-Day Plan")
def regenerate_single_meal(
    payload: MealRegenerateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    try:
        updated_plan = nutrition_service.regenerate_single_meal(
            db=db,
            user_id=user_id,
            day_num=payload.day,
            meal_type=payload.meal_type,
            reason=payload.reason
        )
        return updated_plan
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Meal regeneration failed: {e}")


@router.post("/meal/log", response_model=MealLogResponse, status_code=status.HTTP_201_CREATED, summary="Log a Meal or Food Entry")
def log_nutrition_meal(
    payload: MealLogCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    try:
        logged = nutrition_service.log_meal(db, user_id, payload)
        return logged
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to log meal: {e}")


@router.delete("/meal/log/{log_id}", summary="Delete Logged Meal Entry")
def delete_logged_meal(
    log_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    success = nutrition_service.delete_meal_log(db, user_id, log_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal log entry not found.")
    return {"status": "success", "message": f"Meal log {log_id} deleted successfully."}


@router.get("/history", response_model=List[MealLogResponse], summary="Get Recent Nutrition Meal Logs")
def get_nutrition_history(
    days: int = 7,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    try:
        logs = nutrition_service.get_meal_history(db, user_id, days=days)
        return logs
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch history: {e}")


@router.post("/analyze-food", response_model=FoodAnalysisResponse, summary="Analyze Food Image or Description")
def analyze_food_item(
    payload: FoodAnalysisRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    try:
        profile, _ = nutrition_service.get_or_create_profile(db, user_id)
        allergies = json.loads(profile.allergies) if profile.allergies else []
        analysis = nutrition_service.analyze_food(
            image_base64=payload.image_base64,
            text_description=payload.text_description,
            user_allergies=allergies
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Food analysis failed: {e}")
