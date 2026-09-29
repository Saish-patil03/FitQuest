#!/usr/bin/env python3
"""
Comprehensive 9-Scenario Regression Test Suite for FitQuest AI Workout Results & Data Integrity.

Verifies:
- TEST 1: New workout, 0 reps -> reps = 0, form_score = 0.0, deterministic no-data message, no Gemini call.
- TEST 2: Complete workout with 10 verified reps -> exact metrics used.
- TEST 3: Workout A (12 reps, 50s, 88% form) -> Finish -> Workout B (0 reps, 19s, N/A form) -> Workout B MUST NOT contain 12 reps, 50s, 88%, or previous coaching text.
- TEST 4: Workout A (0 reps) -> Workout B (10 reps) -> Workout B contains ONLY Workout B telemetry.
- TEST 5: Complete workout -> refresh browser / query GET /workouts/{id} -> session remains correct and isolated.
- TEST 6: Complete workout -> open History -> start new 0-rep workout -> session remains isolated from history.
- TEST 7: Frontend sends reps = 0, form_score = 95 -> backend forces form to 0.0, returns zero-rep state.
- TEST 8: Valid workout with offline fallback -> operates on verified metrics without inventing numbers.
- TEST 9: Inspect network request / API completion payload -> provider is 'Deterministic Validation Gate', reps = 0.
"""

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db, SessionLocal
from backend.models import WorkoutSessionModel, FormLogModel, AICoachingLogModel
from assistant import AIFitnessAssistant, WorkoutSessionData, UserProfile
from utils.counter import BaseExerciseTracker
from backend.services.cv_service import cv_live_service

def run_regression_tests():
    print("==================================================")
    print(" Running FitQuest 9-Scenario Data Integrity Suite ")
    print("==================================================")

    init_db()
    db = SessionLocal()
    db.query(AICoachingLogModel).delete()
    db.query(FormLogModel).delete()
    db.query(WorkoutSessionModel).delete()
    db.commit()
    db.close()

    client = TestClient(app)

    # Base Exercise Tracker check
    tracker = BaseExerciseTracker("High Knees")
    assert tracker.rep_count == 0
    assert tracker.get_form_score() == 0.0, f"Expected 0.0 form score for 0 reps, got {tracker.get_form_score()}"
    print("[PASS] BaseExerciseTracker returns 0.0 form score for 0 reps.")

    # Create test user
    user_res = client.post("/api/v1/users", json={"name": "Strict Session User", "email": "strict_session@example.com"})
    assert user_res.status_code in (200, 201)
    user_id = user_res.json()["id"]

    zero_rep_msg = "No valid repetitions were detected in this session, so there isn't enough workout data to generate performance insights. Complete an exercise and try again."

    # ==================================================
    # TEST 1: Complete workout with 0 reps
    # ==================================================
    payload_1 = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 1,  # Bicep Curl
            "repetitions": 0,
            "duration_sec": 19,
            "form_score": 0.0
        },
        "form_scores_history": [],
        "feedback_events": ["No valid repetitions detected"]
    }
    res_1 = client.post("/api/v1/workouts", json=payload_1)
    assert res_1.status_code == 201
    data_1 = res_1.json()
    assert data_1["repetitions"] == 0
    assert data_1["form_score"] == 0.0
    ai_logs_1 = data_1.get("ai_coaching_logs", [])
    assert len(ai_logs_1) > 0
    assert ai_logs_1[0]["provider"] == "Deterministic Validation Gate"
    assert zero_rep_msg in ai_logs_1[0]["response"]
    print("[PASS] TEST 1: Complete workout with 0 reps produced deterministic zero-rep response without Gemini call.")

    # ==================================================
    # TEST 2: Complete workout with 10 verified reps
    # ==================================================
    payload_2 = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 2,  # Squat
            "repetitions": 10,
            "duration_sec": 60,
            "form_score": 95.0
        },
        "form_scores_history": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        "feedback_events": ["Good squat depth"]
    }
    res_2 = client.post("/api/v1/workouts", json=payload_2)
    assert res_2.status_code == 201
    data_2 = res_2.json()
    assert data_2["repetitions"] == 10
    assert data_2["form_score"] == 95.0
    assert data_2["duration_sec"] == 60
    ai_logs_2 = data_2.get("ai_coaching_logs", [])
    assert len(ai_logs_2) > 0
    print("[PASS] TEST 2: Complete workout with 10 verified reps recorded exact metrics cleanly.")

    # ==================================================
    # TEST 3: Workout A (12 reps, 50s, 88% form) -> Workout B (0 reps, 19s, N/A form)
    # Re-creates exact manual bug scenario!
    # ==================================================
    # Step 1: Start live session for Workout A
    sess_a_id = "session_test_3_a"
    start_res_a = client.post("/api/v1/workouts/live/start-session", json={"session_id": sess_a_id, "exercise_choice": "2"})
    assert start_res_a.status_code == 200

    # Ingest Workout A (12 reps, 50s, 88% form)
    payload_3_a = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 2,  # Squat
            "repetitions": 12,
            "duration_sec": 50,
            "form_score": 88.0
        },
        "form_scores_history": [1]*12,
        "feedback_events": ["12 reps completed"]
    }
    res_3_a = client.post("/api/v1/workouts", json=payload_3_a)
    assert res_3_a.status_code == 201
    data_3_a = res_3_a.json()
    assert data_3_a["repetitions"] == 12
    assert data_3_a["form_score"] == 88.0

    # Stop Workout A session
    client.post("/api/v1/workouts/live/stop-session", json={"session_id": sess_a_id})

    # Step 2: Immediately start Workout B for 0 reps
    sess_b_id = "session_test_3_b"
    start_res_b = client.post("/api/v1/workouts/live/start-session", json={"session_id": sess_b_id, "exercise_choice": "2"})
    assert start_res_b.status_code == 200

    # Ingest Workout B (0 reps, 19s)
    payload_3_b = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 2,  # Squat
            "repetitions": 0,
            "duration_sec": 19,
            "form_score": 0.0
        },
        "form_scores_history": [],
        "feedback_events": ["No reps detected"]
    }
    res_3_b = client.post("/api/v1/workouts", json=payload_3_b)
    assert res_3_b.status_code == 201
    data_3_b = res_3_b.json()
    assert data_3_b["repetitions"] == 0, f"Expected 0 reps for Workout B, got {data_3_b['repetitions']}"
    assert data_3_b["form_score"] == 0.0, f"Expected 0.0 form score for Workout B, got {data_3_b['form_score']}"

    ai_logs_3_b = data_3_b.get("ai_coaching_logs", [])
    assert len(ai_logs_3_b) > 0
    text_3_b = ai_logs_3_b[0]["response"]
    provider_3_b = ai_logs_3_b[0]["provider"]

    assert provider_3_b == "Deterministic Validation Gate", f"Expected 'Deterministic Validation Gate', got '{provider_3_b}'"

    # CRITICAL CHECK: Workout B MUST NOT contain ANY data from Workout A!
    forbidden_leak = ["12 reps", "12 / 12", "88.0%", "88%", "50 seconds", "00:50", "you completed 12"]
    for phrase in forbidden_leak:
        assert phrase not in text_3_b.lower(), f"STALE DATA LEAK DETECTED! '{phrase}' from Workout A leaked into Workout B: {text_3_b}"

    assert zero_rep_msg in text_3_b, f"Expected deterministic zero-rep text, got: {text_3_b}"
    print("[PASS] TEST 3: Workout A (12 reps, 50s, 88%) -> Workout B (0 reps, 19s) -> Workout B contains ZERO data from Workout A.")

    # ==================================================
    # TEST 4: Complete 0-rep workout first, THEN complete 10-rep workout
    # ==================================================
    payload_4_zero = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 3,  # Push-up
            "repetitions": 0,
            "duration_sec": 8,
            "form_score": 0.0
        },
        "form_scores_history": [],
        "feedback_events": ["No reps"]
    }
    res_4_a = client.post("/api/v1/workouts", json=payload_4_zero)
    assert res_4_a.status_code == 201
    assert res_4_a.json()["repetitions"] == 0

    payload_4_valid = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 3,  # Push-up
            "repetitions": 10,
            "duration_sec": 50,
            "form_score": 90.0
        },
        "form_scores_history": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        "feedback_events": ["Good pushup form"]
    }
    res_4_b = client.post("/api/v1/workouts", json=payload_4_valid)
    assert res_4_b.status_code == 201
    data_4_b = res_4_b.json()
    assert data_4_b["repetitions"] == 10
    assert data_4_b["form_score"] == 90.0
    text_4_b = data_4_b["ai_coaching_logs"][0]["response"]
    assert zero_rep_msg not in text_4_b, "Valid 10-rep workout must NOT show zero-rep state"
    print("[PASS] TEST 4: Complete 0-rep workout first, then 10-rep workout -> 2nd workout correctly shows 10 reps.")

    # ==================================================
    # TEST 5: Refresh/reload result page after 0-rep workout
    # ==================================================
    zero_session_id = data_3_b["id"]
    res_get_5 = client.get(f"/api/v1/workouts/{zero_session_id}")
    assert res_get_5.status_code == 200
    data_5 = res_get_5.json()
    assert data_5["repetitions"] == 0
    assert data_5["form_score"] == 0.0
    assert len(data_5["ai_coaching_logs"]) > 0
    assert zero_rep_msg in data_5["ai_coaching_logs"][0]["response"]
    print("[PASS] TEST 5: GET /workouts/{id} for zero-rep session returns reps=0 and deterministic coaching text.")

    # ==================================================
    # TEST 6: Navigate Workout -> History -> Workout again -> complete 0 reps
    # ==================================================
    res_hist_6 = client.get(f"/api/v1/workouts/user/{user_id}")
    assert res_hist_6.status_code == 200
    history_6 = res_hist_6.json()
    assert len(history_6) >= 4, "History contains recorded sessions"

    # Start new zero-rep session after checking history
    payload_6 = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 4,  # Sit-up
            "repetitions": 0,
            "duration_sec": 14,
            "form_score": 0.0
        },
        "form_scores_history": [],
        "feedback_events": ["No reps"]
    }
    res_6 = client.post("/api/v1/workouts", json=payload_6)
    assert res_6.status_code == 201
    data_6 = res_6.json()
    assert data_6["repetitions"] == 0
    assert zero_rep_msg in data_6["ai_coaching_logs"][0]["response"]
    print("[PASS] TEST 6: Session completed after viewing history remains strictly isolated.")

    # ==================================================
    # TEST 7: Verify malformed frontend data (reps = 0, form_score = 95.0)
    # ==================================================
    payload_7 = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 1,
            "repetitions": 0,
            "duration_sec": 20,
            "form_score": 95.0  # Manipulated form score
        },
        "form_scores_history": [],
        "feedback_events": ["Manipulated test"]
    }
    res_7 = client.post("/api/v1/workouts", json=payload_7)
    assert res_7.status_code == 201
    data_7 = res_7.json()
    assert data_7["form_score"] == 0.0, "Backend must force form_score to 0.0 when reps == 0"
    assert zero_rep_msg in data_7["ai_coaching_logs"][0]["response"]
    print("[PASS] TEST 7: Backend validation forces form_score to 0.0 and rejects performance analysis on reps=0.")

    # ==================================================
    # TEST 8: Gemini offline fallback & zero-rep gate
    # ==================================================
    assistant_offline = AIFitnessAssistant(api_key=None)
    assistant_offline.genai_client = None

    # Offline mode with valid reps -> uses actual metrics
    data_8_valid = WorkoutSessionData(
        exercise_name="Squat", rep_count=8, duration_sec=40, form_score=88.0,
        form_scores_history=[1, 1, 1, 1, 1, 1, 1, 1], feedback_events=["Good depth"]
    )
    feedback_8 = assistant_offline.generate_workout_feedback(data_8_valid)
    assert "Completed Reps: 8 reps" in feedback_8

    # Offline mode with zero reps -> STILL returns deterministic zero-rep message
    data_8_zero = WorkoutSessionData(
        exercise_name="Squat", rep_count=0, duration_sec=10, form_score=0.0,
        form_scores_history=[], feedback_events=[]
    )
    feedback_8_zero = assistant_offline.generate_workout_feedback(data_8_zero)
    assert zero_rep_msg in feedback_8_zero
    print("[PASS] TEST 8: Offline fallback operates accurately for valid reps; zero-rep STILL returns deterministic no-data message.")

    # ==================================================
    # TEST 9: Inspect API completion response payload for zero-rep workout
    # ==================================================
    payload_9 = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 2,
            "repetitions": 0,
            "duration_sec": 5,
            "form_score": 0.0
        },
        "form_scores_history": [],
        "feedback_events": []
    }
    res_9 = client.post("/api/v1/workouts", json=payload_9)
    assert res_9.status_code == 201
    data_9 = res_9.json()
    assert data_9["repetitions"] == 0
    assert data_9["form_score"] == 0.0
    assert data_9["ai_coaching_logs"][0]["provider"] == "Deterministic Validation Gate"
    assert zero_rep_msg in data_9["ai_coaching_logs"][0]["response"]
    print("[PASS] TEST 9: API completion payload verified: provider='Deterministic Validation Gate', reps=0.")

    print("\n==================================================")
    print(" ALL 9 REGRESSION TEST SCENARIOS PASSED 100%!     ")
    print("==================================================")

if __name__ == "__main__":
    run_regression_tests()
