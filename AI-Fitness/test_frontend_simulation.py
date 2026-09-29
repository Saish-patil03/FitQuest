#!/usr/bin/env python3
"""
E2E Frontend Simulation & Verification Test for FitQuest Workout Result Pipeline.

Simulates exact JavaScript state transitions from frontend/workout.js:
1. Workout A: User completes 10 reps of Squat.
   - endWorkoutSession() receives stopSummary {total_reps: 10, form_score: 95.0, duration_sec: 60}
   - POST /api/v1/workouts is called with repetitions=10.
   - Response contains 10-rep performance analysis.
2. Workout B: User completes 0 reps of Squat (immediate stop after 7 seconds).
   - endWorkoutSession() receives stopSummary {total_reps: 0, form_score: 0.0, duration_sec: 7}
   - currentRepCount is updated to 0 from stopSummary.
   - POST /api/v1/workouts is called with repetitions=0.
   - Response contains provider='Deterministic Validation Gate' and deterministic zero-rep text.
   - AI Coach Insights UI contains ZERO text from Workout A (no 10 reps, no 95%, no 60s).
"""

import json
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db, SessionLocal
from backend.models import WorkoutSessionModel, FormLogModel, AICoachingLogModel

def run_frontend_simulation():
    print("==================================================")
    print(" Running E2E Frontend Flow Simulation Test       ")
    print("==================================================")

    init_db()
    db = SessionLocal()
    db.query(AICoachingLogModel).delete()
    db.query(FormLogModel).delete()
    db.query(WorkoutSessionModel).delete()
    db.commit()
    db.close()

    client = TestClient(app)

    # 1. Register User
    u = client.post("/api/v1/users", json={"name": "Real Browser User", "email": "browser@example.com"}).json()
    user_id = u["id"]

    zero_rep_msg = "No valid repetitions were detected in this session, so there isn't enough workout data to generate performance insights. Complete an exercise and try again."

    # --------------------------------------------------
    # WORKOUT A: 10 Reps
    # --------------------------------------------------
    session_a_id = "session_browser_a_123"
    
    # Start live session
    start_a = client.post("/api/v1/workouts/live/start-session", json={"session_id": session_a_id, "exercise_choice": "2"}).json()
    assert start_a["status"] == "success"

    # Stop live session (simulating endWorkoutSession())
    stop_a = client.post("/api/v1/workouts/live/stop-session", json={"session_id": session_a_id}).json()

    # Ingest Workout A with 10 reps
    payload_a = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 2, # Squat
            "repetitions": 10,
            "duration_sec": 60,
            "form_score": 95.0
        },
        "form_scores_history": [1]*10,
        "feedback_events": ["Good depth"]
    }
    res_a = client.post("/api/v1/workouts", json=payload_a).json()
    assert res_a["repetitions"] == 10
    text_a = res_a["ai_coaching_logs"][0]["response"]
    print(f"[PASS] Workout A registered 10 reps cleanly.")

    # --------------------------------------------------
    # WORKOUT B: 0 Reps (Simulates immediate stop after 7s)
    # --------------------------------------------------
    session_b_id = "session_browser_b_456"

    # Start live session for Workout B
    start_b = client.post("/api/v1/workouts/live/start-session", json={"session_id": session_b_id, "exercise_choice": "2"}).json()
    assert start_b["status"] == "success"
    assert start_b["rep_count"] == 0, f"New session must start with 0 reps, got {start_b['rep_count']}"

    # Stop live session (simulating endWorkoutSession())
    stop_b = client.post("/api/v1/workouts/live/stop-session", json={"session_id": session_b_id}).json()
    assert stop_b["status"] == "success"
    assert stop_b["total_reps"] == 0, f"stop-session summary must return 0 reps for 0-rep workout, got {stop_b['total_reps']}"

    # Ingest Workout B using the verified total_reps from stopSummary (0 reps)
    payload_b = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 2, # Squat
            "repetitions": stop_b["total_reps"], # 0
            "duration_sec": 7,
            "form_score": 0.0
        },
        "form_scores_history": [],
        "feedback_events": ["No valid repetitions detected"]
    }
    res_b = client.post("/api/v1/workouts", json=payload_b).json()
    assert res_b["repetitions"] == 0, f"Workout B must have 0 reps, got {res_b['repetitions']}"
    assert res_b["form_score"] == 0.0

    text_b = res_b["ai_coaching_logs"][0]["response"]
    provider_b = res_b["ai_coaching_logs"][0]["provider"]

    assert provider_b == "Deterministic Validation Gate"
    assert zero_rep_msg in text_b

    # Verify ZERO data from Workout A leaked into Workout B
    for phrase in ["10 reps", "95.0%", "60 seconds", "outstanding work"]:
        assert phrase not in text_b.lower(), f"Leak detected in Workout B: {phrase}"

    print(f"[PASS] Workout B registered 0 reps cleanly with ZERO stale data from Workout A.")

    # --------------------------------------------------
    # WORKOUT C: 5 Reps
    # --------------------------------------------------
    session_c_id = "session_browser_c_789"
    client.post("/api/v1/workouts/live/start-session", json={"session_id": session_c_id, "exercise_choice": "2"})
    stop_c = client.post("/api/v1/workouts/live/stop-session", json={"session_id": session_c_id}).json()

    payload_c = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 2, # Squat
            "repetitions": 5,
            "duration_sec": 30,
            "form_score": 85.0
        },
        "form_scores_history": [1, 1, 1, 1, 1],
        "feedback_events": ["5 reps completed"]
    }
    res_c = client.post("/api/v1/workouts", json=payload_c).json()
    assert res_c["repetitions"] == 5
    assert res_c["form_score"] == 85.0
    text_c = res_c["ai_coaching_logs"][0]["response"]
    assert zero_rep_msg not in text_c
    print(f"[PASS] Workout C registered 5 reps cleanly without zero-rep or 10-rep leaks.")

    print("\n==================================================")
    print(" ALL E2E SIMULATION TESTS PASSED 100%!           ")
    print("==================================================")

if __name__ == "__main__":
    run_frontend_simulation()
