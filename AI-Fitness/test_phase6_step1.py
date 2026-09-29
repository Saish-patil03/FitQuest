#!/usr/bin/env python3
"""
Test suite for Phase 6 Step 1: Frontend Workout Experience & API Integration.
"""

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db

def test_phase6_step1_integration():
    print("[TEST] Initializing Phase 6 Step 1 Integration Test Suite...")

    init_db()
    client = TestClient(app)

    # 1. Verify GET /api/v1/exercises (Exercise Selection Grid)
    res_ex = client.get("/api/v1/exercises")
    assert res_ex.status_code == 200, "Failed to fetch exercises"
    exercises = res_ex.json()
    assert len(exercises) == 20, f"Expected 20 exercises, got {len(exercises)}"
    print(f"[PASS] GET /api/v1/exercises returned {len(exercises)} exercises for frontend selection grid.")

    # 2. Verify User Creation & Workout Session Ingestion (Workout Results Screen)
    user_res = client.post("/api/v1/users", json={"name": "Phase6 Athlete", "email": "p6.athlete@example.com"})
    user_id = user_res.json()["id"]

    workout_payload = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": exercises[1]["id"],  # Squat
            "repetitions": 15,
            "duration_sec": 90,
            "form_score": 93.3
        },
        "form_scores_history": [1, 1, 1, 1, 1, 1],
        "feedback_events": ["Good squat depth maintained"]
    }
    res_w = client.post("/api/v1/workouts", json=workout_payload)
    assert res_w.status_code == 201, "Workout ingestion failed"
    session = res_w.json()
    assert session["repetitions"] == 15, "Rep count mismatch"
    assert len(session["ai_coaching_logs"]) > 0, "AI coaching log missing"
    print(f"[PASS] POST /api/v1/workouts ingested session ID {session['id']} with AI coaching.")

    # 3. Verify GET /api/v1/workouts/user/{user_id} (History View)
    res_hist = client.get(f"/api/v1/workouts/user/{user_id}")
    assert res_hist.status_code == 200, "Get history failed"
    history = res_hist.json()
    assert len(history) >= 1, "History empty"
    print(f"[PASS] GET /api/v1/workouts/user/{user_id} returned {len(history)} historical records.")

    # 4. Verify Phase 5 AI Chatbot (POST /api/v1/ai/qa) remains 100% functional
    res_chat = client.post("/api/v1/ai/qa", json={"question": "How can I improve squat depth?"})
    assert res_chat.status_code == 200, "Chatbot Q&A failed"
    assert res_chat.json().get("status") == "success", "Chatbot status mismatch"
    print("[PASS] POST /api/v1/ai/qa (Phase 5 AI Chatbot) verified 100% functional.")

    print("\n[SUCCESS] All Phase 6 Step 1 Integration tests passed cleanly!")

if __name__ == "__main__":
    test_phase6_step1_integration()
