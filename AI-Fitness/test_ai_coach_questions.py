#!/usr/bin/env python3
"""
Comprehensive test suite for upgraded FitQuest AI Coach chatbot capabilities.
Tests 9 required categories across online LLM mode (if API available) and offline rule-based engine.
"""

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db
from assistant import AIFitnessAssistant, UserProfile

def test_ai_coach_categories():
    print("[TEST] Initializing FitQuest AI Coach Q&A Category Test Suite...")

    init_db()
    client = TestClient(app)

    test_cases = [
        {
            "category": "1. Exercise Technique",
            "question": "What is the correct way to perform a squat?",
            "expected_keywords": ["squat", "form", "feet", "depth", "knees", "chest"]
        },
        {
            "category": "2. Workout Planning",
            "question": "Create a 4-day beginner workout plan for building strength.",
            "expected_keywords": ["plan", "day", "sets", "reps", "upper", "lower", "bench", "squat"]
        },
        {
            "category": "3. Nutrition",
            "question": "What should I eat after a workout?",
            "expected_keywords": ["protein", "carbs", "nutrition", "eat", "post-workout", "muscle"]
        },
        {
            "category": "4. Recovery",
            "question": "How many rest days should I take?",
            "expected_keywords": ["rest", "days", "recovery", "sleep", "week"]
        },
        {
            "category": "5. Personal Recommendation",
            "question": "I only have dumbbells and 30 minutes. What workout should I do?",
            "expected_keywords": ["dumbbell", "30", "workout", "mins", "circuit"]
        },
        {
            "category": "6. Exercise Comparison",
            "question": "Which is better for chest, push-ups or bench press?",
            "expected_keywords": ["push-up", "bench press", "chest", "comparison", "recommendation"]
        },
        {
            "category": "7. Progression",
            "question": "How do I use progressive overload?",
            "expected_keywords": ["overload", "progressive", "weight", "reps", "volume"]
        },
        {
            "category": "8. Contextual Beginner",
            "question": "I'm a beginner and my goal is strength. How should I start training?",
            "expected_keywords": ["beginner", "strength", "training", "pillars", "form"]
        },
        {
            "category": "9. Out-of-Domain Redirection",
            "question": "Who was the first president of India?",
            "expected_keywords": ["specialized", "fitness", "unable", "off-topic", "FitQuest AI Coach"]
        }
    ]

    print("\n==================================================")
    print("PART A: Testing via REST API (POST /api/v1/ai/qa)")
    print("==================================================")

    for case in test_cases:
        category = case["category"]
        question = case["question"]

        payload = {
            "question": question,
            "user_profile": {
                "fitness_goal": "Strength",
                "experience_level": "Beginner"
            }
        }

        res = client.post("/api/v1/ai/qa", json=payload)
        assert res.status_code == 200, f"API call failed for category {category} with status {res.status_code}"
        data = res.json()
        assert data.get("status") == "success", f"Status mismatch for category {category}"
        assert data.get("question") == question, f"Question echo mismatch for category {category}"
        answer = data.get("answer", "")
        assert len(answer) > 50, f"Answer too short for category {category}: '{answer}'"

        # Verify response contains expected domain/category relevance
        lower_answer = answer.lower()
        if "Out-of-Domain" in category:
            assert "fitquest" in lower_answer or "fitness" in lower_answer or "specialized" in lower_answer, (
                f"Out-of-domain redirection missing fitness context: '{answer}'"
            )
        else:
            assert any(kw.lower() in lower_answer for kw in case["expected_keywords"]), (
                f"Answer for category '{category}' lacked expected keywords: '{answer[:100]}...'"
            )

        print(f"[PASS] [{category}] REST API verified successfully ({len(answer)} chars).")

    print("\n==================================================")
    print("PART B: Direct Offline Fallback Engine Verification")
    print("==================================================")

    # Force offline mode by instantiating AIFitnessAssistant without API key
    offline_assistant = AIFitnessAssistant(api_key=None)
    offline_assistant.genai_client = None  # Explicitly clear client

    profile = UserProfile(fitness_goal="Hypertrophy", experience_level="Beginner")

    for case in test_cases:
        category = case["category"]
        question = case["question"]

        answer = offline_assistant.answer_fitness_question(question, profile)
        assert len(answer) > 40, f"Offline answer too short for category {category}"

        lower_answer = answer.lower()
        if "Out-of-Domain" in category:
            assert "specialized" in lower_answer or "fitquest ai coach" in lower_answer or "fitness" in lower_answer, (
                f"Offline out-of-domain redirection failed: '{answer}'"
            )
        else:
            assert any(kw.lower() in lower_answer for kw in case["expected_keywords"]), (
                f"Offline answer for '{category}' lacked expected keywords: '{answer[:100]}...'"
            )

        print(f"[PASS] [{category}] Offline Fallback Engine verified successfully ({len(answer)} chars).")

    print("\n[SUCCESS] All 9 FitQuest AI Coach Q&A categories verified in Online & Offline modes!")

if __name__ == "__main__":
    test_ai_coach_categories()
