# Member 4 — AI Fitness Assistant Module

The `assistant` package provides intelligent, personalized workout interpretation, form feedback, biomechanical correction cues, and Q&A capability for the **AI-Fitness** platform.

---

## 📁 Package Architecture

```text
assistant/
├── __init__.py         # Package interface exposing AIFitnessAssistant, WorkoutSessionData, UserProfile
├── assistant.py        # Core AIFitnessAssistant engine with Gemini API support & rule-based offline fallback
├── schema.py           # Typed dataclasses for session telemetry and user profiles
├── prompts.py          # Prompt engineering templates for exercise coaching
└── README.md           # Package documentation
```

---

## 🚀 Key Features

1. **Personalized Workout Interpretation**:
   Converts raw computer vision telemetry (`exercise_name`, `rep_count`, `duration_sec`, `form_score`, `form_scores_history`) into actionable athlete feedback.

2. **Form Flaw Breakdown**:
   Explains joint misalignment errors and provides biomechanical cues for the athlete's next set.

3. **Hybrid AI Architecture**:
   - **Primary Engine**: Uses Google Gemini API (`gemini-1.5-flash` / `gemini-2.0-flash`) for rich generative coaching.
   - **Zero-Downtime Fallback**: If offline or if no API key is set, automatically runs an offline rule-based biomechanics engine so the app never fails.

4. **Integration Ready**:
   Seamlessly interfaces with Member 3's `ExerciseController` and is prepared for Member 5 & 6 (Backend REST API / Frontend UI).

---

## 💻 Quick Usage Example

```python
from assistant import AIFitnessAssistant, WorkoutSessionData, UserProfile

# 1. Instantiate Assistant (Auto-detects GEMINI_API_KEY if present)
assistant = AIFitnessAssistant()

# 2. Package Workout Telemetry from ExerciseController
session = WorkoutSessionData(
    exercise_name="Bicep Curl",
    rep_count=12,
    duration_sec=75,
    form_score=91.7,
    form_scores_history=[1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1],
    feedback_events=["Curl higher on rep 6"]
)

profile = UserProfile(fitness_goal="Hypertrophy", experience_level="Intermediate")

# 3. Generate Coach Insights
feedback = assistant.generate_workout_feedback(session, user_profile=profile)
print(feedback)
```
