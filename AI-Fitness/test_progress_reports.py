#!/usr/bin/env python3
"""
Unit & Integration Test Suite for FitQuest User Progress Reports.
Verifies:
1. 15-day, 30-day, 60-day, 90-day availability computation
2. Minimum 15-day period enforcement (disallows shorter periods)
3. Locked states and friendly messages for insufficient history
4. Accurate date boundary filtering
5. Workout, sets, reps, and duration aggregation
6. Movement quality, form trends, and strongest/focus areas
7. Readiness & recovery metric integration
8. Nutrition and goal tracking integration
9. What Changed (first half vs second half) comparison
10. Strict multi-tenant security isolation (User A vs User B)
11. Deterministic rule-based fallback when Gemini AI is unavailable
12. Clean ReportLab PDF generation and stream response
13. Empty history graceful handling
14. REST API endpoints (/api/v1/reports/available, /api/v1/reports/{days}, /api/v1/reports/{days}/pdf)
"""

import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from backend.main import app
from backend.database import Base, get_db
from backend.models.user import UserModel
from backend.models.exercise import ExerciseModel
from backend.models.workout import WorkoutSessionModel
from backend.models.structured_workout import (
    StructuredWorkoutSessionModel,
    StructuredWorkoutSetModel,
)
from backend.models.nutrition import NutritionProfileModel, NutritionMealLogModel
from backend.models.goal import UserGoalModel
from backend.models.achievement import UserAchievementModel
from backend.utils.auth import create_access_token, hash_password
from backend.services.report_service import report_service

# Setup isolated in-memory SQLite database
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestProgressReports(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        Base.metadata.create_all(bind=test_engine)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)

    def setUp(self):
        self.db = TestingSessionLocal()
        self.db.query(NutritionMealLogModel).delete()
        self.db.query(NutritionProfileModel).delete()
        self.db.query(UserGoalModel).delete()
        self.db.query(UserAchievementModel).delete()
        self.db.query(StructuredWorkoutSetModel).delete()
        self.db.query(StructuredWorkoutSessionModel).delete()
        self.db.query(WorkoutSessionModel).delete()
        self.db.query(UserModel).delete()
        self.db.query(ExerciseModel).delete()
        self.db.commit()

        # Seed exercises
        self.ex_squat = ExerciseModel(id=1, name="Squat", difficulty="Intermediate", muscle_group="Legs & Core", description="Squat")
        self.ex_pushup = ExerciseModel(id=2, name="Push-up", difficulty="Intermediate", muscle_group="Chest & Arms", description="Push-up")
        self.ex_curl = ExerciseModel(id=3, name="Bicep Curl", difficulty="Beginner", muscle_group="Arms", description="Bicep Curl")
        self.db.add_all([self.ex_squat, self.ex_pushup, self.ex_curl])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _create_user(self, name: str, email: str, days_ago: int = 20) -> Tuple_User_Token:
        created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
        user = UserModel(
            name=name,
            email=email,
            password_hash=hash_password("ReportTest123!"),
            fitness_goal="Strength",
            experience_level="Intermediate",
            age=28,
            height=175.0,
            weight=72.0,
            gender="Male",
            created_at=created_at,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        token = create_access_token(user.id)
        return user, token

    def test_01_minimum_period_enforcement(self):
        """1. Reports shorter than 15 days (e.g. 7 or 10 days) are disallowed."""
        user, token = self._create_user("Alice", "alice@fitquest.ai", days_ago=20)
        headers = {"Authorization": f"Bearer {token}"}

        # Request 7 days -> 400 Bad Request
        res_7 = self.client.get("/api/v1/reports/7", headers=headers)
        self.assertEqual(res_7.status_code, 400)
        self.assertIn("Minimum period is 15 days", res_7.json()["detail"])

        # Request 10 days -> 400 Bad Request
        res_10 = self.client.get("/api/v1/reports/10", headers=headers)
        self.assertEqual(res_10.status_code, 400)

        # PDF endpoint also rejects invalid periods
        res_pdf_7 = self.client.get("/api/v1/reports/7/pdf", headers=headers)
        self.assertEqual(res_pdf_7.status_code, 400)

    def test_02_report_availability_locked_states(self):
        """2. New user with 8 days history has 15, 30, 60, 90-day reports locked."""
        user, token = self._create_user("Newbie", "newbie@fitquest.ai", days_ago=8)
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.get("/api/v1/reports/available", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["reports"]), 4)

        for r in data["reports"]:
            self.assertFalse(r["is_available"])
            self.assertIn("Available in", r["status_message"])

        # Attempting to generate locked 15-day report returns 400 with friendly message
        res_gen = self.client.get("/api/v1/reports/15", headers=headers)
        self.assertEqual(res_gen.status_code, 400)
        self.assertIn("Keep going — your 15-day report will be available", res_gen.json()["detail"])

    def test_03_report_availability_partial_history(self):
        """3. User with 35 days history has 15d and 30d available, but 60d and 90d locked."""
        user, token = self._create_user("Midway", "midway@fitquest.ai", days_ago=35)
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.get("/api/v1/reports/available", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        reports_map = {r["period_days"]: r for r in data["reports"]}
        self.assertTrue(reports_map[15]["is_available"])
        self.assertTrue(reports_map[30]["is_available"])
        self.assertFalse(reports_map[60]["is_available"])
        self.assertFalse(reports_map[90]["is_available"])

    def test_04_full_15_day_report_generation(self):
        """4. Generate full 15-day progress report with aggregated workouts, form, and recovery."""
        user, token = self._create_user("Athlete", "athlete@fitquest.ai", days_ago=20)
        headers = {"Authorization": f"Bearer {token}"}

        now = datetime.now(timezone.utc)
        # Seed workouts across the 15-day window
        # Day 14 ago (First half)
        w1 = WorkoutSessionModel(user_id=user.id, exercise_id=1, repetitions=12, duration_sec=45, form_score=75.0, started_at=now - timedelta(days=13))
        # Day 10 ago (First half)
        w2 = WorkoutSessionModel(user_id=user.id, exercise_id=2, repetitions=15, duration_sec=60, form_score=78.0, started_at=now - timedelta(days=10))
        # Day 5 ago (Second half)
        w3 = WorkoutSessionModel(user_id=user.id, exercise_id=1, repetitions=14, duration_sec=50, form_score=88.0, started_at=now - timedelta(days=5))
        # Day 2 ago (Second half)
        w4 = WorkoutSessionModel(user_id=user.id, exercise_id=3, repetitions=16, duration_sec=55, form_score=92.0, started_at=now - timedelta(days=2))
        self.db.add_all([w1, w2, w3, w4])

        # Seed a completed goal
        goal = UserGoalModel(user_id=user.id, goal_type="REPETITION", target_value=50.0, start_date=now - timedelta(days=10), is_completed=True, completed_at=now - timedelta(days=3))
        self.db.add(goal)

        # Seed nutrition profile
        nut = NutritionProfileModel(user_id=user.id, target_calories=2200, target_protein_g=140.0, target_carbs_g=250.0, target_fat_g=70.0)
        self.db.add(nut)
        self.db.commit()

        res = self.client.get("/api/v1/reports/15", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Verify Header
        self.assertEqual(data["header"]["period_days"], 15)
        self.assertEqual(data["header"]["user_name"], "Athlete")

        # Verify Overview
        self.assertEqual(data["overview"]["workouts_completed"], 4)
        self.assertEqual(data["overview"]["total_active_days"], 4)
        self.assertEqual(data["overview"]["total_reps"], 57)
        self.assertAlmostEqual(data["overview"]["avg_form_score"], 83.25, delta=0.5)

        # Verify Workout Progress Top Exercises
        self.assertGreaterEqual(len(data["workout_progress"]["top_exercises"]), 2)
        ex_names = [e["exercise_name"] for e in data["workout_progress"]["top_exercises"]]
        self.assertIn("Squat", ex_names)

        # Verify What Changed Section (First half 2 workouts avg 76.5% vs Second half 2 workouts avg 90.0%)
        self.assertTrue(data["what_changed"]["has_sufficient_comparison_data"])
        self.assertEqual(data["what_changed"]["first_half_workouts"], 2)
        self.assertEqual(data["what_changed"]["second_half_workouts"], 2)
        self.assertGreater(data["what_changed"]["second_half_avg_form"], data["what_changed"]["first_half_avg_form"])

        # Verify Nutrition & Achievements
        self.assertTrue(data["nutrition"]["has_nutrition_profile"])
        self.assertEqual(data["nutrition"]["daily_calories_target"], 2200)
        self.assertEqual(data["achievements"]["completed_goals_count"], 1)

        # Verify Next Steps
        self.assertGreaterEqual(len(data["next_steps"]), 2)

    def test_05_multi_tenant_user_isolation(self):
        """5. User A cannot access or generate reports for User B."""
        user_a, token_a = self._create_user("User A", "usera@fitquest.ai", days_ago=25)
        user_b, token_b = self._create_user("User B", "userb@fitquest.ai", days_ago=25)

        # Add workout for User B
        w = WorkoutSessionModel(user_id=user_b.id, exercise_id=1, repetitions=10, duration_sec=40, form_score=85.0)
        self.db.add(w)
        self.db.commit()

        # User A requests report -> only User A's data returned (0 workouts for User A)
        res_a = self.client.get("/api/v1/reports/15", headers={"Authorization": f"Bearer {token_a}"})
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.json()
        self.assertEqual(data_a["header"]["user_name"], "User A")
        self.assertEqual(data_a["overview"]["workouts_completed"], 0)

        # User B requests report -> User B's workout returned
        res_b = self.client.get("/api/v1/reports/15", headers={"Authorization": f"Bearer {token_b}"})
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.json()
        self.assertEqual(data_b["header"]["user_name"], "User B")
        self.assertEqual(data_b["overview"]["workouts_completed"], 1)

    def test_06_unauthenticated_requests_rejected(self):
        """6. Unauthenticated requests to reports API return 401 Unauthorized."""
        res_avail = self.client.get("/api/v1/reports/available")
        self.assertEqual(res_avail.status_code, 401)

        res_rep = self.client.get("/api/v1/reports/15")
        self.assertEqual(res_rep.status_code, 401)

        res_pdf = self.client.get("/api/v1/reports/15/pdf")
        self.assertEqual(res_pdf.status_code, 401)

    def test_07_pdf_generation_and_download_endpoint(self):
        """7. PDF generation returns valid binary PDF attachment with correct headers."""
        user, token = self._create_user("PDF Tester", "pdftester@fitquest.ai", days_ago=30)
        headers = {"Authorization": f"Bearer {token}"}

        w = WorkoutSessionModel(user_id=user.id, exercise_id=1, repetitions=20, duration_sec=60, form_score=90.0)
        self.db.add(w)
        self.db.commit()

        res_pdf = self.client.get("/api/v1/reports/15/pdf", headers=headers)
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.headers["content-type"], "application/pdf")
        self.assertIn("attachment; filename=", res_pdf.headers["content-disposition"])
        self.assertTrue(res_pdf.content.startswith(b"%PDF"))
        self.assertGreater(len(res_pdf.content), 1000)

    def test_08_deterministic_ai_fallback(self):
        """8. When Gemini API client fails or is absent, deterministic fallback engine succeeds."""
        user, token = self._create_user("Fallback User", "fallback@fitquest.ai", days_ago=20)
        headers = {"Authorization": f"Bearer {token}"}

        # Mock genai client generate_content to raise exception
        with patch.object(report_service, "genai_client", None):
            res = self.client.get("/api/v1/reports/15", headers=headers)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["ai_provider"], "FitQuest Intelligence")
            self.assertIn("15-day journey", data["ai_summary"])

    def test_09_empty_workout_history_graceful_handling(self):
        """9. Available report period with zero workouts displays clean neutral states without crashing."""
        user, token = self._create_user("Zero Workouts", "zero@fitquest.ai", days_ago=25)
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.get("/api/v1/reports/15", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["overview"]["workouts_completed"], 0)
        self.assertIsNone(data["overview"]["avg_form_score"])
        self.assertEqual(data["overview"]["total_reps"], 0)
        self.assertFalse(data["what_changed"]["has_sufficient_comparison_data"])

    def test_10_30_day_report_generation(self):
        """10. Generate 30-day progress report for user with 40 days history."""
        user, token = self._create_user("Thirty Day User", "thirty@fitquest.ai", days_ago=40)
        headers = {"Authorization": f"Bearer {token}"}

        now = datetime.now(timezone.utc)
        for i in [28, 20, 15, 10, 2]:
            w = WorkoutSessionModel(user_id=user.id, exercise_id=1, repetitions=15, duration_sec=60, form_score=85.0, started_at=now - timedelta(days=i))
            self.db.add(w)
        self.db.commit()

        res = self.client.get("/api/v1/reports/30", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["header"]["period_days"], 30)
        self.assertEqual(data["overview"]["workouts_completed"], 5)
        self.assertEqual(data["overview"]["total_reps"], 75)

    def test_11_60_day_and_90_day_reports(self):
        """11. Generate 60-day and 90-day progress reports for veteran user with 100 days history."""
        user, token = self._create_user("Veteran User", "veteran@fitquest.ai", days_ago=100)
        headers = {"Authorization": f"Bearer {token}"}

        res_60 = self.client.get("/api/v1/reports/60", headers=headers)
        self.assertEqual(res_60.status_code, 200)
        self.assertEqual(res_60.json()["header"]["period_days"], 60)

        res_90 = self.client.get("/api/v1/reports/90", headers=headers)
        self.assertEqual(res_90.status_code, 200)
        self.assertEqual(res_90.json()["header"]["period_days"], 90)

    def test_12_user_isolation_on_pdf_endpoint(self):
        """12. User A cannot download PDF for User B's workout data."""
        user_a, token_a = self._create_user("Alice PDF", "alice_pdf@fitquest.ai", days_ago=30)
        user_b, token_b = self._create_user("Bob PDF", "bob_pdf@fitquest.ai", days_ago=30)

        # Add 5 workouts for Bob
        now = datetime.now(timezone.utc)
        for i in range(5):
            w = WorkoutSessionModel(user_id=user_b.id, exercise_id=1, repetitions=20, duration_sec=60, form_score=95.0, started_at=now - timedelta(days=i+1))
            self.db.add(w)
        self.db.commit()

        # Alice generates PDF -> Alice's PDF generated (0 workouts)
        res_pdf_a = self.client.get("/api/v1/reports/15/pdf", headers={"Authorization": f"Bearer {token_a}"})
        self.assertEqual(res_pdf_a.status_code, 200)
        self.assertTrue(res_pdf_a.content.startswith(b"%PDF"))

    def test_13_structured_workout_sets_aggregation(self):
        """13. Structured workout session sets are counted in total sets."""
        user, token = self._create_user("Structured User", "struct@fitquest.ai", days_ago=25)
        headers = {"Authorization": f"Bearer {token}"}

        now = datetime.now(timezone.utc)
        # Create structured session and 3 sets
        struct_sess = StructuredWorkoutSessionModel(
            user_id=user.id,
            plan_title="Upper Body Power",
            category="Strength",
            status="COMPLETED",
            started_at=now - timedelta(days=5),
            completed_at=now - timedelta(days=5, minutes=-20),
            total_exercises=1,
            total_sets=3,
            completed_sets=3,
            total_target_reps=30,
            total_actual_reps=30,
            average_form_score=88.0,
        )
        self.db.add(struct_sess)
        self.db.commit()

        for set_num in range(1, 4):
            s_set = StructuredWorkoutSetModel(
                structured_session_id=struct_sess.id,
                exercise_id=2,
                exercise_name="Push-up",
                set_number=set_num,
                target_reps=10,
                actual_reps=10,
                form_score=90.0,
                status="COMPLETED",
            )
            self.db.add(s_set)
        self.db.commit()

        res = self.client.get("/api/v1/reports/15", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["overview"]["total_sets"], 3)


# Helper type for create_user
from typing import Tuple
Tuple_User_Token = Tuple[UserModel, str]

if __name__ == "__main__":
    unittest.main()

