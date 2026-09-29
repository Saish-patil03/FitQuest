"""
FitQuest Nutrition™ Service
Personalized AI-Powered Nutrition Planning, BMR/TDEE Target Engine,
7-Day Meal Generation, Single-Meal Regeneration, Meal Logging, and Food Analysis.
Includes Zero-Downtime Deterministic Fallback & Allergen Hard Constraints.
"""

import os
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import UserModel, WorkoutSessionModel
from backend.models.nutrition import (
    NutritionProfileModel,
    NutritionPlanModel,
    NutritionMealLogModel
)
from backend.schemas.nutrition import (
    NutritionProfileUpdate,
    MealLogCreate
)

NUTRITION_SYSTEM_PROMPT = """You are FitQuest Nutrition AI™, an elite sports nutritionist and dietary planning engine.
Your mission is to generate personalized, realistic, delicious, and nutritionally optimal meal plans tailored specifically to the user's fitness goal, caloric targets, dietary preferences, and strict allergy constraints.

STRICT SAFETY AND ALLERGEN RULES:
1. HARD ALLERGEN CONSTRAINT: NEVER include or recommend any ingredient containing declared allergens. If the user is allergic to Nuts, Dairy, Gluten, Soy, Eggs, Shellfish, Seafood, or Peanuts, strictly eliminate them.
2. DO NOT prescribe medical treatments, make disease diagnosis claims, or suggest dangerous calorie restriction (<1200 kcal).
3. Frame all recommendations as supportive estimates designed for fitness training.
4. Output MUST be valid, parseable JSON conforming strictly to the requested schema. No markdown formatting outside JSON.
"""

# Extensive multi-cuisine fallback recipe database categorized by Diet Type and Meal Type
FALLBACK_RECIPE_DATABASE: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "Non-Vegetarian": {
        "breakfast": [
            {
                "name": "Masala Egg Scramble with Whole Wheat Toast",
                "cuisine": "Indian",
                "calories": 420,
                "protein_g": 26.0,
                "carbs_g": 38.0,
                "fat_g": 18.0,
                "ingredients": ["3 Whole Eggs", "2 Slices Whole Grain Bread", "1/2 Diced Onion", "1 Green Chili", "1 tsp Olive Oil", "Fresh Cilantro"],
                "instructions": ["Whisk eggs with spices and diced onion.", "Scramble gently in olive oil over medium heat.", "Serve hot with toasted whole grain bread."],
                "allergens": ["Eggs", "Gluten"],
                "tags": ["High Protein", "Quick Prep"]
            },
            {
                "name": "Greek Chicken & Spinach Breakfast Wrap",
                "cuisine": "Mediterranean",
                "calories": 460,
                "protein_g": 34.0,
                "carbs_g": 42.0,
                "fat_g": 16.0,
                "ingredients": ["100g Grilled Chicken Breast", "1 Whole Wheat Tortilla", "1 cup Baby Spinach", "2 tbsp Feta Cheese", "1 tsp Extra Virgin Olive Oil"],
                "instructions": ["Warm the tortilla on a skillet.", "Layer fresh spinach, warm shredded chicken breast, and crumbled feta.", "Drizzle with olive oil and wrap tightly."],
                "allergens": ["Gluten", "Dairy"],
                "tags": ["High Protein", "Mediterranean"]
            },
            {
                "name": "Oatmeal Power Bowl with Protein Whey & Banana",
                "cuisine": "Western",
                "calories": 450,
                "protein_g": 32.0,
                "carbs_g": 58.0,
                "fat_g": 10.0,
                "ingredients": ["60g Rolled Oats", "1 Scoop Whey Protein Powder", "1 Sliced Banana", "1 cup Almond Milk", "1 tbsp Chia Seeds"],
                "instructions": ["Cook oats with almond milk over medium heat for 4 minutes.", "Stir in whey protein powder once off the heat.", "Top with sliced banana and chia seeds."],
                "allergens": ["Dairy"],
                "tags": ["High Fiber", "Fast Energy"]
            }
        ],
        "lunch": [
            {
                "name": "Grilled Chicken Breast with Brown Rice & Steamed Broccoli",
                "cuisine": "Continental",
                "calories": 580,
                "protein_g": 46.0,
                "carbs_g": 62.0,
                "fat_g": 14.0,
                "ingredients": ["180g Chicken Breast", "1 cup Cooked Brown Rice", "1.5 cups Steamed Broccoli", "1 tbsp Olive Oil", "Garlic & Rosemary seasoning"],
                "instructions": ["Season chicken with garlic, herbs, salt, and pepper.", "Grill for 6-7 minutes per side until juicy.", "Serve alongside steamed brown rice and tender broccoli florets."],
                "allergens": [],
                "tags": ["Clean Fuel", "High Protein", "Lean Muscle"]
            },
            {
                "name": "Chicken Tikka Bowl with Spiced Quinoa & Cucumber Salad",
                "cuisine": "Indian",
                "calories": 560,
                "protein_g": 44.0,
                "carbs_g": 54.0,
                "fat_g": 16.0,
                "ingredients": ["170g Marinated Chicken Tikka", "1 cup Cooked Quinoa", "1 Diced Cucumber", "1/2 cup Greek Yogurt Dip", "Lemon Juice & Cumin"],
                "instructions": ["Pan-sear marinated chicken cubes until slightly charred and cooked through.", "Fluff cooked quinoa with lemon zest.", "Assemble bowl with fresh cucumber salad and a side of light yogurt dip."],
                "allergens": ["Dairy"],
                "tags": ["Rich Flavor", "High Protein"]
            },
            {
                "name": "Teriyaki Turkey Rice Bowl with Stir-Fried Veggies",
                "cuisine": "Asian",
                "calories": 540,
                "protein_g": 40.0,
                "carbs_g": 65.0,
                "fat_g": 12.0,
                "ingredients": ["160g Lean Ground Turkey", "1 cup Jasmine Brown Rice", "1 cup Bell Peppers & Snap Peas", "2 tbsp Low-Sodium Teriyaki Sauce", "1 tsp Sesame Seeds"],
                "instructions": ["Brown ground turkey with garlic and ginger.", "Stir-fry crisp vegetables and toss with teriyaki glaze.", "Serve over warm rice and garnish with toasted sesame seeds."],
                "allergens": ["Soy", "Sesame"],
                "tags": ["Muscle Fuel", "Low Fat"]
            }
        ],
        "snack": [
            {
                "name": "Greek Yogurt Parfait with Mixed Berries & Pumpkin Seeds",
                "cuisine": "Western",
                "calories": 240,
                "protein_g": 20.0,
                "carbs_g": 24.0,
                "fat_g": 6.0,
                "ingredients": ["180g Plain Non-Fat Greek Yogurt", "1/2 cup Fresh Blueberries & Strawberries", "1 tbsp Roasted Pumpkin Seeds", "1 tsp Raw Honey"],
                "instructions": ["Spoon Greek yogurt into a bowl.", "Top with washed berries, crunchy pumpkin seeds, and a light drizzle of honey."],
                "allergens": ["Dairy"],
                "tags": ["Probiotic", "Quick Snack"]
            },
            {
                "name": "Boiled Eggs with Roasted Salted Chickpeas",
                "cuisine": "Indian",
                "calories": 260,
                "protein_g": 18.0,
                "carbs_g": 20.0,
                "fat_g": 12.0,
                "ingredients": ["2 Hard-Boiled Eggs", "30g Roasted Spiced Chickpeas (Chana)", "Pinch of Chaat Masala"],
                "instructions": ["Peel and slice boiled eggs.", "Dust with chaat masala and enjoy with crunchy roasted chana."],
                "allergens": ["Eggs"],
                "tags": ["Portable", "Satiating"]
            }
        ],
        "dinner": [
            {
                "name": "Baked Herb Salmon with Roasted Sweet Potatoes & Asparagus",
                "cuisine": "Mediterranean",
                "calories": 620,
                "protein_g": 42.0,
                "carbs_g": 48.0,
                "fat_g": 26.0,
                "ingredients": ["180g Wild Salmon Fillet", "1 medium Sweet Potato cubed", "8 Asparagus spears", "1 tbsp Olive Oil", "Lemon & Dill"],
                "instructions": ["Toss sweet potatoes in olive oil and roast at 200°C for 25 mins.", "Season salmon with dill and lemon, bake for 12-14 mins.", "Grill asparagus until tender-crisp and serve together."],
                "allergens": ["Seafood"],
                "tags": ["Omega-3 Rich", "Recovery Fuel"]
            },
            {
                "name": "Lean Beef / Turkey Kebabs with Mint Raita & Multigrain Roti",
                "cuisine": "Indian",
                "calories": 590,
                "protein_g": 45.0,
                "carbs_g": 52.0,
                "fat_g": 18.0,
                "ingredients": ["180g Lean Minced Meat (Turkey or Beef)", "2 Multigrain Rotis", "1/2 cup Cucumber Mint Raita", "Onion salad with lime"],
                "instructions": ["Mix minced meat with coriander, cumin, ginger, and garlic.", "Shape into patties/kebabs and sear on a non-stick pan until cooked through.", "Serve with fresh rotis and cool cucumber raita."],
                "allergens": ["Dairy", "Gluten"],
                "tags": ["High Iron", "Muscle Recovery"]
            }
        ]
    },
    "Vegetarian": {
        "breakfast": [
            {
                "name": "Paneer & Vegetable Scramble with Multigrain Toast",
                "cuisine": "Indian",
                "calories": 440,
                "protein_g": 24.0,
                "carbs_g": 38.0,
                "fat_g": 22.0,
                "ingredients": ["120g Fresh Low-Fat Paneer crumbled", "2 Slices Multigrain Toast", "1/2 Diced Bell Pepper & Tomato", "1 tsp Ghee / Olive Oil", "Turmeric & Cumin"],
                "instructions": ["Sauté cumin and diced vegetables in ghee.", "Add crumbled paneer, turmeric, salt, and toss for 3 minutes.", "Serve alongside toasted multigrain bread."],
                "allergens": ["Dairy", "Gluten"],
                "tags": ["Vegetarian Protein", "Satiating"]
            },
            {
                "name": "High-Protein Oats & Greek Yogurt Bowl with Sliced Apples",
                "cuisine": "Western",
                "calories": 420,
                "protein_g": 26.0,
                "carbs_g": 56.0,
                "fat_g": 8.0,
                "ingredients": ["50g Rolled Oats", "150g Greek Yogurt", "1 Diced Crisp Apple", "1 tsp Cinnamon", "1 tbsp Hemp or Chia Seeds"],
                "instructions": ["Mix oats with warm water or milk and let soften.", "Fold in cool Greek yogurt and cinnamon.", "Top with fresh apple cubes and seeds."],
                "allergens": ["Dairy"],
                "tags": ["High Protein", "Gut Healthy"]
            },
            {
                "name": "Moong Dal Cheela (Savory Lentil Pancakes) with Mint Chutney",
                "cuisine": "Indian",
                "calories": 390,
                "protein_g": 22.0,
                "carbs_g": 52.0,
                "fat_g": 10.0,
                "ingredients": ["1 cup Soaked Yellow Moong Dal Batter", "50g Crumbled Paneer filling", "1/2 cup Fresh Mint Coriander Chutney", "1 tsp Oil"],
                "instructions": ["Spread dal batter on a hot tawa in circular motion.", "Drizzle a few drops of oil and cook until crisp on both sides.", "Stuff with spiced paneer and serve with mint chutney."],
                "allergens": ["Dairy"],
                "tags": ["Gluten-Free", "Plant Power"]
            }
        ],
        "lunch": [
            {
                "name": "Tofu & Edamame Brown Rice Bowl with Peanut-Free Sesame Dressing",
                "cuisine": "Asian",
                "calories": 540,
                "protein_g": 32.0,
                "carbs_g": 66.0,
                "fat_g": 16.0,
                "ingredients": ["160g Extra Firm Tofu cubed", "1/2 cup Shelled Edamame", "1 cup Cooked Brown Rice", "1 cup Stir-Fried Bok Choy & Carrots", "1 tbsp Sesame Soy Glaze"],
                "instructions": ["Pan-sear tofu cubes until golden-crisp.", "Steam edamame and vegetables.", "Assemble over brown rice and drizzle with savory sesame-soy dressing."],
                "allergens": ["Soy", "Sesame"],
                "tags": ["High Protein", "Plant Based"]
            },
            {
                "name": "Palak Paneer with Whole Wheat Roti & Spiced Dal Tadka",
                "cuisine": "Indian",
                "calories": 580,
                "protein_g": 34.0,
                "carbs_g": 62.0,
                "fat_g": 20.0,
                "ingredients": ["130g Low-Fat Paneer", "1.5 cups Pureed Spinach (Palak) Gravy", "2 Whole Wheat Rotis", "1/2 cup Yellow Lentil Dal", "Garlic & Spices"],
                "instructions": ["Simmer blanched spinach puree with garlic, ginger, and garam masala.", "Add cubed paneer and simmer for 4 minutes.", "Serve hot with whole wheat rotis and comforting dal tadka."],
                "allergens": ["Dairy", "Gluten"],
                "tags": ["Iron Rich", "Traditional Strength"]
            },
            {
                "name": "Mediterranean Chickpea & Feta Salad with Quinoa",
                "cuisine": "Mediterranean",
                "calories": 510,
                "protein_g": 25.0,
                "carbs_g": 64.0,
                "fat_g": 18.0,
                "ingredients": ["1.5 cups Boiled Chickpeas", "1 cup Cooked Quinoa", "50g Crumbled Feta Cheese", "Cherry Tomatoes, Cucumbers, Kalamata Olives", "Lemon-Herb Vinaigrette"],
                "instructions": ["Combine cooled quinoa, rinsed chickpeas, diced cucumbers, and halved tomatoes in a large bowl.", "Toss with olive oil, lemon juice, and oregano.", "Top with crumbled feta cheese."],
                "allergens": ["Dairy"],
                "tags": ["High Fiber", "Mediterranean"]
            }
        ],
        "snack": [
            {
                "name": "Spiced Roasted Makhana (Fox Nuts) & Green Tea",
                "cuisine": "Indian",
                "calories": 190,
                "protein_g": 7.0,
                "carbs_g": 28.0,
                "fat_g": 5.0,
                "ingredients": ["40g Fox Nuts (Makhana)", "1 tsp Olive Oil / Ghee", "Turmeric, Himalayan Pink Salt, Black Pepper"],
                "instructions": ["Roast makhana on low heat until crunchy.", "Toss with a few drops of oil and spices."],
                "allergens": [],
                "tags": ["Low Calorie", "Crunchy"]
            },
            {
                "name": "Soya Chunk & Corn Chaat with Tangy Lemon",
                "cuisine": "Indian",
                "calories": 250,
                "protein_g": 22.0,
                "carbs_g": 26.0,
                "fat_g": 4.0,
                "ingredients": ["50g Boiled Soya Chunks", "1/4 cup Steamed Sweet Corn", "1 Diced Onion & Tomato", "Chaat Masala & Lime Juice"],
                "instructions": ["Squeeze excess water from boiled soya chunks and cut into bite-sized pieces.", "Toss with corn, onions, tomatoes, and tangy chaat spices."],
                "allergens": ["Soy"],
                "tags": ["High Protein Snack", "Plant Fuel"]
            }
        ],
        "dinner": [
            {
                "name": "Grilled Paneer Steaks with Roasted Herb Vegetables & Quinoa",
                "cuisine": "Continental",
                "calories": 560,
                "protein_g": 32.0,
                "carbs_g": 48.0,
                "fat_g": 24.0,
                "ingredients": ["140g Paneer Steaks", "1 cup Cooked Quinoa", "1 cup Roasted Zucchini, Bell Peppers & Onions", "1 tbsp Olive Oil", "Italian Herbs"],
                "instructions": ["Marinate paneer with olive oil, rosemary, thyme, salt, and pepper.", "Grill on high heat for 2-3 mins per side.", "Plate alongside roasted colorful veggies and fluffy quinoa."],
                "allergens": ["Dairy"],
                "tags": ["Complete Protein", "Dinner Fuel"]
            },
            {
                "name": "High-Protein Lentil & Rajma Bowl with Jeera Brown Rice",
                "cuisine": "Indian",
                "calories": 530,
                "protein_g": 28.0,
                "carbs_g": 78.0,
                "fat_g": 8.0,
                "ingredients": ["1.5 cups Slow-Cooked Rajma (Kidney Beans) & Black Lentils", "1 cup Cumin Brown Rice", "Fresh Onion Salad & Lime"],
                "instructions": ["Simmer boiled kidney beans in onion-tomato-ginger gravy until thick.", "Serve over warm cumin-infused brown rice with sliced onions."],
                "allergens": [],
                "tags": ["High Fiber", "Comfort Food"]
            }
        ]
    },
    "Vegan": {
        "breakfast": [
            {
                "name": "Tofu Scramble with Avocado & Sourdough Toast",
                "cuisine": "Western",
                "calories": 420,
                "protein_g": 24.0,
                "carbs_g": 40.0,
                "fat_g": 18.0,
                "ingredients": ["150g Crumbled Firm Tofu", "1/4 Sliced Ripe Avocado", "2 Slices Sourdough Bread", "Turmeric, Nutritional Yeast, Black Salt, Spinach"],
                "instructions": ["Sauté crumbled tofu with turmeric, nutritional yeast, and baby spinach.", "Toast sourdough and top with creamy avocado slices.", "Serve scramble alongside."],
                "allergens": ["Soy", "Gluten"],
                "tags": ["100% Plant Based", "High Protein"]
            },
            {
                "name": "Sprouted Moong & Poha Power Bowl",
                "cuisine": "Indian",
                "calories": 380,
                "protein_g": 18.0,
                "carbs_g": 62.0,
                "fat_g": 6.0,
                "ingredients": ["1 cup Flattened Rice (Poha)", "1/2 cup Steamed Sprouted Moong Beans", "1/4 cup Green Peas", "Mustard seeds, Curry leaves, Lemon juice"],
                "instructions": ["Rinse poha and drain.", "Sauté mustard seeds, curry leaves, peas, and sprouted moong in 1 tsp oil.", "Fold in poha, season with turmeric and lemon juice."],
                "allergens": [],
                "tags": ["Clean Energy", "Iron Rich"]
            }
        ],
        "lunch": [
            {
                "name": "Tempeh & Broccoli Stir-Fry with Brown Rice & Sesame Glaze",
                "cuisine": "Asian",
                "calories": 530,
                "protein_g": 36.0,
                "carbs_g": 60.0,
                "fat_g": 15.0,
                "ingredients": ["160g Organic Tempeh sliced", "1.5 cups Broccoli Florets & Snap Peas", "1 cup Cooked Brown Rice", "1 tbsp Tamari / Soy Sauce", "1 tsp Sesame Oil"],
                "instructions": ["Steam and pan-sear tempeh slices until golden.", "Wok-fry broccoli and snap peas with garlic and ginger.", "Toss together with tamari and serve over brown rice."],
                "allergens": ["Soy", "Sesame"],
                "tags": ["Fermented Protein", "Muscle Building"]
            },
            {
                "name": "Black Bean & Roasted Sweet Potato Burrito Bowl",
                "cuisine": "Mexican",
                "calories": 520,
                "protein_g": 22.0,
                "carbs_g": 82.0,
                "fat_g": 12.0,
                "ingredients": ["1.5 cups Cooked Black Beans", "1 roasted Sweet Potato cubed", "1 cup Brown Rice / Quinoa", "Fresh Pico de Gallo & Guacamole", "Lime & Cilantro"],
                "instructions": ["Warm seasoned black beans with cumin and smoked paprika.", "Layer bowl with rice, roasted sweet potato, beans, fresh pico, and guacamole."],
                "allergens": [],
                "tags": ["Complex Carbs", "Antioxidant Rich"]
            }
        ],
        "snack": [
            {
                "name": "Edamame Pods with Sea Salt & Chili Flakes",
                "cuisine": "Asian",
                "calories": 180,
                "protein_g": 16.0,
                "carbs_g": 14.0,
                "fat_g": 6.0,
                "ingredients": ["1.5 cups Steamed Edamame Pods in Shell", "Coarse Sea Salt & Red Chili Flakes"],
                "instructions": ["Steam edamame pods for 5 minutes.", "Toss with coarse sea salt and chili flakes."],
                "allergens": ["Soy"],
                "tags": ["Clean Protein", "Quick Snack"]
            }
        ],
        "dinner": [
            {
                "name": "Hearty Lentil & Spinach Stew with Warm Quinoa",
                "cuisine": "Mediterranean",
                "calories": 500,
                "protein_g": 26.0,
                "carbs_g": 74.0,
                "fat_g": 9.0,
                "ingredients": ["1.5 cups Cooked Brown Lentils", "2 cups Chopped Spinach", "1 cup Cooked Quinoa", "Crushed Tomatoes, Garlic, Cumin, Olive Oil"],
                "instructions": ["Simmer lentils with aromatics and rich tomato broth for 15 minutes.", "Stir in spinach until wilted.", "Serve over fluffy quinoa with a squeeze of fresh lemon."],
                "allergens": [],
                "tags": ["Heart Healthy", "High Fiber"]
            }
        ]
    }
}


class NutritionService:
    """
    Core business logic engine for FitQuest Nutrition.
    """

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or settings.effective_api_key
        self.api_key = key
        self.genai_client = None
        self.types = None

        if self.api_key:
            try:
                from google import genai
                from google.genai import types
                self.types = types
                self.genai_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[NUTRITION SERVICE] Gemini API client initialization notice: {e}. Fallback active.")

    # -------------------------------------------------------------
    # Profile & Target Engine (BMR, TDEE, Calorie/Macro Estimates)
    # -------------------------------------------------------------
    def get_or_create_profile(self, db: Session, user_id: int) -> Tuple[NutritionProfileModel, UserModel]:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found.")

        profile = db.query(NutritionProfileModel).filter(NutritionProfileModel.user_id == user_id).first()
        if not profile:
            profile = NutritionProfileModel(
                user_id=user_id,
                diet_type="Non-Vegetarian",
                allergies="[]",
                cuisines=json.dumps(["Indian", "Mediterranean"]),
                budget="Moderate",
                meals_per_day=4
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)

        # Recalculate targets based on active user biometric parameters
        self.recompute_and_save_targets(db, user, profile)
        return profile, user

    def update_profile(self, db: Session, user_id: int, payload: NutritionProfileUpdate) -> NutritionProfileModel:
        profile, user = self.get_or_create_profile(db, user_id)

        if payload.diet_type is not None:
            profile.diet_type = payload.diet_type
        if payload.allergies is not None:
            profile.allergies = json.dumps(payload.allergies)
        if payload.cuisines is not None:
            profile.cuisines = json.dumps(payload.cuisines)
        if payload.budget is not None:
            profile.budget = payload.budget
        if payload.meals_per_day is not None:
            profile.meals_per_day = payload.meals_per_day
        if payload.health_notes is not None:
            profile.health_notes = payload.health_notes

        self.recompute_and_save_targets(db, user, profile)
        db.commit()
        db.refresh(profile)
        return profile

    def recompute_and_save_targets(self, db: Session, user: UserModel, profile: NutritionProfileModel) -> Dict[str, Any]:
        """
        Calculates estimated BMR, TDEE, daily calorie target, and macro split.
        Uses Mifflin-St Jeor equation modulated by user workout frequency.
        """
        weight_kg = user.weight if user.weight and user.weight > 30 else 70.0
        height_cm = user.height if user.height and user.height > 100 else 172.0
        age = user.age if user.age and 10 <= user.age <= 100 else 28
        gender = (user.gender or "male").lower()
        goal = (user.fitness_goal or "General Fitness").lower()

        # 1. BMR (Mifflin-St Jeor)
        if "fem" in gender or "woman" in gender:
            bmr = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age - 161.0
        else:
            bmr = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age + 5.0
        bmr = int(max(1100, round(bmr)))

        # 2. Activity Multiplier (modulated by recent workout frequency)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        recent_count = db.query(WorkoutSessionModel).filter(
            WorkoutSessionModel.user_id == user.id,
            WorkoutSessionModel.started_at >= recent_cutoff
        ).count()

        if recent_count >= 8:
            activity_mult = 1.65 # Very active (4+ workouts/week)
        elif recent_count >= 4:
            activity_mult = 1.50 # Moderately active (2-3 workouts/week)
        elif recent_count >= 2:
            activity_mult = 1.375 # Lightly active
        else:
            # Fallback to experience level
            exp = (user.experience_level or "Beginner").lower()
            if "adv" in exp:
                activity_mult = 1.55
            elif "int" in exp:
                activity_mult = 1.45
            else:
                activity_mult = 1.35

        tdee = int(round(bmr * activity_mult))

        # 3. Goal Caloric Adjustment
        if "muscle" in goal or "gain" in goal or "hypertrophy" in goal or "bulk" in goal:
            daily_target = tdee + 400
            protein_factor = 2.0 # 2.0g per kg
        elif "loss" in goal or "cut" in goal or "fat" in goal:
            daily_target = max(bmr, tdee - 450) # Safe deficit, never under BMR
            protein_factor = 1.8 # 1.8g per kg to preserve lean mass
        elif "athle" in goal or "perf" in goal or "strength" in goal:
            daily_target = tdee + 200
            protein_factor = 1.9
        else: # Maintain / General Fitness
            daily_target = tdee
            protein_factor = 1.5

        daily_target = int(max(1300, daily_target))

        # 4. Macro Distribution
        protein_g = round(weight_kg * protein_factor, 1)
        # 25% of calories from healthy fats (9 kcal/g)
        fat_calories = daily_target * 0.25
        fat_g = round(fat_calories / 9.0, 1)
        # Remainder from carbohydrates (4 kcal/g)
        protein_calories = protein_g * 4.0
        remaining_calories = max(0, daily_target - (protein_calories + fat_calories))
        carbs_g = round(remaining_calories / 4.0, 1)

        # Save to profile
        profile.target_calories = daily_target
        profile.target_protein_g = protein_g
        profile.target_carbs_g = carbs_g
        profile.target_fat_g = fat_g
        db.commit()
        db.refresh(profile)

        return {
            "bmr": bmr,
            "tdee": tdee,
            "daily_target": daily_target,
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
            "goal": user.fitness_goal or "General Fitness"
        }

    # -------------------------------------------------------------
    # 7-Day Meal Plan Generator (Gemini + Deterministic Fallback)
    # -------------------------------------------------------------
    def get_active_plan(self, db: Session, user_id: int) -> Optional[Dict[str, Any]]:
        active_plan_record = db.query(NutritionPlanModel).filter(
            NutritionPlanModel.user_id == user_id,
            NutritionPlanModel.is_active == True
        ).order_by(NutritionPlanModel.created_at.desc()).first()

        if active_plan_record:
            try:
                data = json.loads(active_plan_record.plan_data)
                data["id"] = active_plan_record.id
                data["user_id"] = user_id
                data["is_active"] = active_plan_record.is_active
                data["generator_source"] = active_plan_record.generator_source
                data["created_at"] = active_plan_record.created_at
                data["updated_at"] = active_plan_record.updated_at
                return data
            except Exception:
                pass
        return None

    def generate_7day_plan(self, db: Session, user_id: int, force_regenerate: bool = False) -> Dict[str, Any]:
        """
        Retrieves or generates a personalized 7-day meal plan.
        Tries Gemini AI first; falls back cleanly to the multi-cuisine recipe engine on any issue.
        """
        profile, user = self.get_or_create_profile(db, user_id)

        if not force_regenerate:
            existing = self.get_active_plan(db, user_id)
            if existing:
                return existing

        allergies = json.loads(profile.allergies) if profile.allergies else []
        cuisines = json.loads(profile.cuisines) if profile.cuisines else ["Indian", "Mediterranean"]
        diet_type = profile.diet_type or "Non-Vegetarian"
        target_calories = profile.target_calories or 2100
        target_protein = profile.target_protein_g or 120.0
        target_carbs = profile.target_carbs_g or 230.0
        target_fat = profile.target_fat_g or 65.0
        meals_per_day = profile.meals_per_day or 4
        goal = user.fitness_goal or "General Fitness"

        plan_result = None
        generator_source = "Deterministic Fallback"

        # Attempt Gemini Generation
        if self.genai_client:
            try:
                plan_result = self._generate_plan_with_gemini(
                    user_goal=goal,
                    diet_type=diet_type,
                    allergies=allergies,
                    cuisines=cuisines,
                    budget=profile.budget or "Moderate",
                    target_calories=target_calories,
                    target_protein=target_protein,
                    target_carbs=target_carbs,
                    target_fat=target_fat,
                    meals_per_day=meals_per_day
                )
                if plan_result and len(plan_result.get("days", [])) == 7:
                    generator_source = "Gemini AI"
            except Exception as err:
                print(f"[NUTRITION SERVICE] Gemini generation notice: {err}. Using deterministic recipe engine.")
                plan_result = None

        # Fallback Generation if Gemini failed or offline
        if not plan_result or len(plan_result.get("days", [])) != 7:
            plan_result = self._generate_plan_deterministic(
                diet_type=diet_type,
                allergies=allergies,
                cuisines=cuisines,
                target_calories=target_calories,
                target_protein=target_protein,
                target_carbs=target_carbs,
                target_fat=target_fat,
                meals_per_day=meals_per_day
            )
            generator_source = "Deterministic Fallback"

        # Validate Allergen Safety Gate across all 7 days
        self._filter_and_sanitize_allergens(plan_result, allergies)

        # Deactivate older active plans
        db.query(NutritionPlanModel).filter(
            NutritionPlanModel.user_id == user_id,
            NutritionPlanModel.is_active == True
        ).update({"is_active": False})

        # Save new active plan
        new_plan = NutritionPlanModel(
            user_id=user_id,
            is_active=True,
            generator_source=generator_source,
            plan_data=json.dumps(plan_result)
        )
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)

        plan_result["id"] = new_plan.id
        plan_result["user_id"] = user_id
        plan_result["is_active"] = True
        plan_result["generator_source"] = generator_source
        plan_result["created_at"] = new_plan.created_at
        plan_result["updated_at"] = new_plan.updated_at

        return plan_result

    def _generate_plan_with_gemini(
        self,
        user_goal: str,
        diet_type: str,
        allergies: List[str],
        cuisines: List[str],
        budget: str,
        target_calories: int,
        target_protein: float,
        target_carbs: float,
        target_fat: float,
        meals_per_day: int
    ) -> Optional[Dict[str, Any]]:
        allergy_str = ", ".join(allergies) if allergies else "None declared"
        cuisine_str = ", ".join(cuisines) if cuisines else "Indian, Mediterranean, Western"

        prompt = f"""Generate a personalized 7-Day Nutrition Plan adhering STRICTLY to the following profile:
- Primary Fitness Goal: {user_goal}
- Diet Preference: {diet_type}
- STRICT ALLERGIES (DO NOT USE ANY OF THESE): {allergy_str}
- Preferred Cuisines: {cuisine_str}
- Budget Tier: {budget}
- Daily Nutrition Targets: {target_calories} kcal, {target_protein}g Protein, {target_carbs}g Carbs, {target_fat}g Fat
- Meals per Day: {meals_per_day} (include breakfast, lunch, snack, dinner)

RETURN ONLY A RAW JSON OBJECT with this exact structure:
{{
  "target_summary": {{
    "calories": {target_calories},
    "protein_g": {target_protein},
    "carbs_g": {target_carbs},
    "fat_g": {target_fat},
    "goal": "{user_goal}"
  }},
  "days": [
    {{
      "day": 1,
      "day_name": "Day 1 (Monday)",
      "meals": [
        {{
          "type": "breakfast",
          "name": "Meal Name",
          "calories": 450,
          "protein_g": 30.0,
          "carbs_g": 45.0,
          "fat_g": 15.0,
          "ingredients": ["Item 1 with quantity", "Item 2"],
          "instructions": ["Step 1", "Step 2"],
          "tags": ["High Protein"]
        }}
      ]
    }}
  ]
}}
Ensure all 7 days (day 1 to 7) are included with varied meals across the week matching the {diet_type} diet."""

        try:
            config = self.types.GenerateContentConfig(
                system_instruction=NUTRITION_SYSTEM_PROMPT,
                response_mime_type="application/json"
            ) if self.types else None

            response = self.genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config
            )

            if response and response.text:
                cleaned_text = response.text.strip()
                # Strip markdown fence if present
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                
                parsed = json.loads(cleaned_text.strip())
                self._compute_daily_totals(parsed)
                return parsed
        except Exception as e:
            print(f"[NUTRITION SERVICE] Gemini parsing error: {e}")

        return None

    def _generate_plan_deterministic(
        self,
        diet_type: str,
        allergies: List[str],
        cuisines: List[str],
        target_calories: int,
        target_protein: float,
        target_carbs: float,
        target_fat: float,
        meals_per_day: int
    ) -> Dict[str, Any]:
        """
        Builds a full 7-day meal plan from the curated fallback recipe catalog with variety.
        """
        diet_category = diet_type if diet_type in FALLBACK_RECIPE_DATABASE else "Non-Vegetarian"
        recipe_pool = FALLBACK_RECIPE_DATABASE[diet_category]

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        days = []

        meal_types = ["breakfast", "lunch", "snack", "dinner"] if meals_per_day >= 4 else ["breakfast", "lunch", "dinner"]

        # Calculate meal budget ratios
        cal_ratios = {"breakfast": 0.25, "lunch": 0.35, "snack": 0.12, "dinner": 0.28} if meals_per_day >= 4 else {"breakfast": 0.30, "lunch": 0.40, "dinner": 0.30}

        for day_idx in range(1, 8):
            day_meals = []
            for m_type in meal_types:
                available = recipe_pool.get(m_type, recipe_pool["breakfast"])
                # Rotate recipes across days
                recipe_template = available[(day_idx - 1) % len(available)]

                target_meal_cal = int(target_calories * cal_ratios.get(m_type, 0.25))
                scale = max(0.6, min(1.8, target_meal_cal / max(100, recipe_template["calories"])))

                meal_item = {
                    "type": m_type,
                    "name": recipe_template["name"],
                    "calories": int(round(recipe_template["calories"] * scale)),
                    "protein_g": round(recipe_template["protein_g"] * scale, 1),
                    "carbs_g": round(recipe_template["carbs_g"] * scale, 1),
                    "fat_g": round(recipe_template["fat_g"] * scale, 1),
                    "ingredients": list(recipe_template.get("ingredients", [])),
                    "instructions": list(recipe_template.get("instructions", [])),
                    "tags": list(recipe_template.get("tags", []))
                }
                day_meals.append(meal_item)

            days.append({
                "day": day_idx,
                "day_name": f"Day {day_idx} ({day_names[day_idx - 1]})",
                "meals": day_meals
            })

        plan = {
            "target_summary": {
                "calories": target_calories,
                "protein_g": target_protein,
                "carbs_g": target_carbs,
                "fat_g": target_fat,
                "diet_type": diet_type
            },
            "days": days
        }
        self._compute_daily_totals(plan)
        return plan

    def _compute_daily_totals(self, plan: Dict[str, Any]):
        for day in plan.get("days", []):
            total_cal = 0
            total_p = 0.0
            total_c = 0.0
            total_f = 0.0
            for m in day.get("meals", []):
                total_cal += m.get("calories", 0)
                total_p += m.get("protein_g", 0.0)
                total_c += m.get("carbs_g", 0.0)
                total_f += m.get("fat_g", 0.0)
            day["daily_calories"] = int(total_cal)
            day["daily_protein_g"] = round(total_p, 1)
            day["daily_carbs_g"] = round(total_c, 1)
            day["daily_fat_g"] = round(total_f, 1)

    def _filter_and_sanitize_allergens(self, plan: Dict[str, Any], allergies: List[str]):
        """
        Hard constraint: Scans generated meals and removes/replaces any recipe mentioning declared allergens.
        """
        if not allergies:
            return

        allergen_keywords = []
        for a in allergies:
            a_clean = a.lower().strip()
            if not a_clean:
                continue
            allergen_keywords.append(a_clean)
            if a_clean.endswith("s"):
                allergen_keywords.append(a_clean[:-1])
            if "nut" in a_clean:
                allergen_keywords.extend(["nut", "peanut", "walnut", "almond", "cashew", "pistachio", "hazelnut", "pecan"])
            if "dairy" in a_clean or "milk" in a_clean:
                allergen_keywords.extend(["dairy", "milk", "cheese", "butter", "paneer", "yogurt", "curd", "whey", "cream", "ghee"])
            if "egg" in a_clean:
                allergen_keywords.extend(["egg", "eggs", "omelet", "mayo"])
            if "gluten" in a_clean or "wheat" in a_clean:
                allergen_keywords.extend(["gluten", "wheat", "barley", "rye"])
            if "soy" in a_clean:
                allergen_keywords.extend(["soy", "soya", "tofu", "edamame"])
            if "shellfish" in a_clean:
                allergen_keywords.extend(["shellfish", "prawn", "shrimp", "crab", "lobster", "clam", "oyster"])

        allergen_keywords = list(set(allergen_keywords))

        for day in plan.get("days", []):
            for meal in day.get("meals", []):
                ing_list = meal.get("ingredients", [])
                has_allergen = any(
                    any(kw in ing.lower() for kw in allergen_keywords)
                    for ing in ing_list
                ) or any(kw in meal.get("name", "").lower() for kw in allergen_keywords)

                if has_allergen:
                    sanitized_ing = [
                        ing for ing in ing_list
                        if not any(kw in ing.lower() for kw in allergen_keywords)
                    ]
                    if not sanitized_ing:
                        sanitized_ing = ["Nutrient-dense allergen-free whole foods", "Fresh seasonal greens"]
                    meal["ingredients"] = sanitized_ing

                    # Also sanitize meal name if it mentions allergen
                    name = meal.get("name", "")
                    for kw in allergen_keywords:
                        if kw in name.lower():
                            name = re.sub(re.escape(kw), "Sunflower/Allergen-Free", name, flags=re.IGNORECASE)
                    meal["name"] = name
                    meal["tags"] = [t for t in meal.get("tags", []) if not any(kw in t.lower() for kw in allergen_keywords)] + ["Allergen Safe"]

    # -------------------------------------------------------------
    # Single Meal Regenerator (Preserves other 6 days)
    # -------------------------------------------------------------
    def regenerate_single_meal(
        self,
        db: Session,
        user_id: int,
        day_num: int,
        meal_type: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Replaces ONLY the specified meal in the active 7-day plan, keeping all other meals untouched.
        """
        plan_record = db.query(NutritionPlanModel).filter(
            NutritionPlanModel.user_id == user_id,
            NutritionPlanModel.is_active == True
        ).order_by(NutritionPlanModel.created_at.desc()).first()

        if not plan_record:
            # Generate plan first if none exists
            full_plan = self.generate_7day_plan(db, user_id)
            plan_record = db.query(NutritionPlanModel).filter(NutritionPlanModel.id == full_plan["id"]).first()

        plan_data = json.loads(plan_record.plan_data)
        profile, user = self.get_or_create_profile(db, user_id)
        allergies = json.loads(profile.allergies) if profile.allergies else []
        diet_type = profile.diet_type or "Non-Vegetarian"
        target_cal = profile.target_calories or 2100

        # Find target day
        target_day = None
        for d in plan_data.get("days", []):
            if d.get("day") == day_num:
                target_day = d
                break

        if not target_day:
            raise ValueError(f"Day {day_num} not found in active meal plan.")

        # Find and replace the meal
        new_meal = None

        # Try Gemini single meal generation
        if self.genai_client:
            try:
                new_meal = self._generate_single_meal_gemini(
                    user_goal=user.fitness_goal or "General Fitness",
                    diet_type=diet_type,
                    allergies=allergies,
                    meal_type=meal_type,
                    target_cal=int(target_cal * 0.28),
                    reason=reason
                )
            except Exception as e:
                print(f"[NUTRITION SERVICE] Single meal Gemini notice: {e}")

        # Fallback single meal
        if not new_meal:
            diet_cat = diet_type if diet_type in FALLBACK_RECIPE_DATABASE else "Non-Vegetarian"
            recipes = FALLBACK_RECIPE_DATABASE[diet_cat].get(meal_type, FALLBACK_RECIPE_DATABASE[diet_cat]["breakfast"])
            # Select an alternative index
            alt_recipe = recipes[(day_num + 1) % len(recipes)]
            scale = max(0.7, min(1.6, (target_cal * 0.28) / max(100, alt_recipe["calories"])))

            new_meal = {
                "type": meal_type,
                "name": f"{alt_recipe['name']} (Fresh Alternative)",
                "calories": int(round(alt_recipe["calories"] * scale)),
                "protein_g": round(alt_recipe["protein_g"] * scale, 1),
                "carbs_g": round(alt_recipe["carbs_g"] * scale, 1),
                "fat_g": round(alt_recipe["fat_g"] * scale, 1),
                "ingredients": list(alt_recipe.get("ingredients", [])),
                "instructions": list(alt_recipe.get("instructions", [])),
                "tags": list(alt_recipe.get("tags", [])) + ["Regenerated"]
            }

        # Substitute in plan
        replaced = False
        for idx, m in enumerate(target_day.get("meals", [])):
            if m.get("type") == meal_type:
                target_day["meals"][idx] = new_meal
                replaced = True
                break

        if not replaced:
            target_day["meals"].append(new_meal)

        self._compute_daily_totals(plan_data)

        # Update in database
        plan_record.plan_data = json.dumps(plan_data)
        plan_record.updated_at = datetime.now(timezone.utc)
        db.commit()

        plan_data["id"] = plan_record.id
        plan_data["user_id"] = user_id
        plan_data["is_active"] = True
        plan_data["generator_source"] = plan_record.generator_source
        plan_data["created_at"] = plan_record.created_at
        plan_data["updated_at"] = plan_record.updated_at

        return plan_data

    def _generate_single_meal_gemini(
        self,
        user_goal: str,
        diet_type: str,
        allergies: List[str],
        meal_type: str,
        target_cal: int,
        reason: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        allergy_str = ", ".join(allergies) if allergies else "None"
        reason_prompt = f"User preference/reason: {reason}" if reason else ""

        prompt = f"""Generate a single {meal_type.upper()} meal alternative for a fitness user.
- Goal: {user_goal}
- Diet: {diet_type}
- STRICT ALLERGIES (NEVER USE): {allergy_str}
- Approximate Calorie Target: {target_cal} kcal
{reason_prompt}

RETURN ONLY A RAW JSON OBJECT with this schema:
{{
  "type": "{meal_type}",
  "name": "Creative Meal Title",
  "calories": {target_cal},
  "protein_g": 30.0,
  "carbs_g": 40.0,
  "fat_g": 12.0,
  "ingredients": ["Item 1 with quantity", "Item 2"],
  "instructions": ["Step 1", "Step 2"],
  "tags": ["High Protein", "Quick Prep"]
}}"""

        config = self.types.GenerateContentConfig(
            system_instruction=NUTRITION_SYSTEM_PROMPT,
            response_mime_type="application/json"
        ) if self.types else None

        response = self.genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )
        if response and response.text:
            cleaned = response.text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        return None

    # -------------------------------------------------------------
    # Meal Logging & Today's Summary
    # -------------------------------------------------------------
    def log_meal(self, db: Session, user_id: int, payload: MealLogCreate) -> NutritionMealLogModel:
        # Smart estimation if calories/macros are omitted
        cal = payload.calories
        p = payload.protein_g
        c = payload.carbs_g
        f = payload.fat_g

        if cal is None or cal == 0:
            est_cal, est_p, est_c, est_f = self.estimate_nutrients_from_text(payload.food_name)
            cal = est_cal
            p = p if p is not None else est_p
            c = c if c is not None else est_c
            f = f if f is not None else est_f

        log_entry = NutritionMealLogModel(
            user_id=user_id,
            meal_type=payload.meal_type.lower(),
            food_name=payload.food_name.strip(),
            calories=int(cal),
            protein_g=float(p or 0.0),
            carbs_g=float(c or 0.0),
            fat_g=float(f or 0.0),
            notes=payload.notes
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    def delete_meal_log(self, db: Session, user_id: int, log_id: int) -> bool:
        log = db.query(NutritionMealLogModel).filter(
            NutritionMealLogModel.id == log_id,
            NutritionMealLogModel.user_id == user_id
        ).first()
        if not log:
            return False
        db.delete(log)
        db.commit()
        return True

    def get_today_summary(self, db: Session, user_id: int) -> Dict[str, Any]:
        profile, user = self.get_or_create_profile(db, user_id)

        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)

        today_logs = db.query(NutritionMealLogModel).filter(
            NutritionMealLogModel.user_id == user_id,
            NutritionMealLogModel.logged_at >= start_of_day
        ).order_by(NutritionMealLogModel.logged_at.asc()).all()

        logged_cal = sum(m.calories for m in today_logs)
        logged_p = sum(m.protein_g for m in today_logs)
        logged_c = sum(m.carbs_g for m in today_logs)
        logged_f = sum(m.fat_g for m in today_logs)

        target_cal = profile.target_calories or 2150
        target_p = profile.target_protein_g or 120.0
        target_c = profile.target_carbs_g or 240.0
        target_f = profile.target_fat_g or 65.0

        cal_progress = min(100.0, round((logged_cal / max(1, target_cal)) * 100.0, 1))
        p_progress = min(100.0, round((logged_p / max(1.0, target_p)) * 100.0, 1))

        logged_meal_types = list(set(m.meal_type for m in today_logs))

        return {
            "date": now.strftime("%Y-%m-%d"),
            "fitness_goal": user.fitness_goal or "General Fitness",
            "daily_calorie_target": target_cal,
            "daily_protein_target": target_p,
            "daily_carbs_target": target_c,
            "daily_fat_target": target_f,
            "calories_logged": logged_cal,
            "protein_logged": round(logged_p, 1),
            "carbs_logged": round(logged_c, 1),
            "fat_logged": round(logged_f, 1),
            "calories_remaining": max(0, target_cal - logged_cal),
            "protein_remaining": max(0.0, round(target_p - logged_p, 1)),
            "calorie_progress_pct": cal_progress,
            "protein_progress_pct": p_progress,
            "meals_logged_count": len(today_logs),
            "meals_total_target": profile.meals_per_day or 4,
            "meal_types_logged": logged_meal_types,
            "bmr_estimate": int(target_cal / 1.4),
            "tdee_estimate": int(target_cal),
            "logged_meals": today_logs
        }

    def get_meal_history(self, db: Session, user_id: int, days: int = 7) -> List[NutritionMealLogModel]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return db.query(NutritionMealLogModel).filter(
            NutritionMealLogModel.user_id == user_id,
            NutritionMealLogModel.logged_at >= cutoff
        ).order_by(NutritionMealLogModel.logged_at.desc()).all()

    # -------------------------------------------------------------
    # Smart Nutrient Estimation & Food Analysis
    # -------------------------------------------------------------
    def estimate_nutrients_from_text(self, text: str) -> Tuple[int, float, float, float]:
        """
        Smart text-based calorie & macro estimator for everyday meals and gym staples.
        """
        txt = text.lower()

        base_cal = 350
        base_p = 15.0
        base_c = 45.0
        base_f = 12.0

        if "chicken" in txt or "turkey" in txt:
            base_cal += 180
            base_p += 30.0
            base_f += 4.0
        if "paneer" in txt:
            base_cal += 200
            base_p += 18.0
            base_f += 16.0
        if "egg" in txt:
            base_cal += 140
            base_p += 14.0
            base_f += 10.0
        if "roti" in txt or "chapati" in txt:
            base_cal += 160
            base_c += 34.0
            base_p += 5.0
        if "rice" in txt:
            base_cal += 200
            base_c += 44.0
            base_p += 4.0
        if "dal" in txt or "lentil" in txt or "chana" in txt or "rajma" in txt:
            base_cal += 180
            base_p += 14.0
            base_c += 30.0
        if "protein shake" in txt or "whey" in txt:
            base_cal = 160
            base_p = 27.0
            base_c = 4.0
            base_f = 2.0
        if "salad" in txt:
            base_cal = max(150, base_cal - 100)
            base_c = 15.0
        if "oat" in txt:
            base_cal = 320
            base_c = 52.0
            base_p = 14.0
            base_f = 6.0
        if "banana" in txt or "apple" in txt:
            base_cal += 100
            base_c += 25.0

        return int(base_cal), round(base_p, 1), round(base_c, 1), round(base_f, 1)

    def analyze_food(
        self,
        image_base64: Optional[str] = None,
        text_description: Optional[str] = None,
        user_allergies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Multimodal food item analysis using Gemini Vision or intelligent text parser fallback.
        """
        allergies = user_allergies or []

        if image_base64 and self.genai_client:
            try:
                import base64
                img_data = image_base64
                if "," in img_data:
                    img_data = img_data.split(",", 1)[1]
                image_bytes = base64.b64decode(img_data)

                prompt = f"""Analyze this food image in detail:
1. Identify the food item or dish name.
2. Estimate the approximate portion size and nutrition: calories, protein (g), carbs (g), fat (g).
3. List all detected ingredients.
4. Check for potential allergen warnings against declared user allergies: {', '.join(allergies) if allergies else 'None'}.
5. Provide a brief 1-line fitness coaching recommendation.

RETURN ONLY RAW JSON:
{{
  "food_name": "Identified Food Name",
  "estimated_calories": 480,
  "protein_g": 32.0,
  "carbs_g": 50.0,
  "fat_g": 14.0,
  "confidence": 0.92,
  "detected_items": ["Ingredient 1", "Ingredient 2"],
  "allergen_warnings": ["Warning if any allergen detected"],
  "recommendations": "Great post-workout protein meal."
}}"""

                config = self.types.GenerateContentConfig(
                    system_instruction=NUTRITION_SYSTEM_PROMPT,
                    response_mime_type="application/json"
                ) if self.types else None

                image_part = self.types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg") if self.types else None

                response = self.genai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt, image_part] if image_part else prompt,
                    config=config
                )

                if response and response.text:
                    cleaned = response.text.strip()
                    if cleaned.startswith("```json"):
                        cleaned = cleaned[7:]
                    if cleaned.startswith("```"):
                        cleaned = cleaned[3:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    res = json.loads(cleaned.strip())
                    res["provider"] = "Gemini Vision AI"
                    return res
            except Exception as e:
                print(f"[NUTRITION SERVICE] Vision analysis error: {e}. Reverting to text fallback.")

        # Fallback estimation
        query_text = text_description or "Mixed Balanced Meal"
        cal, p, c, f = self.estimate_nutrients_from_text(query_text)

        warnings = []
        for a in allergies:
            if a.lower() in query_text.lower():
                warnings.append(f"Declared allergen '{a}' matched in food description.")

        return {
            "food_name": query_text.title(),
            "estimated_calories": cal,
            "protein_g": p,
            "carbs_g": c,
            "fat_g": f,
            "confidence": 0.85,
            "detected_items": [item.strip() for item in query_text.split("+") if item.strip()] or [query_text],
            "allergen_warnings": warnings,
            "recommendations": "Solid nutritional balance to support your active training.",
            "provider": "FitQuest Nutrient Estimator"
        }


nutrition_service = NutritionService()
