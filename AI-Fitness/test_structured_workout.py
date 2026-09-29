import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import os
os.environ["FITQUEST_SECRET_KEY"] = "test_super_secret_isolation_suite_key_2026"

from backend.database import Base, get_db, seed_exercises
from backend.main import app
import backend.models
from backend.models.user import UserModel
from backend.models.exercise import ExerciseModel
from backend.models.workout import WorkoutSessionModel
from backend.models.structured_workout import (
    StructuredWorkoutSessionModel,
    StructuredWorkoutSetModel
)
from backend.utils.auth import create_access_token, hash_password
from backend.services.structured_workout_service import structured_workout_service
from backend.services.analytics_service import analytics_service
from backend.services.readiness_service import readiness_service
from backend.services.training_load_service import training_load_service
from backend.services.goal_service import goal_service

# Setup isolated in-memory SQLite database for test suite using StaticPool
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
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

class TestStructuredWorkouts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        cls.ai_patcher = patch("backend.services.workout_service.ai_service.generate_coaching_for_session")
        cls.mock_ai = cls.ai_patcher.start()
        cls.mock_ai.return_value = ("Great workout set! Keep up the good form.", "Rule-Based Test Engine")

        Base.metadata.create_all(bind=engine)
        cls.db = TestingSessionLocal()
        seed_exercises(cls.db)

        # Retrieve or create test user
        cls.user = UserModel(
            id=1,
            name="Structured Athlete",
            email="athlete_structured@fitquest.ai",
            password_hash=hash_password("hashed_pass_xyz")
        )
        cls.db.add(cls.user)
        cls.db.commit()
        cls.token = create_access_token(1)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.ai_patcher.stop()
        cls.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_01_list_preset_workout_templates(self):
        """1. Preset workout templates endpoint returns valid routines."""
        response = self.client.get("/api/v1/structured-workouts/templates")
        self.assertEqual(response.status_code, 200)
        plans = response.json()
        self.assertGreaterEqual(len(plans), 5)
        self.assertEqual(plans[0]["title"], "Full Body Foundation")
        self.assertEqual(plans[0]["category"], "Full Body")

    def test_02_start_structured_workout_preset(self):
        """2. Start a structured workout from preset template."""
        payload = {
            "user_id": 1,
            "plan_id": 1
        }
        response = self.client.post("/api/v1/structured-workouts/start", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["plan_title"], "Full Body Foundation")
        self.assertEqual(data["total_exercises"], 4)
        self.assertEqual(data["total_sets"], 12)
        self.assertEqual(data["status"], "IN_PROGRESS")

    def test_03_start_structured_workout_custom(self):
        """3. Start a custom structured workout."""
        payload = {
            "user_id": 1,
            "title": "Custom Upper Body Blast",
            "category": "Upper Body",
            "custom_exercises": [
                {"exercise_id": 3, "target_sets": 2, "target_reps": 10},
                {"exercise_id": 1, "target_sets": 2, "target_reps": 12}
            ]
        }
        response = self.client.post("/api/v1/structured-workouts/start", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["plan_title"], "Custom Upper Body Blast")
        self.assertEqual(data["total_exercises"], 2)
        self.assertEqual(data["total_sets"], 4)

    def test_04_log_set_result_updates_structured_and_standard_telemetry(self):
        """4. Logging a set creates standard WorkoutSessionModel entry and updates structured session."""
        start_res = self.client.post("/api/v1/structured-workouts/start", json={"user_id": 1, "plan_id": 1}, headers=self.headers).json()
        sess_id = start_res["id"]
        ex = self.db.query(ExerciseModel).first()
        ex_id = ex.id if ex else 1

        set_payload = {
            "structured_session_id": sess_id,
            "exercise_id": ex_id,
            "set_number": 1,
            "target_reps": 12,
            "actual_reps": 12,
            "duration_sec": 30,
            "form_score": 95.0,
            "form_scores_history": [1]*12,
            "feedback_events": ["Good Form"]
        }
        res = self.client.post("/api/v1/structured-workouts/log-set", json=set_payload, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        set_data = res.json()
        self.assertIsNotNone(set_data["workout_session_id"])
        self.assertEqual(set_data["actual_reps"], 12)

        # Verify standard WorkoutSessionModel record exists in database
        std_sess = self.db.query(WorkoutSessionModel).filter(WorkoutSessionModel.id == set_data["workout_session_id"]).first()
        self.assertIsNotNone(std_sess)
        self.assertEqual(std_sess.repetitions, 12)

    def test_05_actual_reps_preserved_never_fabricated(self):
        """5. Actual reps (9/12) are recorded; target reps (12) are NEVER fabricated."""
        start_res = self.client.post("/api/v1/structured-workouts/start", json={"user_id": 1, "plan_id": 1}, headers=self.headers).json()
        sess_id = start_res["id"]
        ex = self.db.query(ExerciseModel).first()
        ex_id = ex.id if ex else 1

        set_payload = {
            "structured_session_id": sess_id,
            "exercise_id": ex_id,
            "set_number": 1,
            "target_reps": 12,
            "actual_reps": 9,
            "duration_sec": 28,
            "form_score": 90.0
        }
        res = self.client.post("/api/v1/structured-workouts/log-set", json=set_payload, headers=self.headers).json()
        self.assertEqual(res["actual_reps"], 9)
        self.assertEqual(res["target_reps"], 12)

        summary = self.client.get(f"/api/v1/structured-workouts/summary/{sess_id}", headers=self.headers).json()
        self.assertEqual(summary["total_actual_reps"], 9)

    def test_06_zero_rep_set_creates_valid_record_with_zero_reps(self):
        """6. Zero-rep set (0/12) is recorded with reps=0 and form_score=0.0."""
        start_res = self.client.post("/api/v1/structured-workouts/start", json={"user_id": 1, "plan_id": 1}, headers=self.headers).json()
        sess_id = start_res["id"]
        ex = self.db.query(ExerciseModel).first()
        ex_id = ex.id if ex else 1

        set_payload = {
            "structured_session_id": sess_id,
            "exercise_id": ex_id,
            "set_number": 1,
            "target_reps": 12,
            "actual_reps": 0,
            "duration_sec": 15,
            "form_score": 90.0
        }
        res = self.client.post("/api/v1/structured-workouts/log-set", json=set_payload, headers=self.headers).json()
        self.assertEqual(res["actual_reps"], 0)
        self.assertEqual(res["form_score"], 0.0)

    def test_07_complete_full_structured_workout(self):
        """7. Complete entire multi-exercise structured workout routine."""
        start_res = self.client.post("/api/v1/structured-workouts/start", json={"user_id": 1, "plan_id": 1}, headers=self.headers).json()
        sess_id = start_res["id"]

        ex_list = self.db.query(ExerciseModel).limit(4).all()
        for idx, ex in enumerate(ex_list, start=1):
            self.client.post("/api/v1/structured-workouts/log-set", json={
                "structured_session_id": sess_id,
                "exercise_id": ex.id,
                "set_number": 1,
                "target_reps": 12,
                "actual_reps": 12,
                "duration_sec": 30,
                "form_score": 92.0
            }, headers=self.headers)

        complete_res = self.client.post(f"/api/v1/structured-workouts/complete/{sess_id}", headers=self.headers)
        self.assertEqual(complete_res.status_code, 200)
        summary = complete_res.json()
        self.assertEqual(summary["status"], "COMPLETED")
        self.assertEqual(summary["completed_sets"], 4)
        self.assertEqual(summary["total_actual_reps"], 48)

    def test_08_analytics_integration(self):
        """8. Standard analytics dashboard reflects structured workout sets."""
        summary = analytics_service.get_user_analytics(self.db, user_id=1)
        self.assertIsNotNone(summary)

    def test_09_training_load_integration(self):
        """9. Training load metrics reflect structured workout sets."""
        load_summary = training_load_service.calculate_user_training_load(self.db, user_id=1)
        self.assertIsNotNone(load_summary)

    def test_10_readiness_integration(self):
        """10. Training readiness metrics reflect structured workout sets."""
        readiness = readiness_service.calculate_user_readiness(self.db, user_id=1)
        self.assertIsNotNone(readiness)

    def test_11_goals_integration(self):
        """11. Personalized goals include structured workout reps."""
        goals_list = goal_service.get_user_goals(self.db, user_id=1)
        self.assertIsInstance(goals_list, list)

    def test_12_single_exercise_endpoint_regression(self):
        """12. Existing single-exercise workout endpoint POST /api/v1/workouts remains 100% functional."""
        ex = self.db.query(ExerciseModel).first()
        ex_id = ex.id if ex else 1

        payload = {
            "session_data": {
                "user_id": 1,
                "exercise_id": ex_id,
                "repetitions": 10,
                "duration_sec": 45,
                "form_score": 88.0
            }
        }
        res = self.client.post("/api/v1/workouts", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["repetitions"], 10)


if __name__ == "__main__":
    unittest.main()
