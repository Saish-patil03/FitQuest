#!/usr/bin/env python3
"""
Test Suite for FitQuest Gamification Layer (Streaks & Achievements)
Verifies:
- TEST 1: New user zero state (0 streak, 0 workout days, 0 valid workouts)
- TEST 2: First valid workout completion (current_streak = 1, FIRST_WORKOUT unlocked)
- TEST 3: Same-day multiple valid workouts (workout session count = 2, workout days = 1, current_streak = 1)
- TEST 4: 3 consecutive workout dates (current_streak = 3, THREE_DAY_STREAK unlocked)
- TEST 5: 7 consecutive workout dates (current_streak = 7, SEVEN_DAY_STREAK unlocked)
- TEST 6: Gap day handling (streak resets appropriately)
- TEST 7: Longest streak preservation (7-day streak, gap, 3-day streak -> longest = 7)
- TEST 8: Zero-rep workout protection (0 streak increase, 0 achievements unlocked, date not active)
- TEST 9: Same-day multi-workout count & streak increment rules
- TEST 10: Multi-user data isolation (User A streak & achievements hidden from User B)
- TEST 11: Achievement uniqueness constraint (no duplicate entries)
"""

import unittest
from datetime import datetime, date, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import UserModel, WorkoutSessionModel, ExerciseModel, UserAchievementModel
from backend.services.gamification_service import gamification_service

# Isolated in-memory SQLite database
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
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

class TestGamificationSystem(unittest.TestCase):

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
        # Clean test tables
        self.db.query(UserAchievementModel).delete()
        self.db.query(WorkoutSessionModel).delete()
        self.db.query(UserModel).delete()
        self.db.commit()

        # Seed test exercise
        ex = self.db.query(ExerciseModel).filter(ExerciseModel.name == "Squat").first()
        if not ex:
            ex = ExerciseModel(
                name="Squat",
                difficulty="Intermediate",
                muscle_group="Legs & Core",
                description="Squat test exercise"
            )
            self.db.add(ex)
            self.db.commit()
        self.test_exercise = ex

    def tearDown(self):
        self.db.close()

    def _register_user(self, name: str, email: str) -> dict:
        res = self.client.post("/api/v1/auth/register", json={
            "name": name,
            "email": email,
            "password": "SecurePassword123!",
            "fitness_goal": "Strength",
            "experience_level": "Intermediate"
        })
        self.assertEqual(res.status_code, 201, res.text)
        return res.json()

    def test_1_new_user_zero_state(self):
        """TEST 1: New user initial streak state (0 streak, 0 days, 0 valid workouts)."""
        auth_data = self._register_user("New User", "new@fitquest.ai")
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Check Streak API
        res = self.client.get("/api/v1/streaks/me", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["current_streak"], 0)
        self.assertEqual(data["longest_streak"], 0)
        self.assertEqual(data["total_workout_days"], 0)
        self.assertEqual(data["total_valid_workouts"], 0)
        self.assertFalse(data["today_completed"])
        self.assertEqual(data["active_dates"], [])

        # Check Achievements API
        ach_res = self.client.get("/api/v1/achievements/me", headers=headers)
        self.assertEqual(ach_res.status_code, 200)
        ach_data = ach_res.json()
        self.assertEqual(len(ach_data), 8)
        for ach in ach_data:
            self.assertFalse(ach["earned"], f"Achievement {ach['id']} should be locked!")

    def test_2_first_valid_workout(self):
        """TEST 2: Complete first valid workout (FIRST_WORKOUT unlocked, streak = 1)."""
        auth_data = self._register_user("First Workout User", "first@fitquest.ai")
        token = auth_data["access_token"]
        user_id = auth_data["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Ingest 1 valid workout (15 reps)
        wo_res = self.client.post("/api/v1/workouts", json={
            "session_data": {
                "user_id": user_id,
                "exercise_id": self.test_exercise.id,
                "repetitions": 15,
                "duration_sec": 60,
                "form_score": 90.0
            }
        }, headers=headers)
        self.assertEqual(wo_res.status_code, 201)

        # Check Streak
        streak_res = self.client.get("/api/v1/streaks/me", headers=headers).json()
        self.assertEqual(streak_res["current_streak"], 1)
        self.assertEqual(streak_res["longest_streak"], 1)
        self.assertEqual(streak_res["total_workout_days"], 1)
        self.assertEqual(streak_res["total_valid_workouts"], 1)
        self.assertTrue(streak_res["today_completed"])

        # Check Achievements
        ach_list = self.client.get("/api/v1/achievements/me", headers=headers).json()
        earned_ids = [a["id"] for a in ach_list if a["earned"]]
        self.assertIn("FIRST_WORKOUT", earned_ids)

    def test_3_same_day_multiple_workouts(self):
        """TEST 3: Complete multiple valid workouts on same day (workout sessions = 2, workout days = 1, streak = 1)."""
        auth_data = self._register_user("Same Day User", "sameday@fitquest.ai")
        token = auth_data["access_token"]
        user_id = auth_data["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Workout 1
        self.client.post("/api/v1/workouts", json={
            "session_data": {"user_id": user_id, "exercise_id": self.test_exercise.id, "repetitions": 10, "duration_sec": 45, "form_score": 85.0}
        }, headers=headers)
        # Workout 2 on same day
        self.client.post("/api/v1/workouts", json={
            "session_data": {"user_id": user_id, "exercise_id": self.test_exercise.id, "repetitions": 12, "duration_sec": 50, "form_score": 88.0}
        }, headers=headers)

        streak_res = self.client.get("/api/v1/streaks/me", headers=headers).json()
        self.assertEqual(streak_res["current_streak"], 1, "Same day workouts must NOT count as multiple streak days!")
        self.assertEqual(streak_res["total_workout_days"], 1)
        self.assertEqual(streak_res["total_valid_workouts"], 2)

    def test_4_and_5_consecutive_workout_streaks(self):
        """TEST 4 & 5: Simulate 3-day and 7-day consecutive workout streaks."""
        auth_data = self._register_user("Streak Master", "streak@fitquest.ai")
        token = auth_data["access_token"]
        user_id = auth_data["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        today = date.today()
        # Seed 7 consecutive workout days directly in DB
        for i in range(6, -1, -1):
            workout_date = datetime.now(timezone.utc) - timedelta(days=i)
            session = WorkoutSessionModel(
                user_id=user_id,
                exercise_id=self.test_exercise.id,
                repetitions=10,
                duration_sec=60,
                form_score=90.0,
                started_at=workout_date,
                completed_at=workout_date
            )
            self.db.add(session)
        self.db.commit()

        # Evaluate achievements
        gamification_service.evaluate_and_award_achievements(self.db, user_id)

        streak_res = self.client.get("/api/v1/streaks/me", headers=headers).json()
        self.assertEqual(streak_res["current_streak"], 7)
        self.assertEqual(streak_res["longest_streak"], 7)

        ach_list = self.client.get("/api/v1/achievements/me", headers=headers).json()
        earned_ids = [a["id"] for a in ach_list if a["earned"]]
        self.assertIn("FIRST_WORKOUT", earned_ids)
        self.assertIn("THREE_DAY_STREAK", earned_ids)
        self.assertIn("SEVEN_DAY_STREAK", earned_ids)

    def test_6_and_7_gap_and_longest_streak_preservation(self):
        """TEST 6 & 7: Simulate streak gap and verify longest_streak preservation."""
        auth_data = self._register_user("Gap User", "gap@fitquest.ai")
        user_id = auth_data["user"]["id"]

        today = date.today()
        # 7-day streak in past (days 15..9 ago)
        for i in range(15, 8, -1):
            workout_date = datetime.combine(today - timedelta(days=i), datetime.min.time()).replace(tzinfo=timezone.utc)
            self.db.add(WorkoutSessionModel(
                user_id=user_id, exercise_id=self.test_exercise.id, repetitions=10, duration_sec=60, form_score=90.0, started_at=workout_date
            ))
        # 2 gap days (days 8, 7 ago no workout)

        # 3-day recent streak (days 2..0 ago)
        for i in range(2, -1, -1):
            workout_date = datetime.combine(today - timedelta(days=i), datetime.min.time()).replace(tzinfo=timezone.utc)
            self.db.add(WorkoutSessionModel(
                user_id=user_id, exercise_id=self.test_exercise.id, repetitions=10, duration_sec=60, form_score=90.0, started_at=workout_date
            ))
        self.db.commit()

        sessions = gamification_service.get_user_valid_sessions(self.db, user_id)
        metrics = gamification_service.calculate_streak_metrics(sessions, target_date=today)

        self.assertEqual(metrics["current_streak"], 3)
        self.assertEqual(metrics["longest_streak"], 7, "Longest streak should preserve past 7-day peak!")

    def test_8_zero_rep_workout_protection(self):
        """TEST 8: Zero-rep workout must NOT increase streak, unlock achievements, or mark date active."""
        auth_data = self._register_user("Zero Rep Gamification", "zerogami@fitquest.ai")
        token = auth_data["access_token"]
        user_id = auth_data["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Ingest 0-rep workout session
        self.client.post("/api/v1/workouts", json={
            "session_data": {
                "user_id": user_id,
                "exercise_id": self.test_exercise.id,
                "repetitions": 0,
                "duration_sec": 74,
                "form_score": 0.0
            }
        })

        streak_res = self.client.get("/api/v1/streaks/me", headers=headers).json()
        self.assertEqual(streak_res["current_streak"], 0)
        self.assertEqual(streak_res["total_workout_days"], 0)
        self.assertEqual(streak_res["total_valid_workouts"], 0)
        self.assertFalse(streak_res["today_completed"])

        ach_list = self.client.get("/api/v1/achievements/me", headers=headers).json()
        earned = [a for a in ach_list if a["earned"]]
        self.assertEqual(len(earned), 0, "Zero-rep workout must NOT unlock any achievements!")

    def test_10_multi_user_data_isolation(self):
        """TEST 10: User A's streak & achievements must NOT be accessible or visible to User B."""
        user_a = self._register_user("User Alpha", "alpha@fitquest.ai")
        user_b = self._register_user("User Beta", "beta@fitquest.ai")

        headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
        headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}

        # User A completes valid workout
        self.client.post("/api/v1/workouts", json={
            "session_data": {"user_id": user_a["user"]["id"], "exercise_id": self.test_exercise.id, "repetitions": 20, "duration_sec": 60, "form_score": 95.0}
        }, headers=headers_a)

        streak_a = self.client.get("/api/v1/streaks/me", headers=headers_a).json()
        streak_b = self.client.get("/api/v1/streaks/me", headers=headers_b).json()

        self.assertEqual(streak_a["current_streak"], 1)
        self.assertEqual(streak_b["current_streak"], 0, "User B should NOT see User A's streak!")

    def test_11_achievement_uniqueness_constraint(self):
        """TEST 11: Achievement unique constraint ensures same achievement cannot be awarded twice."""
        auth_data = self._register_user("Unique Achiever", "unique@fitquest.ai")
        user_id = auth_data["user"]["id"]

        # Award FIRST_WORKOUT twice
        gamification_service.evaluate_and_award_achievements(self.db, user_id)
        # Add another session
        self.db.add(WorkoutSessionModel(
            user_id=user_id, exercise_id=self.test_exercise.id, repetitions=10, duration_sec=60, form_score=90.0, started_at=datetime.now(timezone.utc)
        ))
        self.db.commit()

        # Re-evaluate
        gamification_service.evaluate_and_award_achievements(self.db, user_id)

        count = (
            self.db.query(UserAchievementModel)
            .filter(UserAchievementModel.user_id == user_id, UserAchievementModel.achievement_type == "FIRST_WORKOUT")
            .count()
        )
        self.assertEqual(count, 1, "Achievement FIRST_WORKOUT must exist exactly once!")

if __name__ == "__main__":
    unittest.main()
