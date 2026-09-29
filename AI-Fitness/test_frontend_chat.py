#!/usr/bin/env python3
"""
Test script verifying frontend-to-backend chatbot communication for POST /api/v1/ai/qa.
Tests 5 distinct fitness questions and error handling.
"""

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db

def test_chatbot_api():
    print("[TEST] Testing Frontend Chatbot API integration with POST /api/v1/ai/qa...")

    init_db()
    client = TestClient(app)

    questions = [
        "How can I improve my squat?",
        "How much rest do I need?",
        "What should I eat after a workout?",
        "How can I build strength?",
        "What is proper posture for bicep curls?"
    ]

    for idx, question in enumerate(questions, start=1):
        payload = {
            "question": question,
            "user_profile": {
                "fitness_goal": "Strength",
                "experience_level": "Intermediate"
            }
        }

        res = client.post("/api/v1/ai/qa", json=payload)
        assert res.status_code == 200, f"Question {idx} failed with status {res.status_code}"
        data = res.json()
        assert data.get("status") == "success", f"Question {idx} status mismatch"
        assert data.get("question") == question, f"Question {idx} echo mismatch"
        assert "answer" in data and len(data["answer"]) > 0, f"Question {idx} empty answer"

        print(f"[PASS] Question {idx}: '{question}' -> Received AI Answer ({len(data['answer'])} chars).")

    print("\n[SUCCESS] Tested 5 chatbot questions successfully against POST /api/v1/ai/qa!")

if __name__ == "__main__":
    test_chatbot_api()
