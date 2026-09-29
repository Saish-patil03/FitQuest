#!/usr/bin/env python3
"""
Test suite for Phase 4 REST API endpoints & AI orchestration service.
"""

from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import Base, get_db, seed_exercises

# Setup isolated in-memory SQLite database
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_api_endpoints():
    print("[TEST] Initializing REST API & Service Layer test suite...")

    # Safety Guard: Ensure test only runs against SQLite
    assert str(test_engine.url).startswith("sqlite"), "Safety guard: Tests must only run against SQLite!"

    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    init_sess = TestingSessionLocal()
    seed_exercises(init_sess)
    init_sess.close()

    # Import ai_service to patch assistant methods
    from backend.services.ai_service import ai_service

    # Patch AI coaching & assistant methods to prevent LLM rate limit delays in tests
    with patch("backend.services.workout_service.ai_service.generate_coaching_for_session", return_value=("Great workout set!", "Rule-Based Test Engine")), \
         patch.object(ai_service.assistant, "generate_workout_feedback", return_value="Good squat form! Keep your back straight."), \
         patch.object(ai_service.assistant, "answer_fitness_question", return_value="Keep your elbows tucked during bicep curls."):

        client = TestClient(app)

        # 1. Test Root & Health Endpoints
        res_root = client.get("/")
        assert res_root.status_code == 200, "Root endpoint failed"

        res_health = client.get("/health")
        assert res_health.status_code == 200, "Health check failed"
        print("[PASS] Root and Health endpoints verified.")

        # 2. Test Exercise Catalogue Endpoint (Verify 20 seeded items)
        res_exercises = client.get("/api/v1/exercises")
        assert res_exercises.status_code == 200, "Exercise list endpoint failed"
        exercises = res_exercises.json()
        assert len(exercises) == 20, f"Expected 20 seeded exercises, found {len(exercises)}"
        print(f"[PASS] GET /api/v1/exercises verified ({len(exercises)} exercises returned).")

        # 3. Test User Registration Endpoint
        import time
        test_email = f"alex.strength_{int(time.time() * 1000)}@example.com"
        user_payload = {
            "name": "Alex Strength",
            "email": test_email,
            "password": "StrongPassword123!",
            "fitness_goal": "Hypertrophy",
            "experience_level": "Intermediate"
        }
        res_user = client.post("/api/v1/auth/register", json=user_payload)
        assert res_user.status_code == 201, f"User registration failed: {res_user.text}"
        auth_data = res_user.json()
        user_id = auth_data["user"]["id"]
        auth_token = auth_data["access_token"]
        auth_headers = {"Authorization": f"Bearer {auth_token}"}
        assert auth_data["user"]["name"] == "Alex Strength", "User name mismatch"
        print(f"[PASS] POST /api/v1/auth/register created user ID {user_id}.")

        # 4. Test Get User Endpoint (Authenticated)
        res_get_user = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert res_get_user.status_code == 200, "Get user failed"
        assert res_get_user.json()["email"] == test_email
        print("[PASS] GET /api/v1/users/{user_id} verified.")

        # 5. Test Workout Ingestion & AI Coaching Orchestration Endpoint (Authenticated)
        workout_payload = {
            "session_data": {
                "user_id": user_id,
                "exercise_id": exercises[0]["id"],  # Bicep Curl
                "repetitions": 12,
                "duration_sec": 60,
                "form_score": 91.7
            },
            "form_scores_history": [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1],
            "feedback_events": ["Curl higher on rep 6"]
        }
        res_workout = client.post("/api/v1/workouts", json=workout_payload, headers=auth_headers)
        assert res_workout.status_code == 201, f"Workout ingestion failed: {res_workout.text}"
        session_data = res_workout.json()
        session_id = session_data["id"]
        assert session_data["repetitions"] == 12, "Repetition count mismatch"
        assert session_data["form_score"] == 91.7, "Form score mismatch"
        assert len(session_data["form_logs"]) == 1, "Form log event missing"
        print(f"[PASS] POST /api/v1/workouts ingested session ID {session_id} with form logs.")

        # 6. Test GET Workout Session Details Endpoint (Authenticated)
        res_session = client.get(f"/api/v1/workouts/{session_id}", headers=auth_headers)
        assert res_session.status_code == 200, "Get workout session failed"
        assert res_session.json()["id"] == session_id
        print("[PASS] GET /api/v1/workouts/{session_id} verified.")

        # 7. Test GET User Workout History Endpoint (Authenticated)
        res_history = client.get(f"/api/v1/workouts/user/{user_id}", headers=auth_headers)
        assert res_history.status_code == 200, "Get user workout history failed"
        assert len(res_history.json()) >= 1, "Workout history should contain at least 1 session"
        print("[PASS] GET /api/v1/workouts/user/{user_id} verified.")

        # 8. Test Standalone AI Coaching Endpoint
        ai_coaching_payload = {
            "session_data": {
                "exercise_name": "Squat",
                "rep_count": 15,
                "duration_sec": 90,
                "form_score": 80.0,
                "form_scores_history": [1, 1, 1, 0, 1],
                "feedback_events": ["Squat deeper next time"]
            },
            "user_profile": {
                "fitness_goal": "Strength",
                "experience_level": "Intermediate"
            }
        }
        res_ai_coaching = client.post("/api/v1/ai/coaching", json=ai_coaching_payload)
        assert res_ai_coaching.status_code == 200, f"AI coaching failed: {res_ai_coaching.text}"
        ai_data = res_ai_coaching.json()
        assert ai_data["status"] == "success"
        assert "coaching_feedback" in ai_data
        print("[PASS] POST /api/v1/ai/coaching verified.")

        # 9. Test Standalone Fitness Q&A Endpoint
        qa_payload = {
            "question": "What is the best form cue for bicep curls?",
            "user_profile": {
                "fitness_goal": "Hypertrophy",
                "experience_level": "Intermediate"
            }
        }
        res_qa = client.post("/api/v1/ai/qa", json=qa_payload)
        assert res_qa.status_code == 200, "Fitness Q&A failed"
        qa_data = res_qa.json()
        assert qa_data["status"] == "success"
        assert "answer" in qa_data
        print("[PASS] POST /api/v1/ai/qa verified.")

        print("\n[SUCCESS] All REST API & AI Service Layer tests passed cleanly!")


if __name__ == "__main__":
    test_api_endpoints()
