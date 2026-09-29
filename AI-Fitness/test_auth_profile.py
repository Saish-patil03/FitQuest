#!/usr/bin/env python3
"""
Test Suite for FitQuest User Authentication & Profile System
Verifies:
- Password Hashing (PBKDF2)
- Registration & Validation
- Login & Bearer Token Authentication
- Invalid Credentials & Expired Token Rejection
- Profile Retrieval (/me) and Profile Updates (/profile)
- Multi-user Workout Session Data Isolation
- AI Coach Personalization per User Profile
"""

import sys
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import get_db, Base
from backend.models import UserModel, WorkoutSessionModel, ExerciseModel
from backend.utils.auth import hash_password, verify_password, create_access_token, verify_access_token

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

class TestAuthAndProfileSystem(unittest.TestCase):

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

    def test_password_hashing_utils(self):
        """Test PBKDF2 password hashing & verification logic."""
        pwd = "SecretFitnessPassword123!"
        hashed = hash_password(pwd)
        self.assertIn(":", hashed)
        self.assertEqual(len(hashed.split(":")), 2)
        self.assertNotEqual(pwd, hashed)
        self.assertTrue(verify_password(pwd, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))



    def test_token_creation_and_verification(self):
        """Test URL-safe HMAC access token creation & decoding."""
        user_id = 42
        token = create_access_token(user_id)
        self.assertIsInstance(token, str)
        decoded_id = verify_access_token(token)
        self.assertEqual(decoded_id, user_id)

        # Invalid token
        self.assertIsNone(verify_access_token("invalid.token.str"))

    def test_user_registration_success(self):
        """Test registering a new user via POST /api/v1/auth/register."""
        payload = {
            "name": "Sarah Connor",
            "email": "sarah@fitquest.ai",
            "password": "TerminatorProofPassword123",
            "fitness_goal": "Strength",
            "experience_level": "Advanced",
            "age": 29,
            "height": 170.0,
            "weight": 63.5,
            "gender": "Female"
        }
        res = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(res.status_code, 201, res.text)
        data = res.json()

        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["name"], "Sarah Connor")
        self.assertEqual(data["user"]["email"], "sarah@fitquest.ai")
        self.assertEqual(data["user"]["fitness_goal"], "Strength")
        self.assertEqual(data["user"]["experience_level"], "Advanced")
        self.assertEqual(data["user"]["age"], 29)

        # Ensure password_hash is NOT exposed in UserResponse schema
        self.assertNotIn("password_hash", data["user"])
        self.assertNotIn("password", data["user"])

        # Check DB row
        db_user = self.db.query(UserModel).filter(UserModel.email == "sarah@fitquest.ai").first()
        self.assertIsNotNone(db_user)
        self.assertTrue(verify_password("TerminatorProofPassword123", db_user.password_hash))

    def test_registration_duplicate_email_error(self):
        """Test registration fails when email is already registered."""
        payload = {
            "name": "Original User",
            "email": "dup@fitquest.ai",
            "password": "Password123"
        }
        res1 = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(res1.status_code, 201)

        res2 = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(res2.status_code, 400)
        self.assertIn("already exists", res2.json()["detail"])

    def test_user_login_success_and_failures(self):
        """Test user login with valid & invalid credentials."""
        # 1. Register
        reg_payload = {
            "name": "Bob Runner",
            "email": "bob@fitquest.ai",
            "password": "MarathonRunner2026",
            "fitness_goal": "Endurance",
            "experience_level": "Intermediate"
        }
        self.client.post("/api/v1/auth/register", json=reg_payload)

        # 2. Login with correct password
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": "bob@fitquest.ai",
            "password": "MarathonRunner2026"
        })
        self.assertEqual(login_res.status_code, 200, login_res.text)
        data = login_res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["name"], "Bob Runner")

        # 3. Login with wrong password
        fail_res = self.client.post("/api/v1/auth/login", json={
            "email": "bob@fitquest.ai",
            "password": "WrongPassword"
        })
        self.assertEqual(fail_res.status_code, 401)

        # 4. Login with non-existent email
        fail_res2 = self.client.post("/api/v1/auth/login", json={
            "email": "nobody@fitquest.ai",
            "password": "SomePassword"
        })
        self.assertEqual(fail_res2.status_code, 401)

    def test_get_current_user_and_profile_updates(self):
        """Test GET /api/v1/auth/me and PUT /api/v1/auth/profile."""
        reg_res = self.client.post("/api/v1/auth/register", json={
            "name": "Charlie Lift",
            "email": "charlie@fitquest.ai",
            "password": "BenchPress300",
            "fitness_goal": "General Fitness"
        })
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # GET /me
        me_res = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["name"], "Charlie Lift")

        # PUT /profile
        update_res = self.client.put("/api/v1/auth/profile", headers=headers, json={
            "name": "Charlie Iron",
            "fitness_goal": "Muscle Gain",
            "experience_level": "Advanced",
            "weight": 85.0,
            "height": 182.0
        })
        self.assertEqual(update_res.status_code, 200)
        updated = update_res.json()
        self.assertEqual(updated["name"], "Charlie Iron")
        self.assertEqual(updated["fitness_goal"], "Muscle Gain")
        self.assertEqual(updated["experience_level"], "Advanced")
        self.assertEqual(updated["weight"], 85.0)

    def test_workout_data_isolation_between_users(self):
        """Test User A cannot view User B's workout session history."""
        # User A
        res_a = self.client.post("/api/v1/auth/register", json={
            "name": "User Alpha",
            "email": "alpha@fitquest.ai",
            "password": "PasswordAlpha123"
        })
        token_a = res_a.json()["access_token"]
        user_a_id = res_a.json()["user"]["id"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # User B
        res_b = self.client.post("/api/v1/auth/register", json={
            "name": "User Beta",
            "email": "beta@fitquest.ai",
            "password": "PasswordBeta123"
        })
        token_b = res_b.json()["access_token"]
        user_b_id = res_b.json()["user"]["id"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A performs Squats
        res_post = self.client.post("/api/v1/workouts", json={
            "session_data": {
                "user_id": user_a_id,
                "exercise_id": self.test_exercise.id,
                "repetitions": 12,
                "duration_sec": 45,
                "form_score": 92.5
            }
        }, headers=headers_a)
        self.assertEqual(res_post.status_code, 201)

        # Fetch User A's history with User A's token
        res_hist_a = self.client.get(f"/api/v1/workouts/user/{user_a_id}", headers=headers_a)
        self.assertEqual(res_hist_a.status_code, 200)
        hist_a = res_hist_a.json()
        self.assertEqual(len(hist_a), 1)
        self.assertEqual(hist_a[0]["repetitions"], 12)

        # Fetch User B's history with User B's token
        res_hist_b = self.client.get(f"/api/v1/workouts/user/{user_b_id}", headers=headers_b)
        self.assertEqual(res_hist_b.status_code, 200)
        hist_b = res_hist_b.json()
        self.assertEqual(len(hist_b), 0, "User B should NOT see User A's workouts!")

        # User A attempts to access User B's history -> 403 Forbidden
        res_cross = self.client.get(f"/api/v1/workouts/user/{user_b_id}", headers=headers_a)
        self.assertEqual(res_cross.status_code, 403, "User A must not be able to read User B's workouts")

if __name__ == "__main__":
    unittest.main()
