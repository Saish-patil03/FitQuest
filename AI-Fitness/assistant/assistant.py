import os
import sys
from typing import Optional, Dict, Any

from .schema import WorkoutSessionData, UserProfile
from .prompts import (
    SYSTEM_PROMPT,
    POST_WORKOUT_SUMMARY_PROMPT,
    FORM_EXPLANATION_PROMPT,
    FITNESS_QA_PROMPT
)

class AIFitnessAssistant:
    """
    Modular AI Fitness Assistant for interpreting workout telemetry,
    providing personalized feedback, biomechanical form guidance, and general Q&A.
    Features an offline rule-based engine fallback for guaranteed zero-downtime.
    """
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):

        cleaned_key = api_key.strip() if api_key and isinstance(api_key, str) else None
        self.api_key = cleaned_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        # Migrate legacy/deprecated model names if passed
        if model_name in ("gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "gemini-3.6-flash"):
            self.model_name = "gemini-2.5-flash"
        else:
            self.model_name = model_name
        self.genai_client = None
        self.types = None

        if self.api_key:
            try:
                from google import genai
                from google.genai import types
                self.types = types
                self.genai_client = genai.Client(api_key=self.api_key)
                print(f"[INFO] AI Assistant initialized with Gemini API ({self.model_name}).")
            except ImportError:
                print("[INFO] google-genai SDK not found. Running in Rule-Based Fallback Mode.")
            except Exception as e:
                print(f"[WARNING] Could not initialize Gemini API: {e}. Falling back to Rule-Based Mode.")

    def generate_workout_feedback(self, session_data: WorkoutSessionData, user_profile: Optional[UserProfile] = None) -> str:
        """
        Interprets completed workout session metrics and produces personalized coaching feedback.
        Requires a verified exercise result with valid_reps > 0.
        """
        profile = user_profile or UserProfile()

        # Hard Data Validation Gate: Zero-rep or unverified sessions MUST return a deterministic message
        if not session_data or session_data.rep_count is None or session_data.rep_count <= 0:
            return "No valid repetitions were detected in this session, so there isn't enough workout data to generate performance insights. Complete an exercise and try again."

        if self.genai_client:
            try:
                prompt = POST_WORKOUT_SUMMARY_PROMPT.format(
                    exercise_name=session_data.exercise_name,
                    rep_count=session_data.rep_count,
                    duration_formatted=session_data.duration_formatted,
                    duration_sec=session_data.duration_sec,
                    form_score=session_data.form_score,
                    form_scores_history=session_data.form_scores_history,
                    feedback_events=session_data.feedback_events or ["No minor warnings"],
                    fitness_goal=profile.fitness_goal,
                    experience_level=profile.experience_level
                )
                config = self.types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT) if self.types else None
                response = self.genai_client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[WARNING] LLM inference failed ({e}). Reverting to Rule-Based Engine.")

        return self._rule_based_workout_feedback(session_data, profile)


    def explain_form_issues(self, exercise_name: str, form_score: float, feedback_events: list) -> str:
        """
        Generates targeted biomechanical advice for form errors.
        """
        if self.genai_client:
            try:
                prompt = FORM_EXPLANATION_PROMPT.format(
                    exercise_name=exercise_name,
                    form_score=form_score,
                    feedback_events=feedback_events or ["General posture check"]
                )
                config = self.types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT) if self.types else None
                response = self.genai_client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[WARNING] Form LLM inquiry failed: {e}")

        return self._rule_based_form_explanation(exercise_name, form_score, feedback_events)

    def answer_fitness_question(self, question: str, user_profile: Optional[UserProfile] = None) -> str:
        """
        Answers user fitness, workout technique, diet, or recovery questions using AI Assistant.
        Falls back seamlessly to a category-aware rule-based engine when LLM is unavailable.
        """
        profile = user_profile or UserProfile()

        if self.genai_client:
            try:
                prompt = FITNESS_QA_PROMPT.format(
                    question=question,
                    fitness_goal=profile.fitness_goal,
                    experience_level=profile.experience_level
                )
                config = self.types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT) if self.types else None
                response = self.genai_client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[WARNING] Q&A LLM inquiry failed: {e}")

        return self._rule_based_fitness_qa(question, profile)

    def _rule_based_fitness_qa(self, question: str, profile: UserProfile) -> str:
        """
        Intelligent offline fallback engine that categorizes user questions and provides
        rich, structured, and specialized fitness coaching guidance.
        """
        q_lower = question.lower().strip()

        # Fitness domain keywords check
        fitness_keywords = [
            "workout", "exercise", "squat", "push-up", "pushup", "bench press", "curl", "bicep",
            "deadlift", "lunge", "plank", "row", "pull-up", "dip", "strength", "muscle", "hypertrophy",
            "fat loss", "weight loss", "cardio", "hiit", "endurance", "nutrition", "diet", "eat",
            "protein", "carbs", "recovery", "rest", "sleep", "form", "technique", "overload",
            "reps", "sets", "tempo", "warm-up", "cool-down", "stretch", "dumbbells", "gym", "home"
        ]
        has_fitness_context = any(kw in q_lower for kw in fitness_keywords)

        # 1. Out-of-domain detection (polite redirection)
        non_fitness_signals = [
            "president", "prime minister", "capital of", "who was", "who is the first", "history",
            "politics", "election", "geography", "python code", "programming", "movie", "actor",
            "recipe for cake", "astronomy", "currency"
        ]
        if any(signal in q_lower for signal in non_fitness_signals) and not has_fitness_context:
            return (
                f"I am FitQuest AI Coach, specialized specifically in fitness, exercise, nutrition, and recovery. "
                f"I am unable to answer off-topic or general knowledge questions like '{question}'. "
                f"Please feel free to ask me any questions about workout planning, exercise technique, nutrition, or recovery!"
            )

        # 2. Workout Planning & Routine Queries (including dumbbell / 30-min constraints)
        if any(kw in q_lower for kw in ["plan", "routine", "schedule", "program", "split", "create a", "workout should i do"]):
            if "dumbbell" in q_lower or "30 min" in q_lower or "home" in q_lower:
                return (
                    f"### 🏋️ FitQuest AI Coach — Express 30-Min Dumbbell Routine\n\n"
                    f"**Target Profile**: {profile.experience_level} | Goal: {profile.fitness_goal}\n\n"
                    f"**Warm-up (3 mins)**:\n"
                    f"- Arm circles & leg swings (1 min)\n"
                    f"- Bodyweight squats & push-ups (2 mins)\n\n"
                    f"**Circuit Workout (24 mins - 3 Rounds, 45s work / 15s rest)**:\n"
                    f"1. **Dumbbell Goblet Squats**: Targets quadriceps, glutes, and core.\n"
                    f"2. **Dumbbell Floor Press / Push-ups**: Targets chest, shoulders, and triceps.\n"
                    f"3. **Dumbbell Bent-Over Rows**: Targets upper back and biceps.\n"
                    f"4. **Dumbbell Romanian Deadlifts**: Targets hamstrings and posterior chain.\n"
                    f"5. **Dumbbell Overhead Shoulder Press**: Targets deltoids.\n"
                    f"6. **Plank with Dumbbell Drag**: Core stability.\n\n"
                    f"**Cool-down (3 mins)**: Light stretching for chest, back, and hamstrings.\n"
                    f"**Progressive Coaching Cue**: Focus on controlled 2-second eccentric lowering on each rep."
                )
            return (
                f"### 📋 FitQuest AI Coach — Structured Training Plan\n\n"
                f"**Profile**: {profile.experience_level} Athlete | Goal: {profile.fitness_goal}\n\n"
                f"**Recommended 4-Day Upper/Lower Split**:\n"
                f"- **Day 1: Upper Body (Strength Focus)**\n"
                f"  - Bench Press / Push-ups: 4 sets x 6-8 reps (90s rest)\n"
                f"  - Bent-Over Rows: 4 sets x 8-10 reps (90s rest)\n"
                f"  - Overhead Press: 3 sets x 8-10 reps (60s rest)\n"
                f"- **Day 2: Lower Body & Core**\n"
                f"  - Barbell / Dumbbell Squats: 4 sets x 6-8 reps (2 mins rest)\n"
                f"  - Romanian Deadlifts: 3 sets x 8-10 reps (90s rest)\n"
                f"  - Calf Raises & Plank Hold: 3 sets x 12-15 reps / 45s\n"
                f"- **Day 3: Active Recovery / Rest**\n"
                f"- **Day 4: Upper Body (Hypertrophy Focus)**\n"
                f"  - Dumbbell Incline Press: 3 sets x 10-12 reps (60s rest)\n"
                f"  - Lat Pulldowns / Cable Rows: 3 sets x 10-12 reps (60s rest)\n"
                f"  - Bicep Curls & Tricep Extensions: 3 sets x 12 reps\n"
                f"- **Day 5: Lower Body & Mobility**\n"
                f"  - Dumbbell Walking Lunges: 3 sets x 10 reps/leg\n"
                f"  - Hamstring Curls & Core Circuit: 3 sets\n\n"
                f"**Key Rule**: Apply progressive overload by adding 1 rep or small weight increase each week."
            )

        # 3. Exercise Comparisons (e.g., push-ups vs bench press)
        if any(kw in q_lower for kw in ["versus", "vs", "better for", "compare", "difference between"]):
            return (
                f"### ⚖️ FitQuest AI Coach — Exercise Comparison\n\n"
                f"**Analysis for Goal: {profile.fitness_goal} ({profile.experience_level})**:\n\n"
                f"1. **Push-Ups**:\n"
                f"   - **Muscles**: Chest, anterior deltoids, triceps, core.\n"
                f"   - **Pros**: Zero equipment needed, builds exceptional core stability & scapular movement.\n"
                f"   - **Best Used For**: Home workouts, warm-ups, endurance, and functional pressing strength.\n\n"
                f"2. **Bench Press**:\n"
                f"   - **Muscles**: Pectoralis major, anterior deltoids, triceps.\n"
                f"   - **Pros**: Highly scalable external load; optimal for maximal strength & hypertrophy.\n"
                f"   - **Best Used For**: Heavy progressive overload and targeted chest mass development.\n\n"
                f"💡 **Recommendation**: Combine both! Use Bench Press as your primary heavy movement and Push-ups as a burn-out finisher or bodyweight core-integrating accessory."
            )

        # 4. Progressive Overload Queries
        if any(kw in q_lower for kw in ["progressive overload", "overload", "how to progress", "increase weight"]):
            return (
                f"### 📈 FitQuest AI Coach — Progressive Overload Master Guide\n\n"
                f"Progressive overload is the fundamental driver of muscle growth and strength adaptation. "
                f"For a **{profile.experience_level}** athlete targeting **{profile.fitness_goal}**, apply these 4 overload methods:\n\n"
                f"1. **Increase Load**: Add small increments of weight (e.g., 2.5–5 lbs) while keeping reps constant.\n"
                f"2. **Increase Volume**: Perform additional reps or an extra set with current weight (e.g., 3x8 → 3x10).\n"
                f"3. **Improve Execution & Tempo**: Control a 3-second eccentric (lowering) phase for greater muscle tension.\n"
                f"4. **Reduce Rest Period**: Decrease rest time between sets (e.g., 90s → 60s) for higher density.\n\n"
                f"**Coach Principle**: Track every workout session metric to ensure week-over-week measurable growth."
            )

        # 5. Exercise Form & Technique Queries
        if any(kw in q_lower for kw in ["squat", "form", "technique", "correct way", "how to perform", "execution"]):
            return (
                f"### 🏋️ FitQuest AI Coach — Exercise Technique Breakdown\n\n"
                f"**Target Exercise Guidance for Goal: {profile.fitness_goal}**:\n\n"
                f"1. **Purpose & Muscles Involved**: Builds lower body power and core stability. Targets quadriceps, glutes, hamstrings, and erector spinae.\n"
                f"2. **Setup & Stance**: Feet shoulder-width apart, toes turned slightly outward (~15-30°). Chest upright and shoulders packed.\n"
                f"3. **Step-by-Step Execution**:\n"
                f"   - Inhale into abdomen, brace your core.\n"
                f"   - Hinge at hips and bend knees simultaneously, sitting down between ankles.\n"
                f"   - Descend until thighs reach at least parallel to the floor.\n"
                f"   - Drive through mid-foot to push back up to standing extension.\n"
                f"4. **Common Mistakes to Avoid**: Knee caving (valgus), heel elevation, lumbar rounding ('butt wink').\n"
                f"5. **Key Coaching Cue**: *'Screw your feet into the floor and push the floor away.'*"
            )

        # 6. Nutrition & Hydration Queries
        if any(kw in q_lower for kw in ["nutrition", "eat", "diet", "post-workout", "pre-workout", "protein", "hydration", "food"]):
            return (
                f"### 🥗 FitQuest AI Coach — Nutrition & Hydration Strategy\n\n"
                f"**Guidance for Goal: {profile.fitness_goal} ({profile.experience_level})**:\n\n"
                f"1. **Post-Workout Nutrition Window (within 45-60 mins)**:\n"
                f"   - **Protein**: Consuming 25-35g high-quality protein (whey, chicken, tofu, eggs) to trigger Muscle Protein Synthesis (MPS).\n"
                f"   - **Carbohydrates**: Consuming 30-50g complex/fast-acting carbs (rice, oats, banana) to replenish glycogen stores.\n"
                f"2. **Daily Macro Targets**:\n"
                f"   - Protein: Aim for 1.6–2.2g per kg of body weight daily.\n"
                f"   - Hydration: Sip 500ml water pre-workout, plus 500-750ml per hour of exercise.\n"
                f"3. **Pre-Workout Fuel**: Light carb + protein snack 60-90 minutes prior (e.g., oatmeal with protein powder or fruit with toast)."
            )

        # 7. Recovery & Rest Days Queries
        if any(kw in q_lower for kw in ["recovery", "rest day", "rest days", "rest period", "how many rest", "sore"]):
            return (
                f"### 💤 FitQuest AI Coach — Recovery & Rest Optimization\n\n"
                f"**Recommended Rest Schedule for {profile.experience_level} ({profile.fitness_goal})**:\n\n"
                f"1. **Frequency**: Take **2 to 3 dedicated rest/recovery days per week**.\n"
                f"2. **Active Recovery Ideas**: Light walking, foam rolling, 15-minute mobility flow, or gentle swimming.\n"
                f"3. **Why Recovery Matters**: Muscles repair and grow during rest periods, not during the workout itself.\n"
                f"4. **Key Indicators of Good Recovery**: Low resting heart rate, consistent sleep quality, and absence of persistent joint pain.\n"
                f"💡 **Rule**: Never train the exact same muscle group with heavy intensity on back-to-back days."
            )

        # 8. Sleep Queries
        if any(kw in q_lower for kw in ["sleep", "bedtime", "rest hours"]):
            return (
                f"### 😴 FitQuest AI Coach — Sleep & Recovery Guide\n\n"
                f"Sleep is your most potent legal performance enhancer for **{profile.fitness_goal}**:\n\n"
                f"1. **Optimal Duration**: Aim for **7.5 to 9 hours of quality sleep nightly**.\n"
                f"2. **Hormonal Benefits**: Deep sleep triggers Growth Hormone (GH) release and regulates cortisol levels.\n"
                f"3. **Sleep Hygiene Habits**:\n"
                f"   - Keep room cool (~65-68°F / 18-20°C).\n"
                f"   - Avoid screens/blue light 60 mins before bed.\n"
                f"   - Avoid caffeine within 8 hours of bedtime."
            )

        # 9. General Unknown Fitness Fallback
        return (
            f"### 🏋️ FitQuest AI Coach — Personal Guidance\n\n"
            f"*(AI service temporarily offline — providing core rule-based coaching)*\n\n"
            f"For **{profile.experience_level}** athletes targeting **{profile.fitness_goal}**, keep these 4 core pillars in mind regarding '{question}':\n"
            f"1. **Consistent Training**: Stick to a structured program for at least 8-12 weeks.\n"
            f"2. **Progressive Overload**: Gradually increase weight, reps, or control over time.\n"
            f"3. **Nutrition & Protein**: Maintain adequate protein (1.6-2.2g/kg) and hydration.\n"
            f"4. **Adequate Rest**: Ensure 7-9 hours of sleep and 2-3 rest days per week for optimal adaptation."
        )


    def _rule_based_workout_feedback(self, session_data: WorkoutSessionData, profile: UserProfile) -> str:
        """
        Intelligent offline fallback feedback engine based on biomechanical rules.
        Handles zero-rep sessions with honest feedback and setup guidance.
        """
        exercise = session_data.exercise_name
        reps = session_data.rep_count
        duration = session_data.duration_formatted
        score = session_data.form_score

        # Zero-rep session handling
        if reps is None or reps <= 0:
            return "No valid repetitions were detected in this session, so there isn't enough workout data to generate performance insights. Complete an exercise and try again."

        # Grade evaluation for valid rep sessions
        if score >= 90.0:
            grade = "A (Excellent Form)"
            form_eval = f"Outstanding biomechanics during {exercise}! You maintained proper joint alignment throughout most reps."
            cues = [
                f"Maintain steady tempo during both concentric and eccentric phases.",
                f"Consider increasing volume or resistance in your next workout session."
            ]
        elif score >= 75.0:
            grade = "B (Good Form with Minor Deviations)"
            form_eval = f"Solid effort! You completed {reps} reps, but keypoint tracking noted minor form breakdowns on some repetitions."
            cues = [
                f"Focus on full Range of Motion (ROM) rather than rushing repetitions.",
                f"Keep your core engaged to stabilize joint posture throughout the set."
            ]
        else:
            grade = "C (Needs Form Attention)"
            form_eval = f"Form score was {score}%. Computer vision detected multiple reps with incomplete range of motion or joint misalignment."
            cues = [
                f"Slow down repetition speed and prioritize clean form over rep speed.",
                f"Focus on reaching full contraction and extension thresholds."
            ]

        # Specific exercise cues
        exercise_lower = exercise.lower()
        if "curl" in exercise_lower:
            cues.append("Keep elbows static near your torso to avoid swinging shoulders.")
        elif "squat" in exercise_lower:
            cues.append("Keep knees tracking over toes and lower hips until thighs are parallel to the floor.")
        elif "push" in exercise_lower or "press" in exercise_lower:
            cues.append("Maintain a rigid plank line and prevent sagging hips.")

        feedback_output = f"""
================================================
           AI COACH WORKOUT INSIGHTS
================================================
🎯 Performance Overview:
   - Exercise: {exercise}
   - Completed Reps: {reps} reps | Duration: {duration}
   - Target Goal: {profile.fitness_goal} ({profile.experience_level})

🔬 Biomechanics & Form Rating: {score}% ({grade})
   {form_eval}

💡 Actionable Coaching Cues for Next Set:
   1. {cues[0]}
   2. {cues[1]}
   3. {cues[2] if len(cues) > 2 else 'Hydrate and rest 60-90 seconds before your next set.'}

🚀 Recommended Next Step:
   Perform 2 minutes of light stretching, then move to your next planned set or complementary movement.
================================================
"""
        return feedback_output.strip()


    def _rule_based_form_explanation(self, exercise_name: str, form_score: float, feedback_events: list) -> str:
        events_str = ", ".join(feedback_events) if feedback_events else "None"
        return (
            f"Form Analysis for {exercise_name} (Score: {form_score}%):\n"
            f"Keypoint alerts recorded: {events_str}.\n"
            f"To improve: Ensure full extension and contraction on every rep. Keep your core braced and control the movement speed."
        )
