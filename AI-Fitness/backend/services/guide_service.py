"""
FitQuest Guide™ Service
Dedicated in-app platform help assistant for explaining features, metrics, and navigation.
Separated strictly from the AI Coach.
"""

import os
import re
from typing import Optional, Dict, Any, List, Tuple
from backend.config import settings

GUIDE_SYSTEM_PROMPT = """You are FitQuest Guide™, the official in-app help assistant for the FitQuest platform.

Your ONLY purpose is to help users understand, explore, and navigate the FitQuest application.
You explain actual FitQuest features, user interface controls, navigation, and metrics.

ACTUAL FITQUEST FEATURES & KNOWLEDGE BASE:
1. Dashboard (Home / "homeView"):
   - Displays Training Readiness Score (0-100 gauge with fatigue and recovery recommendations).
   - Acute & Chronic Training Load (ACWR - Acute:Chronic Workload Ratio, sweet spot 0.8-1.3).
   - Personalized Active Goals (Weekly workouts, Form mastery targets, Calorie targets, Volume).
   - Gamification & Streaks (Current streak, Longest streak, XP, Level, Badges & Achievements).
   - Quick action shortcuts to start workouts, open Movement DNA, or log nutrition.

2. Workout ("workoutView"):
   - Step A: Exercise Catalogue (Squats, Push-ups, Lunges, Bicep Curls, Dumbbell Rows, Planks, Jumping Jacks, etc.).
   - Step B: Customization & Adaptive Mode (Rep targets, Set counts, Rest timer duration, AI Pose Correction toggle, Movement Copilot toggle, Adaptive dynamic load).
   - Step C: Live Real-Time Workout Runner with Dual Viewports (3D/2D Animated Skeleton Demo Guide + Live Camera with YOLOv8 Pose Landmark Tracking), Live HUD with Rep Counter, Form Score (0-100%), Biomechanical Joint Angles, Audio & Visual Form Cues, and Movement Copilot live in-set micro-corrections.
   - Step D: Post-Workout Performance Results, AI Coach Biomechanical Feedback breakdown, Movement DNA instant update, Copilot session summary, and Gamification XP/streak toast.

3. Movement DNA™ ("movementDnaView"):
   - Biomechanical movement fingerprint analyzing 6 core dimensions: Stability, Symmetry, Range of Motion, Velocity Control / Tempo, Postural Integrity, and Consistency.
   - Identifies the user's primary movement limiter (e.g. Torso Stability under load, Left/Right knee asymmetry).
   - Longitudinal movement quality evolution timeline chart with custom corrective drills.

4. Adaptive AI ("adaptiveTrainingView"):
   - Real-time training intelligence that auto-regulates sets, reps, weight volume, and difficulty based on fatigue accumulation, form thresholds, Readiness score, and Movement DNA limiters.

5. Movement Copilot™:
   - Real-time in-set coaching engine during active workouts that monitors intra-set cadence, rep velocity, joint angles, and provides instant audio/visual micro-cues to fix faults before failed reps.

6. Evolution ("evolutionView"):
   - Longitudinal progress tracking of movement quality and physical adaptation over weeks and months with radar shifts and quality score trajectories.

7. Analytics ("progressView"):
   - Interactive performance dashboard with charts for volume progression, form quality trends over time, muscle group distribution, and frequency heatmaps across 7d/30d/90d/all time.

8. Nutrition ("nutritionView"):
   - Personalized AI-powered nutrition and diet recommendation module tailored to the user's fitness goal.
   - Today's Nutrition summary with daily calorie target, protein target, and meals logged progress.
   - Personalized 7-Day Meal Plan with expandable recipe cards (ingredients, instructions, macros).
   - Single-meal regeneration button preserving the rest of the plan.
   - Quick Meal Logger to record eaten food and track remaining calories.
   - Nutrition Preferences & Allergies area (Diet style, allergens, preferred cuisines, budget).
   - Food Analyzer for image-based nutrient estimation.

9. AI Coach ("aiCoachView"):
   - Personal AI fitness coach & biomechanics specialist handling workout programming, exercise technique, and general fitness Q&A.

10. History ("historyView"):
    - Chronological log of all completed workouts with dates, reps, duration, form scores, calories, and performance notes.

11. Navigation System:
    - Main tabs: Dashboard (homeView), Workout (workoutView), Nutrition (nutritionView), Movement DNA™ (movementDnaView), Adaptive AI (adaptiveTrainingView), Evolution (evolutionView), Analytics (progressView), AI Coach (aiCoachView), History (historyView).
    - Account dropdown in top right for profile settings.

STRICT SCOPE & BOUNDARIES:
- You are NOT the AI Coach. Do NOT give direct medical diagnoses or personalized workout prescriptions. Explain how to use the FitQuest features and direct users to appropriate tabs.
- If asked unrelated/general knowledge questions (e.g., weather, politics, programming code, jokes, celebrities), politely explain that you are specifically the FitQuest platform help assistant.
- Never invent features, buttons, or capabilities that do not exist in FitQuest. Use the exact terminology of the app.
- Keep responses clear, concise, friendly, and structured.
"""

VIEW_NAME_MAP = {
    "homeView": "Dashboard (Home)",
    "workoutView": "Workout Experience",
    "nutritionView": "Nutrition",
    "movementDnaView": "Movement DNA™",
    "adaptiveTrainingView": "Adaptive AI",
    "evolutionView": "Evolution",
    "progressView": "Analytics",
    "aiCoachView": "AI Coach",
    "historyView": "History",
    "profileModal": "User Profile"
}

NAV_TRIGGER_MAP = {
    "dashboard": "homeView",
    "home": "homeView",
    "workout": "workoutView",
    "workouts": "workoutView",
    "exercise": "workoutView",
    "nutrition": "nutritionView",
    "diet": "nutritionView",
    "meal plan": "nutritionView",
    "meal": "nutritionView",
    "meals": "nutritionView",
    "food": "nutritionView",
    "movement dna": "movementDnaView",
    "dna": "movementDnaView",
    "adaptive ai": "adaptiveTrainingView",
    "adaptive": "adaptiveTrainingView",
    "evolution": "evolutionView",
    "analytics": "progressView",
    "progress": "progressView",
    "charts": "progressView",
    "ai coach": "aiCoachView",
    "coach": "aiCoachView",
    "history": "historyView"
}


class FitQuestGuideService:
    """
    Service layer providing dedicated in-app platform help and navigation assistance.
    """
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        cleaned_key = api_key.strip() if api_key and isinstance(api_key, str) else None
        self.api_key = cleaned_key or settings.effective_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model_name = model_name
        self.genai_client = None
        self.types = None

        if self.api_key:
            try:
                from google import genai
                from google.genai import types
                self.types = types
                self.genai_client = genai.Client(api_key=self.api_key)
                print(f"[INFO] FitQuest Guide initialized with Gemini API ({self.model_name}).")
            except ImportError:
                print("[INFO] google-genai SDK not found. FitQuest Guide running in Rule-Based Mode.")
            except Exception as e:
                print(f"[WARNING] FitQuest Guide could not initialize Gemini API: {e}. Running in Rule-Based Mode.")

    def process_guide_query(
        self,
        message: str,
        current_view: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Processes a user query to FitQuest Guide.
        Returns a dictionary with reply, nav_suggestion, nav_action, and provider.
        """
        msg_clean = message.strip()
        msg_lower = msg_clean.lower()

        # Check navigation intent
        nav_action = self._detect_navigation_intent(msg_lower)
        nav_suggestion = self._detect_navigation_suggestion(msg_lower, current_view)

        # Check AI Coach redirection (Fitness coaching question)
        if self._is_fitness_coaching_query(msg_lower):
            return {
                "reply": (
                    "That's a fitness coaching question! **FitQuest AI Coach** is designed specifically "
                    "to help you with workout programming, exercise technique, nutrition, and recovery.\n\n"
                    "You can open the **AI Coach** tab from the top navigation menu to ask your question."
                ),
                "nav_suggestion": "aiCoachView",
                "nav_action": None,
                "provider": "FitQuest Guide Scope Gate"
            }

        # Check general off-topic query (out of domain)
        if self._is_out_of_domain_query(msg_lower):
            return {
                "reply": (
                    "I am **FitQuest Guide™**, your in-app assistant for understanding and navigating the "
                    "FitQuest platform.\n\n"
                    "I can explain any FitQuest feature, including **Workouts**, **Movement DNA™**, "
                    "**BODY SIM™**, **Adaptive AI**, **Movement Copilot**, **Analytics**, and **History**! "
                    "How can I help you with FitQuest today?"
                ),
                "nav_suggestion": None,
                "nav_action": None,
                "provider": "FitQuest Guide Scope Gate"
            }

        # If Gemini client is active, try generating a response
        if self.genai_client:
            try:
                active_view_name = VIEW_NAME_MAP.get(current_view, current_view or "Dashboard")
                user_prompt = f"Current Active View in FitQuest: {active_view_name} (ID: {current_view})\n\nUser Question: {msg_clean}"
                
                config = self.types.GenerateContentConfig(
                    system_instruction=GUIDE_SYSTEM_PROMPT,
                    temperature=0.2,
                    max_output_tokens=600
                )
                response = self.genai_client.models.generate_content(
                    model=self.model_name,
                    contents=user_prompt,
                    config=config
                )
                if response and response.text:
                    reply_text = response.text.strip()
                    return {
                        "reply": reply_text,
                        "nav_suggestion": nav_suggestion,
                        "nav_action": nav_action,
                        "provider": "Gemini (FitQuest Guide)"
                    }
            except Exception as e:
                print(f"[WARNING] FitQuest Guide Gemini call failed: {e}. Falling back to Rule-Based Knowledge Engine.")

        # Deterministic Knowledge Engine Fallback
        reply_text = self._rule_based_guide_qa(msg_clean, msg_lower, current_view)
        return {
            "reply": reply_text,
            "nav_suggestion": nav_suggestion or nav_action,
            "nav_action": nav_action,
            "provider": "FitQuest Guide Knowledge Engine"
        }

    def _detect_navigation_intent(self, text: str) -> Optional[str]:
        """Detects if user explicitly requests to go to/open a specific section."""
        nav_verbs = ["go to", "take me to", "open", "navigate to", "switch to", "show me"]
        for verb in nav_verbs:
            if verb in text:
                remainder = text.split(verb, 1)[1].strip()
                for key, view_id in NAV_TRIGGER_MAP.items():
                    if key in remainder:
                        return view_id
        return None

    def _detect_navigation_suggestion(self, text: str, current_view: Optional[str] = None) -> Optional[str]:
        """Suggests a relevant navigation tab based on topic."""
        for key, view_id in NAV_TRIGGER_MAP.items():
            if key in text and view_id != current_view:
                return view_id
        return None

    def _is_fitness_coaching_query(self, text: str) -> bool:
        """Determines if query is a fitness coaching question meant for AI Coach."""
        # Queries about navigating to or using FitQuest Nutrition module features
        if any(w in text for w in ["fitquest nutrition", "how do i view", "where is", "how to log", "what is fitquest", "explain", "navigate to nutrition", "open nutrition", "my diet plan", "my meal plan"]):
            return False

        coaching_patterns = [
            r"how many (reps|sets|squats|pushups|push-ups|calories)",
            r"should i (eat|rest|train|lift|bulk|cut|fast)",
            r"what should i (eat|drink|take)",
            r"how to lose (weight|fat)",
            r"how to gain (muscle|weight)",
            r"(knee|back|shoulder|wrist|elbow|neck|hip) hurts",
            r"create a (workout|split|routine|program|plan)",
            r"workout (routine|split|program|plan) for",
            r"how do i (bulk|cut|tone)",
            r"how (can|do) i (improve|fix|increase) my (squat|bench|deadlift|pushup|form|strength)"
        ]
        return any(re.search(pattern, text) for pattern in coaching_patterns)

    def _is_out_of_domain_query(self, text: str) -> bool:
        """Determines if query is an unrelated general-purpose question."""
        non_fitquest_terms = [
            "weather", "president", "prime minister", "capital of", "who was", "who is",
            "write python", "write code", "javascript code", "movie", "actor", "recipe for cake",
            "joke", "tell a joke", "cryptocurrency", "bitcoin", "stock market", "news today"
        ]
        fitquest_terms = [
            "fitquest", "workout", "dna", "readiness", "load", "streak",
            "copilot", "adaptive", "evolution", "analytics", "coach", "history", "guide", "nutrition", "meal"
        ]
        has_fitquest = any(ft in text for ft in fitquest_terms)
        return any(term in text for term in non_fitquest_terms) and not has_fitquest

    def _rule_based_guide_qa(self, original_msg: str, text: str, current_view: Optional[str] = None) -> str:
        """
        High-precision rule-based knowledge engine covering every FitQuest feature.
        """
        # Context-aware generic questions ("What is this?", "What am I looking at?", "Explain this page")
        if any(phrase in text for phrase in ["what is this", "what am i looking at", "explain this page", "what does this mean", "help on this screen"]):
            if current_view == "movementDnaView":
                return (
                    "### 🧬 Movement DNA™ Overview\n\n"
                    "You are currently viewing **Movement DNA™**, your personalized biomechanical movement fingerprint.\n\n"
                    "• **6 Biomechanical Dimensions**: Stability, Symmetry, Range of Motion, Velocity Control, Postural Integrity, and Consistency.\n"
                    "• **Primary Limiter**: Identifies the key movement constraint holding your performance back (e.g. Torso Stability or Knee Asymmetry).\n"
                    "• **Quality Evolution**: Tracks your longitudinal kinematic progress across workouts with targeted corrective drills."
                )
            elif current_view == "workoutView":
                return (
                    "### 🏋️ Workout Experience Overview\n\n"
                    "You are on the **Workout** tab. Here is how to use it:\n\n"
                    "1. **Step A**: Select an exercise from the catalogue (e.g. Squats, Push-ups, Lunges).\n"
                    "2. **Step B**: Customize reps, sets, rest timers, and toggle **Movement Copilot™** or **Adaptive AI**.\n"
                    "3. **Step C**: Run the workout with real-time YOLOv8 camera tracking, demo skeleton guide, and live form scoring.\n"
                    "4. **Step D**: Review your completed reps, form scores, and AI biomechanical feedback."
                )
            elif current_view == "progressView":
                return (
                    "### 📊 Analytics Overview\n\n"
                    "You are viewing **Analytics**, your interactive performance dashboard.\n\n"
                    "• Filter data by time range (7 days, 30 days, 90 days, or All Time).\n"
                    "• Track volume progression, form quality trends, muscle group distribution, and training frequency heatmaps."
                )
            elif current_view == "adaptiveTrainingView":
                return (
                    "### 🧠 Adaptive AI Overview\n\n"
                    "You are viewing **Adaptive AI**, our real-time training intelligence system.\n\n"
                    "It automatically adjusts workout volume, sets, reps, and intensity based on your fatigue accumulation, form thresholds, and Readiness Score."
                )
            elif current_view == "evolutionView":
                return (
                    "### 📈 Evolution Overview\n\n"
                    "You are viewing **Evolution**, which showcases your long-term movement quality improvements and historical radar adaptations over time."
                )
            elif current_view == "historyView":
                return (
                    "### 🕒 Workout History Overview\n\n"
                    "You are viewing **History**, a complete chronological record of all your completed workout sessions, reps, durations, and form scores."
                )
            elif current_view == "aiCoachView":
                return (
                    "### 🤖 AI Coach Overview\n\n"
                    "You are on the **AI Coach** page. Ask your personal AI coach questions about exercise technique, training splits, recovery, and nutrition!"
                )
            elif current_view == "nutritionView":
                return (
                    "### 🥗 Nutrition Overview\n\n"
                    "You are on the **Nutrition** page, your personalized AI diet and meal recommendation module.\n\n"
                    "• **Today's Nutrition**: Tracks daily calorie targets, protein goals, and completed meals progress.\n"
                    "• **7-Day Meal Plan**: Expandable meal cards with ingredients, prep steps, and macro breakdowns.\n"
                    "• **Single-Meal Regenerator**: Swap any individual meal while keeping the rest of your weekly plan intact.\n"
                    "• **Quick Meal Logger**: Log what you ate to automatically estimate calories and update remaining targets.\n"
                    "• **Preferences & Allergies**: Configure your diet style (Veg/Non-Veg/Vegan), hard allergen exclusions, cuisines, and budget.\n"
                    "• **Food Analyzer**: Upload or take a photo of your food for instant AI nutrient analysis."
                )
            else:
                return (
                    "### 🏠 Dashboard Overview\n\n"
                    "You are on the **FitQuest Dashboard**.\n\n"
                    "• **Training Readiness Score**: Measures recovery status from 0-100.\n"
                    "• **Acute & Chronic Load**: Tracks training fatigue (ACWR) to prevent injury.\n"
                    "• **Active Goals & Streaks**: View current fitness goals, XP, and badges.\n"
                    "• **Quick Actions**: Launch workouts, view Movement DNA™, or explore Nutrition."
                )

        # Feature Queries
        if "what does fitquest provide" in text or "what can fitquest do" in text or "what is fitquest" in text or "features" in text or "overview" in text:
            return (
                "### ⚡ Welcome to FitQuest AI!\n\n"
                "FitQuest is an AI-powered biomechanical fitness & workout intelligence platform. Here are the core features available:\n\n"
                "1. **Real-Time Workout Runner**: YOLOv8 camera pose tracking, skeleton demo guide, rep counting, and live form scoring.\n"
                "2. **Movement DNA™**: 6-dimension biomechanical fingerprint analyzing Stability, Symmetry, ROM, Tempo, Posture, and Consistency.\n"
                "3. **Adaptive AI**: Dynamic auto-regulation of reps, sets, and load based on fatigue.\n"
                "4. **Movement Copilot™**: Real-time in-set micro-coaching and fatigue analysis.\n"
                "5. **Nutrition**: Personalized 7-day meal plans, daily targets, and food logging.\n"
                "6. **Training Readiness & Load (ACWR)**: Daily readiness gauge and acute:chronic workload ratios.\n"
                "7. **Analytics & Evolution**: Longitudinal form trend charts and movement quality tracking.\n"
                "8. **FitQuest AI Coach**: Dedicated AI chatbot for personalized fitness, technique, and nutrition guidance.\n"
                "9. **Workout History & Gamification**: Session logs, XP, streak tracking, and unlockable achievements."
            )

        if "movement dna" in text or "dna" in text:
            return (
                "### 🧬 What is Movement DNA™?\n\n"
                "**Movement DNA™** is your unique biomechanical movement fingerprint computed from your workout tracking data.\n\n"
                "• **6 Core Dimensions**:\n"
                "  1. *Stability*: Core control and balance.\n"
                "  2. *Symmetry*: Bilateral balance between left and right sides.\n"
                "  3. *Range of Motion (ROM)*: Depth and joint mobility.\n"
                "  4. *Velocity Control / Tempo*: Smooth eccentric control and concentric power.\n"
                "  5. *Postural Integrity*: Spinal and torso alignment.\n"
                "  6. *Consistency*: Repetition-to-repetition kinematic uniformity.\n"
                "• **Limiter Detection**: Highlights your primary biomechanical limiter with tailored corrective exercises.\n\n"
                "👉 *You can view it anytime under the **Movement DNA™** tab in the top navigation.*"
            )

        if "body sim" in text or "bodysim" in text or "simulation" in text:
            return (
                "### 🧬 Movement Intelligence in FitQuest\n\n"
                "FitQuest focuses on real-time and longitudinal biomechanical analysis through **Movement DNA™**, **Movement Copilot™**, and **Adaptive AI**.\n\n"
                "You can view your biomechanical fingerprint and primary limiters directly in the **Movement DNA™** tab!"
            )

        if "readiness" in text or "readiness score" in text:
            return (
                "### 🔋 What is the Training Readiness Score?\n\n"
                "The **Training Readiness Score** (0–100) gauges how prepared your body is to perform today.\n\n"
                "• **Optimal (85–100)**: Prime recovery state. Great for high intensity or personal records.\n"
                "• **Good (70–84)**: Well recovered. Standard training recommended.\n"
                "• **Moderate (50–69)**: Mild fatigue. Moderate training or technical focus advised.\n"
                "• **Low (<50)**: High fatigue accumulation. Active recovery, mobility, or deload recommended.\n\n"
                "It is calculated on your **Dashboard** using rest quality, recent training volume, and soreness."
            )

        if "training load" in text or "acwr" in text or "chronic load" in text:
            return (
                "### 📈 What is Training Load & ACWR?\n\n"
                "FitQuest monitors your **Acute:Chronic Workload Ratio (ACWR)**:\n\n"
                "• **Acute Load**: Fatigue accumulated over the last 7 days.\n"
                "• **Chronic Load**: Fitness accumulated over the last 28 days.\n"
                "• **Sweet Spot (0.8 – 1.3)**: Optimal workload for building fitness safely.\n"
                "• **Danger Zone (> 1.5)**: High risk of overtraining or injury; deload recommended.\n\n"
                "Check your current ACWR ratio on the **Dashboard**."
            )

        if "how do i start a workout" in text or "start workout" in text or "how to workout" in text:
            return (
                "### 🚀 How to Start a Workout in FitQuest\n\n"
                "1. Click the **Workout** tab in the top navigation.\n"
                "2. **Step A**: Choose an exercise from the catalogue (e.g. Squats, Push-ups, Lunges).\n"
                "3. **Step B**: Set your target reps, set count, and rest time. You can enable **Movement Copilot** or **Adaptive AI**.\n"
                "4. **Step C**: Click **Start Workout**. Allow camera permissions for real-time YOLOv8 pose detection.\n"
                "5. Follow the skeleton demo avatar and perform your reps while the HUD counts reps and rates form.\n"
                "6. **Step D**: View your post-workout score, AI biomechanical feedback, and updated Movement DNA™."
            )

        if "copilot" in text or "movement copilot" in text:
            return (
                "### 🎙️ What is Movement Copilot™?\n\n"
                "**Movement Copilot™** is your real-time in-set coaching assistant during live workouts.\n\n"
                "• Tracks intra-set rep cadence, joint symmetry, and velocity loss.\n"
                "• Delivers instant visual and audio micro-cues (e.g. *'Drive through heels'*, *'Keep chest up'*) before fatigue causes failed reps.\n"
                "• Provides post-workout fatigue degradation charts."
            )

        if "adaptive" in text or "adaptive ai" in text:
            return (
                "### 🧠 What is Adaptive AI?\n\n"
                "**Adaptive AI** automatically personalizes your workout parameters in real time.\n\n"
                "It adjusts rep targets, set counts, and volume based on your real-time fatigue, form breakdown threshold, and daily Readiness Score so you never overtrain or underperform."
            )

        if "evolution" in text:
            return (
                "### 📈 What is the Evolution Section?\n\n"
                "The **Evolution** section tracks your long-term athletic adaptation over weeks and months.\n\n"
                "It displays longitudinal Movement DNA radar shifts, quality score trajectories, and milestone achievements."
            )

        if "analytics" in text or "progress" in text or "charts" in text:
            return (
                "### 📊 What is Analytics?\n\n"
                "The **Analytics** tab provides rich visualizations of your fitness journey:\n\n"
                "• **Volume Progression**: Total reps, sets, and weight volume over time.\n"
                "• **Form Trends**: Average form quality score progression.\n"
                "• **Muscle Distribution**: Breakdown of targeted muscle groups.\n"
                "• **Frequency Heatmaps**: Consistency and session frequency calendar."
            )

        if "history" in text or "where can i see my history" in text:
            return (
                "### 🕒 Where Can I See My Workout History?\n\n"
                "You can see all your past workouts under the **History** tab in the top navigation.\n\n"
                "Each log entry displays the exercise completed, total reps, duration, form quality score, and date."
            )

        if "ai coach" in text or "where do i find ai coach" in text:
            return (
                "### 🤖 Where Do I Find the AI Coach?\n\n"
                "You can open the **AI Coach** by clicking **AI Coach** in the top navigation bar or from the Dashboard quick card.\n\n"
                "AI Coach is your personal fitness expert for workout planning, technique advice, diet, and recovery questions!"
            )

        if "streak" in text or "xp" in text or "badges" in text or "achievements" in text or "gamification" in text:
            return (
                "### 🏆 Streaks, XP & Achievements\n\n"
                "FitQuest rewards your workout consistency:\n\n"
                "• **XP & Levels**: Earn XP with every completed repetition and high form score.\n"
                "• **Streaks**: Workout regularly to maintain your daily streak.\n"
                "• **Achievements**: Unlock special badges like *First Rep*, *Streak Master*, *Form Perfectionist*, and *Century Club*."
            )

        if "nutrition" in text or "diet" in text or "meal plan" in text or "diet plan" in text or "log meal" in text or "log food" in text or "food" in text:
            return (
                "### 🥗 What is FitQuest Nutrition™?\n\n"
                "FitQuest Nutrition is your personalized AI diet and meal recommendation module tailored to your fitness goals:\n\n"
                "• **Personalized 7-Day Meal Plan**: Goal-aligned meals (Breakfast, Lunch, Snack, Dinner) respecting your diet style and hard allergy constraints.\n"
                "• **Today's Nutrition Summary**: Live progress for daily calorie and protein targets.\n"
                "• **Single-Meal Regenerator**: Swap any individual meal without changing the rest of the week.\n"
                "• **Quick Meal Logger**: Log what you ate with automatic calorie and macro estimation.\n"
                "• **Nutrition Preferences**: Customize diet style (Veg/Non-Veg/Vegan), allergies, cuisines, and budget.\n"
                "• **Food Analyzer**: Estimate nutrients from food descriptions or uploaded photos.\n\n"
                "👉 *Access it anytime under the **Nutrition** tab in the top navigation.*"
            )

        # Default fallback explanation
        return (
            "I'm **FitQuest Guide™**, your in-app assistant!\n\n"
            "I can explain any part of the platform, including:\n"
            "• **Dashboard**: Readiness scores, Training Load (ACWR), and Goals\n"
            "• **Workout**: YOLOv8 pose tracking, skeleton demo, and live form scores\n"
            "• **Nutrition**: Personalized 7-day meal plans, daily targets, and food logging\n"
            "• **Movement DNA™**: 6-dimension biomechanical fingerprint and limiter detection\n"
            "• **Movement Copilot™ & Adaptive AI**: Real-time micro-coaching and auto-regulation\n"
            "• **Analytics & Evolution**: Long-term form trends and volume charts\n"
            "• **AI Coach**: Dedicated coaching chatbot for fitness and nutrition\n"
            "• **History**: Workout logs and gamification streaks\n\n"
            "What would you like to explore?"
        )


fitquest_guide_service = FitQuestGuideService()
