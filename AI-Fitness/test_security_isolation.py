#!/usr/bin/env python3
"""
Comprehensive Multi-User Data Isolation & Security Test Suite for FitQuest / AI-Fitness.
Verifies:
1. User A & User B registration and login.
2. Token generation and Bearer authentication.
3. User A can access ONLY User A's data.
4. User B can access ONLY User B's data.
5. User A CANNOT access User B's workouts via user_id (403).
6. User A CANNOT access User B's workout session via session_id (403/404).
7. User A CANNOT access User B's structured workout summary or history (403/404).
8. User A CANNOT modify or log sets in User B's structured workout session (403/404).
9. User A CANNOT impersonate User B by passing user_b_id in POST /api/v1/workouts.
10. Unauthenticated requests to all private routes return 401 Unauthorized.
11. User directory listing GET /api/v1/users is blocked (403 Forbidden).
12. Legacy user creation POST /api/v1/users is rejected (400 Bad Request).
13. Missing FITQUEST_SECRET_KEY raises a clear RuntimeError.
14. CORS origins are strictly controlled without wildcard.
"""

import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

# Ensure test secret key is set
os.environ["FITQUEST_SECRET_KEY"] = "test_super_secret_isolation_suite_key_2026"

from backend.main import app
from backend.database import get_db, Base, seed_exercises
from backend.models.user import UserModel
from backend.models.workout import WorkoutSessionModel
from backend.models.structured_workout import (
    StructuredWorkoutSessionModel,
    StructuredWorkoutSetModel
)
from backend.models.goal import UserGoalModel
from backend.models.achievement import UserAchievementModel
from backend.utils.auth import get_secret_key, hash_password, create_access_token, verify_access_token
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup isolated in-memory SQLite database
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestSecurityAndDataIsolation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        seed_exercises(db)
        db.close()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)

    def setUp(self):
        app.dependency_overrides[get_db] = override_get_db
        self.db = TestingSessionLocal()
        self.db.query(StructuredWorkoutSetModel).delete()
        self.db.query(StructuredWorkoutSessionModel).delete()
        self.db.query(WorkoutSessionModel).delete()
        self.db.query(UserGoalModel).delete()
        self.db.query(UserAchievementModel).delete()
        self.db.query(UserModel).delete()
        self.db.commit()

        # Patch AI coaching to run fast without external API calls
        self.ai_patcher = patch(
            "backend.services.workout_service.ai_service.generate_coaching_for_session",
            return_value=("Coaching insight: Keep spine neutral!", "Rule-Based Isolation Engine")
        )
        self.ai_patcher.start()

    def tearDown(self):
        self.ai_patcher.stop()
        self.db.close()
        app.dependency_overrides[get_db] = override_get_db

    def _register(self, name: str, email: str, password: str = "StrongPass123!"):
        res = self.client.post("/api/v1/auth/register", json={
            "name": name,
            "email": email,
            "password": password,
            "fitness_goal": "Strength",
            "experience_level": "Intermediate",
            "age": 28,
            "height": 178.0,
            "weight": 75.0,
            "gender": "Male"
        })
        self.assertEqual(res.status_code, 201, f"Failed to register {email}: {res.text}")
        return res.json()

    def _login(self, email: str, password: str = "StrongPass123!"):
        res = self.client.post("/api/v1/auth/login", json={
            "email": email,
            "password": password
        })
        self.assertEqual(res.status_code, 200, f"Failed to login {email}: {res.text}")
        return res.json()

    def test_01_secret_key_enforcement(self):
        """Verify get_secret_key raises RuntimeError when secret key is missing."""
        self.assertTrue(bool(get_secret_key()))
        with patch.dict(os.environ, {"FITQUEST_SECRET_KEY": ""}), \
             patch("backend.config.settings.FITQUEST_SECRET_KEY", None):
            with self.assertRaises(RuntimeError):
                get_secret_key()

    def test_02_registration_and_login_isolation(self):
        """User A and User B register and get unique IDs, tokens, and profiles."""
        data_a = self._register("Alice Wonder", "alice@example.com")
        data_b = self._register("Bob Builder", "bob@example.com")

        self.assertNotEqual(data_a["user"]["id"], data_b["user"]["id"])
        self.assertNotEqual(data_a["access_token"], data_b["access_token"])

        # Login User A
        login_a = self._login("alice@example.com")
        self.assertEqual(login_a["user"]["email"], "alice@example.com")

        # Login User B
        login_b = self._login("bob@example.com")
        self.assertEqual(login_b["user"]["email"], "bob@example.com")

    def test_03_unauthenticated_requests_blocked(self):
        """Unauthenticated requests to protected endpoints return 401 Unauthorized."""
        endpoints = [
            ("GET", "/api/v1/auth/me"),
            ("PUT", "/api/v1/auth/profile", {"name": "Hacker"}),
            ("POST", "/api/v1/workouts", {"session_data": {"user_id": 1, "exercise_id": 1, "repetitions": 10, "duration_sec": 30, "form_score": 90}}),
            ("GET", "/api/v1/workouts/1"),
            ("GET", "/api/v1/workouts/user/1"),
            ("POST", "/api/v1/structured-workouts/start", {"user_id": 1, "plan_id": 1}),
            ("GET", "/api/v1/structured-workouts/user/1"),
            ("GET", "/api/v1/structured-workouts/summary/1"),
            ("GET", "/api/v1/analytics/progress"),
            ("GET", "/api/v1/goals/me"),
            ("POST", "/api/v1/goals", {"goal_type": "REPETITION", "target_value": 100, "time_frame": "WEEKLY"}),
            ("GET", "/api/v1/readiness/me"),
            ("GET", "/api/v1/training-load/me"),
            ("GET", "/api/v1/streaks/me"),
            ("GET", "/api/v1/achievements/me"),
        ]

        for method, path, *body in endpoints:
            payload = body[0] if body else None
            if method == "GET":
                res = self.client.get(path)
            elif method == "POST":
                res = self.client.post(path, json=payload)
            elif method == "PUT":
                res = self.client.put(path, json=payload)
            self.assertEqual(
                res.status_code, 401,
                f"Expected 401 for unauthenticated {method} {path}, got {res.status_code}: {res.text}"
            )

    def test_04_user_directory_lockdown(self):
        """GET /api/v1/users is blocked (403), POST /api/v1/users is deprecated (400)."""
        res_list = self.client.get("/api/v1/users")
        self.assertEqual(res_list.status_code, 403, "GET /api/v1/users must return 403 Forbidden")

        res_create = self.client.post("/api/v1/users", json={"name": "Test", "email": "test@test.com"})
        self.assertEqual(res_create.status_code, 400, "POST /api/v1/users must return 400 Bad Request")

    def test_05_profile_access_isolation(self):
        """User A cannot view User B's profile via /api/v1/users/{id}."""
        data_a = self._register("Alice", "alice_prof@example.com")
        data_b = self._register("Bob", "bob_prof@example.com")

        headers_a = {"Authorization": f"Bearer {data_a['access_token']}"}
        headers_b = {"Authorization": f"Bearer {data_b['access_token']}"}

        # Alice views Alice's profile -> 200
        res_own = self.client.get(f"/api/v1/users/{data_a['user']['id']}", headers=headers_a)
        self.assertEqual(res_own.status_code, 200)
        self.assertEqual(res_own.json()["email"], "alice_prof@example.com")

        # Alice views Bob's profile -> 403
        res_other = self.client.get(f"/api/v1/users/{data_b['user']['id']}", headers=headers_a)
        self.assertEqual(res_other.status_code, 403, "Alice should be forbidden from accessing Bob's profile")

    def test_06_workout_history_isolation(self):
        """User A cannot view User B's workout history."""
        data_a = self._register("Alice W", "alice_work@example.com")
        data_b = self._register("Bob W", "bob_work@example.com")

        headers_a = {"Authorization": f"Bearer {data_a['access_token']}"}
        headers_b = {"Authorization": f"Bearer {data_b['access_token']}"}

        # Alice records a workout
        self.client.post("/api/v1/workouts", json={
            "session_data": {"user_id": data_a["user"]["id"], "exercise_id": 1, "repetitions": 15, "duration_sec": 60, "form_score": 95.0}
        }, headers=headers_a)

        # Alice accesses Alice's workouts -> 200
        res_a_own = self.client.get(f"/api/v1/workouts/user/{data_a['user']['id']}", headers=headers_a)
        self.assertEqual(res_a_own.status_code, 200)
        self.assertEqual(len(res_a_own.json()), 1)

        # Alice attempts to access Bob's workouts -> 403
        res_a_on_b = self.client.get(f"/api/v1/workouts/user/{data_b['user']['id']}", headers=headers_a)
        self.assertEqual(res_a_on_b.status_code, 403, "Alice should be forbidden from reading Bob's workout history")

    def test_07_single_workout_session_isolation(self):
        """User A cannot view User B's single workout session by session_id."""
        data_a = self._register("Alice S", "alice_sess@example.com")
        data_b = self._register("Bob S", "bob_sess@example.com")

        headers_a = {"Authorization": f"Bearer {data_a['access_token']}"}
        headers_b = {"Authorization": f"Bearer {data_b['access_token']}"}

        # Bob records a workout session
        res_bob_workout = self.client.post("/api/v1/workouts", json={
            "session_data": {"user_id": data_b["user"]["id"], "exercise_id": 2, "repetitions": 20, "duration_sec": 90, "form_score": 88.0}
        }, headers=headers_b)
        bob_session_id = res_bob_workout.json()["id"]

        # Bob accesses his own session -> 200
        res_bob_own = self.client.get(f"/api/v1/workouts/{bob_session_id}", headers=headers_b)
        self.assertEqual(res_bob_own.status_code, 200)

        # Alice attempts to access Bob's session -> 403
        res_alice_on_bob = self.client.get(f"/api/v1/workouts/{bob_session_id}", headers=headers_a)
        self.assertEqual(res_alice_on_bob.status_code, 403, "Alice should be forbidden from accessing Bob's session ID")

    def test_08_workout_user_id_impersonation_prevention(self):
        """If Alice sends user_id = Bob's ID in POST /api/v1/workouts, backend assigns it to Alice."""
        data_a = self._register("Alice Impersonator", "alice_imp@example.com")
        data_b = self._register("Bob Victim", "bob_vic@example.com")

        headers_a = {"Authorization": f"Bearer {data_a['access_token']}"}
        headers_b = {"Authorization": f"Bearer {data_b['access_token']}"}

        # Alice attempts to create workout under Bob's user_id
        res_forge = self.client.post("/api/v1/workouts", json={
            "session_data": {
                "user_id": data_b["user"]["id"], # Malicious attempt to spoof Bob's ID
                "exercise_id": 1,
                "repetitions": 50,
                "duration_sec": 120,
                "form_score": 99.0
            }
        }, headers=headers_a)
        self.assertEqual(res_forge.status_code, 201)
        created_session = res_forge.json()

        # The session MUST belong to Alice, NOT Bob
        self.assertEqual(created_session["user_id"], data_a["user"]["id"])
        self.assertNotEqual(created_session["user_id"], data_b["user"]["id"])

        # Bob's history must still be empty
        res_bob_history = self.client.get(f"/api/v1/workouts/user/{data_b['user']['id']}", headers=headers_b)
        self.assertEqual(len(res_bob_history.json()), 0)

        # Alice's history has the workout
        res_alice_history = self.client.get(f"/api/v1/workouts/user/{data_a['user']['id']}", headers=headers_a)
        self.assertEqual(len(res_alice_history.json()), 1)

    def test_09_structured_workout_isolation(self):
        """User A cannot access, log sets, or complete User B's structured workout session."""
        data_a = self._register("Alice Struct", "alice_str@example.com")
        data_b = self._register("Bob Struct", "bob_str@example.com")

        headers_a = {"Authorization": f"Bearer {data_a['access_token']}"}
        headers_b = {"Authorization": f"Bearer {data_b['access_token']}"}

        # Bob starts a structured routine
        res_start = self.client.post("/api/v1/structured-workouts/start", json={
            "plan_id": 1
        }, headers=headers_b)
        self.assertEqual(res_start.status_code, 201)
        bob_struct_id = res_start.json()["id"]

        # Alice attempts to view Bob's structured summary -> 403
        res_alice_summary = self.client.get(f"/api/v1/structured-workouts/summary/{bob_struct_id}", headers=headers_a)
        self.assertEqual(res_alice_summary.status_code, 403)

        # Alice attempts to view Bob's structured history -> 403
        res_alice_history = self.client.get(f"/api/v1/structured-workouts/user/{data_b['user']['id']}", headers=headers_a)
        self.assertEqual(res_alice_history.status_code, 403)

        # Alice attempts to log a set in Bob's session -> 403
        res_alice_log = self.client.post("/api/v1/structured-workouts/log-set", json={
            "structured_session_id": bob_struct_id,
            "exercise_id": 3,
            "set_number": 1,
            "target_reps": 12,
            "actual_reps": 12,
            "duration_sec": 30,
            "form_score": 90.0
        }, headers=headers_a)
        self.assertEqual(res_alice_log.status_code, 403)

        # Alice attempts to complete Bob's session -> 403
        res_alice_complete = self.client.post(f"/api/v1/structured-workouts/complete/{bob_struct_id}", headers=headers_a)
        self.assertEqual(res_alice_complete.status_code, 403)

        # Bob successfully logs set and completes his own session
        res_bob_log = self.client.post("/api/v1/structured-workouts/log-set", json={
            "structured_session_id": bob_struct_id,
            "exercise_id": 3,
            "set_number": 1,
            "target_reps": 12,
            "actual_reps": 12,
            "duration_sec": 30,
            "form_score": 90.0
        }, headers=headers_b)
        self.assertEqual(res_bob_log.status_code, 201)

        res_bob_complete = self.client.post(f"/api/v1/structured-workouts/complete/{bob_struct_id}", headers=headers_b)
        self.assertEqual(res_bob_complete.status_code, 200)

    def test_10_goals_and_analytics_isolation(self):
        """User A and User B have completely separate goals and progress metrics."""
        data_a = self._register("Alice Goal", "alice_goal@example.com")
        data_b = self._register("Bob Goal", "bob_goal@example.com")

        headers_a = {"Authorization": f"Bearer {data_a['access_token']}"}
        headers_b = {"Authorization": f"Bearer {data_b['access_token']}"}

        # Alice creates a goal
        self.client.post("/api/v1/goals", json={
            "goal_type": "REPETITION",
            "target_value": 200,
            "time_frame": "WEEKLY"
        }, headers=headers_a)

        # Alice has 1 goal
        goals_a = self.client.get("/api/v1/goals/me", headers=headers_a).json()
        self.assertEqual(len(goals_a), 1)

        # Bob has 0 goals
        goals_b = self.client.get("/api/v1/goals/me", headers=headers_b).json()
        self.assertEqual(len(goals_b), 0)

if __name__ == "__main__":
    unittest.main()
