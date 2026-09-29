"""
Comprehensive Automated Test Suite for FITQUEST NUTRITION™
Validates BMR/TDEE calculation, Gemini/Fallback 7-Day Meal Plans, Single-Meal Regeneration,
Allergy Filtering, Meal Logging, Today Summary, Food Analyzer, User Isolation, and Guide Integration.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import Base, get_db
from backend.models import UserModel
from backend.models.nutrition import NutritionProfileModel, NutritionPlanModel, NutritionMealLogModel
from backend.utils.auth import create_access_token
from backend.services.nutrition_service import nutrition_service
from backend.services.guide_service import fitquest_guide_service

# Setup isolated in-memory SQLite database using StaticPool
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_database():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

def create_test_user(db, email="athlete@fitquest.ai", name="Test Athlete", goal="Muscle Gain", weight=78.0, height=180.0, age=26, gender="Male"):
    user = UserModel(
        name=name,
        email=email,
        password_hash="hashed_test_password",
        age=age,
        height=height,
        weight=weight,
        gender=gender,
        fitness_goal=goal,
        experience_level="Intermediate"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

create_auth_token = create_access_token


# ==============================================================================
# 1. BIOMETRIC TARGETS & BMR / TDEE CALCULATION TESTS
# ==============================================================================

def test_bmr_and_tdee_calculation_male():
    """Verify Mifflin-St Jeor equation and goal adjustments for male user."""
    db = TestingSessionLocal()
    user = create_test_user(db, email="male_calc@fitquest.ai", weight=80.0, height=180.0, age=25, gender="Male", goal="Muscle Gain")
    profile, _ = nutrition_service.get_or_create_profile(db, user.id)
    targets = nutrition_service.recompute_and_save_targets(db, user, profile)

    # Weight: 80kg, Height: 180cm, Age: 25 -> BMR = 10*80 + 6.25*180 - 5*25 + 5 = 800 + 1125 - 125 + 5 = 1805
    assert targets["bmr"] == 1805
    assert targets["tdee"] > targets["bmr"]
    # Muscle Gain gives a caloric surplus
    assert targets["daily_target"] > targets["tdee"]
    # High protein for muscle gain (>= 2.0g/kg -> 160g)
    assert targets["protein_g"] >= 160.0
    assert targets["carbs_g"] > 0
    assert targets["fat_g"] > 0
    db.close()

def test_bmr_and_tdee_calculation_female_weight_loss():
    """Verify Mifflin-St Jeor equation and caloric deficit for female weight loss."""
    db = TestingSessionLocal()
    user = create_test_user(db, email="female_calc@fitquest.ai", weight=65.0, height=165.0, age=28, gender="Female", goal="Weight Loss")
    profile, _ = nutrition_service.get_or_create_profile(db, user.id)
    targets = nutrition_service.recompute_and_save_targets(db, user, profile)

    # Weight: 65kg, Height: 165cm, Age: 28 -> BMR = 10*65 + 6.25*165 - 5*28 - 161 = 650 + 1031.25 - 140 - 161 = 1380
    assert targets["bmr"] == 1380
    # Weight loss target should be below TDEE
    assert targets["daily_target"] < targets["tdee"]
    assert targets["protein_g"] >= 100.0
    db.close()


# ==============================================================================
# 2. DETERMINISTIC FALLBACK & ALLERGEN FILTERING TESTS
# ==============================================================================

def test_deterministic_7day_plan_generation():
    """Verify deterministic 7-day plan generator creates a valid 7-day structure with 4 meals per day."""
    plan_dict = nutrition_service._generate_plan_deterministic(
        diet_type="Non-Vegetarian",
        allergies=[],
        cuisines=["Indian", "Mediterranean"],
        target_calories=2200,
        target_protein=140.0,
        target_carbs=240.0,
        target_fat=65.0,
        meals_per_day=4
    )

    assert "days" in plan_dict
    assert len(plan_dict["days"]) == 7

    for day in plan_dict["days"]:
        assert len(day["meals"]) == 4
        meal_types = [m["type"].lower() for m in day["meals"]]
        assert "breakfast" in meal_types
        assert "lunch" in meal_types
        assert "snack" in meal_types
        assert "dinner" in meal_types
        assert day["daily_calories"] > 0
        assert day["daily_protein_g"] > 0

def test_strict_allergy_filtering():
    """Verify allergen filtering substitutes dishes containing allergens."""
    plan = {
        "days": [
            {
                "day": 1,
                "meals": [
                    {
                        "name": "Peanut Butter Banana Toast with Crushed Walnuts",
                        "type": "breakfast",
                        "calories": 420,
                        "protein_g": 18,
                        "carbs_g": 48,
                        "fat_g": 16,
                        "ingredients": ["Whole wheat bread", "Peanut butter", "Walnuts", "Banana"],
                        "instructions": ["Toast bread and spread peanut butter."],
                        "tags": ["Nuts", "Quick"]
                    }
                ]
            }
        ]
    }

    nutrition_service._filter_and_sanitize_allergens(plan, allergies=["Nuts", "Peanuts"])
    meal = plan["days"][0]["meals"][0]
    for ing in meal["ingredients"]:
        assert "peanut" not in ing.lower()
        assert "walnut" not in ing.lower()

def test_single_meal_regeneration():
    """Verify single meal regeneration swaps only the requested meal while preserving the rest."""
    db = TestingSessionLocal()
    user = create_test_user(db, email="regen_user@fitquest.ai")
    
    # 1. Generate plan
    plan_dict = nutrition_service.generate_7day_plan(db, user.id, force_regenerate=True)

    day1_lunch_before = next(m for m in plan_dict["days"][0]["meals"] if m["type"].lower() == "lunch")
    day1_dinner_before = next(m for m in plan_dict["days"][0]["meals"] if m["type"].lower() == "dinner")
    day2_lunch_before = next(m for m in plan_dict["days"][1]["meals"] if m["type"].lower() == "lunch")

    # 2. Swap only Day 1 Lunch
    updated_plan = nutrition_service.regenerate_single_meal(
        db=db,
        user_id=user.id,
        day_num=1,
        meal_type="lunch"
    )

    day1_dinner_after = next(m for m in updated_plan["days"][0]["meals"] if m["type"].lower() == "dinner")
    day2_lunch_after = next(m for m in updated_plan["days"][1]["meals"] if m["type"].lower() == "lunch")

    # Day 1 Dinner and Day 2 Lunch MUST be preserved identically
    assert day1_dinner_before["name"] == day1_dinner_after["name"]
    assert day2_lunch_before["name"] == day2_lunch_after["name"]
    db.close()


# ==============================================================================
# 3. TEXT NUTRIENT ESTIMATION & AI FOOD ANALYZER TESTS
# ==============================================================================

def test_smart_text_nutrient_estimation():
    """Verify heuristic NLP nutrient estimator for common foods."""
    cal_eggs, p_eggs, c_eggs, f_eggs = nutrition_service.estimate_nutrients_from_text("3 boiled eggs with multigrain toast")
    assert cal_eggs > 250
    assert p_eggs >= 18.0

    cal_chk, p_chk, c_chk, f_chk = nutrition_service.estimate_nutrients_from_text("200g grilled chicken breast with brown rice")
    assert p_chk >= 40.0
    assert cal_chk > 400

    cal_pan, p_pan, c_pan, f_pan = nutrition_service.estimate_nutrients_from_text("Paneer butter masala with 2 rotis")
    assert p_pan >= 16.0
    assert cal_pan > 400

def test_food_analyzer_service():
    """Verify Food Analyzer returns structured macros and advice."""
    result = nutrition_service.analyze_food(
        image_base64=None,
        text_description="Grilled Salmon with sweet potato and steamed broccoli"
    )

    assert result["food_name"] is not None
    assert result["estimated_calories"] > 0
    assert result["protein_g"] > 0
    assert "recommendations" in result


# ==============================================================================
# 4. REST API ENDPOINTS & INTEGRATION TESTS
# ==============================================================================

def test_nutrition_profile_api():
    """Test GET and PUT /api/v1/nutrition/profile."""
    client = TestClient(app)
    db = TestingSessionLocal()
    user = create_test_user(db, email="nutrition_user1@fitquest.ai")
    token = create_auth_token(user.id)

    # 1. GET initial profile (auto-initialized)
    res = client.get("/api/v1/nutrition/profile", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == user.id
    assert data["target_calories"] > 1200

    # 2. PUT update profile preferences
    update_payload = {
        "diet_type": "Vegetarian",
        "allergies": ["Nuts", "Dairy"],
        "cuisines": ["Indian", "Asian"],
        "budget": "Premium",
        "meals_per_day": 3
    }
    update_res = client.put("/api/v1/nutrition/profile", json=update_payload, headers={"Authorization": f"Bearer {token}"})
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["diet_type"] == "Vegetarian"
    assert "Nuts" in updated_data["allergies"]
    assert "Dairy" in updated_data["allergies"]
    assert updated_data["meals_per_day"] == 3
    db.close()

def test_nutrition_meal_logging_and_summary_api():
    """Test logging meals and verifying today's progress calculation."""
    client = TestClient(app)
    db = TestingSessionLocal()
    user = create_test_user(db, email="nutrition_logger@fitquest.ai")
    token = create_auth_token(user.id)

    # 1. Check Today Summary before logging
    today_res = client.get("/api/v1/nutrition/today", headers={"Authorization": f"Bearer {token}"})
    assert today_res.status_code == 200
    summary = today_res.json()
    assert summary["calories_logged"] == 0
    assert summary["meals_logged_count"] == 0

    # 2. Log Breakfast
    log1_res = client.post(
        "/api/v1/nutrition/meal/log",
        json={"meal_type": "breakfast", "food_name": "Oatmeal with banana and whey protein", "calories": 450, "protein_g": 32.0, "carbs_g": 60.0, "fat_g": 8.0},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert log1_res.status_code == 201
    log1 = log1_res.json()
    assert log1["calories"] == 450
    assert log1["protein_g"] == 32.0

    # 3. Log Lunch with auto-estimation
    log2_res = client.post(
        "/api/v1/nutrition/meal/log",
        json={"meal_type": "lunch", "food_name": "Grilled chicken breast with rice and salad"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert log2_res.status_code == 201
    log2 = log2_res.json()
    assert log2["calories"] > 0
    assert log2["protein_g"] > 0

    # 4. Verify updated Today's Nutrition Summary
    updated_today = client.get("/api/v1/nutrition/today", headers={"Authorization": f"Bearer {token}"}).json()
    assert updated_today["calories_logged"] == 450 + log2["calories"]
    assert updated_today["protein_logged"] == pytest.approx(32.0 + log2["protein_g"], rel=1e-2)
    assert updated_today["meals_logged_count"] == 2
    assert "breakfast" in updated_today["meal_types_logged"]
    assert "lunch" in updated_today["meal_types_logged"]

    # 5. Delete log1
    del_res = client.delete(f"/api/v1/nutrition/meal/log/{log1['id']}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200

    # Verify summary after delete
    post_del_today = client.get("/api/v1/nutrition/today", headers={"Authorization": f"Bearer {token}"}).json()
    assert post_del_today["meals_logged_count"] == 1
    db.close()

def test_meal_plan_generation_and_regeneration_api():
    """Test 7-Day Plan generation and single meal swap via REST API."""
    client = TestClient(app)
    db = TestingSessionLocal()
    user = create_test_user(db, email="plan_athlete@fitquest.ai")
    token = create_auth_token(user.id)

    # 1. Generate 7-Day Plan
    gen_res = client.post("/api/v1/nutrition/plan/generate?force=true", headers={"Authorization": f"Bearer {token}"})
    assert gen_res.status_code == 200
    plan = gen_res.json()
    assert len(plan["days"]) == 7

    # 2. Swap single meal on Day 3
    swap_res = client.post(
        "/api/v1/nutrition/meal/regenerate",
        json={"day": 3, "meal_type": "dinner"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert swap_res.status_code == 200
    swapped_plan = swap_res.json()
    assert len(swapped_plan["days"]) == 7
    day3_dinner = next(m for m in swapped_plan["days"][2]["meals"] if m["type"].lower() == "dinner")
    assert day3_dinner["name"] is not None
    db.close()

def test_food_analyzer_api():
    """Test POST /api/v1/nutrition/analyze-food."""
    client = TestClient(app)
    db = TestingSessionLocal()
    user = create_test_user(db, email="analyzer_user@fitquest.ai")
    token = create_auth_token(user.id)

    res = client.post(
        "/api/v1/nutrition/analyze-food",
        json={"text_description": "2 Rotis with Paneer Bhurji and cucumber salad"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["estimated_calories"] > 0
    assert data["protein_g"] > 0
    db.close()

def test_multi_tenant_nutrition_isolation():
    """Ensure User A cannot access or modify User B's nutrition plan or logs."""
    client = TestClient(app)
    db = TestingSessionLocal()
    user_a = create_test_user(db, email="user_a@fitquest.ai", name="User A")
    user_b = create_test_user(db, email="user_b@fitquest.ai", name="User B")

    token_a = create_auth_token(user_a.id)
    token_b = create_auth_token(user_b.id)

    # User A logs a meal
    log_a = client.post(
        "/api/v1/nutrition/meal/log",
        json={"meal_type": "breakfast", "food_name": "Secret Breakfast of A", "calories": 500, "protein_g": 30.0},
        headers={"Authorization": f"Bearer {token_a}"}
    ).json()

    # User B's today summary must NOT contain User A's meal
    summary_b = client.get("/api/v1/nutrition/today", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert summary_b["calories_logged"] == 0
    assert len(summary_b["logged_meals"]) == 0

    # User B cannot delete User A's meal log
    del_res = client.delete(f"/api/v1/nutrition/meal/log/{log_a['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert del_res.status_code == 404
    db.close()

def test_fitquest_guide_nutrition_integration():
    """Test that FitQuest Guide service recognizes nutrition queries and suggests nutritionView."""
    client = TestClient(app)
    response = client.post("/api/v1/guide/chat", json={
        "message": "What is FitQuest Nutrition and how do I view my diet plan?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["nav_suggestion"] == "nutritionView"
    assert "Nutrition" in data["reply"] or "nutrition" in data["reply"] or "meal" in data["reply"]
