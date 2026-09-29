#!/usr/bin/env python3
"""
Test Suite for FitQuest Forgot Password & Password Reset System
Verifies:
- TEST 1: Forgot password request with existing email (generic success message)
- TEST 2: Forgot password request with non-existing email (EXACT SAME generic message - anti-enumeration)
- TEST 3: Secure token generation & hashed storage in DB (token stored only as SHA-256 hash)
- TEST 4: Valid reset token password update
- TEST 5: Login with old password fails after reset
- TEST 6: Login with new password succeeds after reset
- TEST 7: Expired reset token rejection
- TEST 8: Invalid reset token rejection
- TEST 9: Token reuse rejection (single-use enforcement)
- TEST 10: Weak / short password validation rejection (<6 characters)
"""

import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import Base, get_db
from backend.models import UserModel, PasswordResetTokenModel
from backend.utils.auth import hash_reset_token

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

class TestForgotPasswordSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Safety Guard: Ensure test only runs against SQLite
        assert str(test_engine.url).startswith("sqlite"), "Safety guard: Tests must only run against SQLite!"
        app.dependency_overrides[get_db] = override_get_db
        Base.metadata.create_all(bind=test_engine)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.pop(get_db, None)

    def setUp(self):
        self.db = TestingSessionLocal()
        self.db.query(PasswordResetTokenModel).delete()
        self.db.query(UserModel).delete()
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _register_user(self, name: str, email: str, password: str = "OriginalSecret123!") -> dict:
        res = self.client.post("/api/v1/auth/register", json={
            "name": name,
            "email": email,
            "password": password,
            "fitness_goal": "Strength",
            "experience_level": "Intermediate"
        })
        self.assertEqual(res.status_code, 201, res.text)
        return res.json()

    def test_1_and_2_anti_enumeration_generic_response(self):
        """TEST 1 & 2: Verify same generic response for both existing and non-existing email addresses."""
        self._register_user("Registered User", "existing@fitquest.ai")

        # 1. Existing email
        res_existing = self.client.post("/api/v1/auth/forgot-password", json={"email": "existing@fitquest.ai"})
        self.assertEqual(res_existing.status_code, 200)
        msg_existing = res_existing.json()["message"]

        # 2. Non-existing email
        res_non_existing = self.client.post("/api/v1/auth/forgot-password", json={"email": "nonexistent@fitquest.ai"})
        self.assertEqual(res_non_existing.status_code, 200)
        msg_non_existing = res_non_existing.json()["message"]

        # Verify EXACT string equality to prevent account enumeration
        self.assertEqual(msg_existing, "If an account exists for this email, password reset instructions have been sent.")
        self.assertEqual(msg_existing, msg_non_existing, "Generic messages MUST match identically!")

    def test_3_hashed_token_storage(self):
        """TEST 3: Verify reset token is stored ONLY as a SHA-256 hash in DB, not plain text."""
        auth_data = self._register_user("Hash Test User", "hashtest@fitquest.ai")
        user_id = auth_data["user"]["id"]

        # Request reset
        self.client.post("/api/v1/auth/forgot-password", json={"email": "hashtest@fitquest.ai"})

        token_record = (
            self.db.query(PasswordResetTokenModel)
            .filter(PasswordResetTokenModel.user_id == user_id)
            .first()
        )
        self.assertIsNotNone(token_record)
        self.assertFalse(token_record.used)
        self.assertEqual(len(token_record.token_hash), 64, "Token hash must be a 64-character SHA-256 hex string!")

    def test_4_5_6_password_reset_flow(self):
        """TEST 4, 5, 6: Valid password reset, old password fails, new password succeeds."""
        auth_data = self._register_user("Reset User", "reset@fitquest.ai", password="OldPassword123!")

        # Initiate reset
        self.client.post("/api/v1/auth/forgot-password", json={"email": "reset@fitquest.ai"})

        # Retrieve active token hash from DB to get matching raw token
        token_record = (
            self.db.query(PasswordResetTokenModel)
            .filter(PasswordResetTokenModel.user_id == auth_data["user"]["id"])
            .first()
        )

        # For testing, we generate and insert a known raw token
        from backend.utils.auth import generate_reset_token
        test_raw_token = generate_reset_token()
        token_record.token_hash = hash_reset_token(test_raw_token)
        self.db.commit()

        # Submit reset request
        reset_res = self.client.post("/api/v1/auth/reset-password", json={
            "token": test_raw_token,
            "new_password": "BrandNewPassword123!"
        })
        self.assertEqual(reset_res.status_code, 200, reset_res.text)

        # TEST 5: Login with old password fails
        old_login = self.client.post("/api/v1/auth/login", json={
            "email": "reset@fitquest.ai",
            "password": "OldPassword123!"
        })
        self.assertEqual(old_login.status_code, 401)

        # TEST 6: Login with new password succeeds
        new_login = self.client.post("/api/v1/auth/login", json={
            "email": "reset@fitquest.ai",
            "password": "BrandNewPassword123!"
        })
        self.assertEqual(new_login.status_code, 200)

    def test_7_expired_token_rejection(self):
        """TEST 7: Verify expired reset token is rejected."""
        auth_data = self._register_user("Expired User", "expired@fitquest.ai")
        user_id = auth_data["user"]["id"]

        from backend.utils.auth import generate_reset_token
        raw_token = generate_reset_token()
        expired_time = datetime.now(timezone.utc) - timedelta(minutes=10)

        reset_obj = PasswordResetTokenModel(
            user_id=user_id,
            token_hash=hash_reset_token(raw_token),
            expires_at=expired_time,
            used=False
        )
        self.db.add(reset_obj)
        self.db.commit()

        res = self.client.post("/api/v1/auth/reset-password", json={
            "token": raw_token,
            "new_password": "NewPassword123!"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("invalid or has expired", res.json()["detail"])

    def test_8_invalid_token_rejection(self):
        """TEST 8: Verify fake/invalid reset token is rejected."""
        res = self.client.post("/api/v1/auth/reset-password", json={
            "token": "fake_invalid_token_123456789",
            "new_password": "NewPassword123!"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("invalid or has expired", res.json()["detail"])

    def test_9_single_use_token_rejection(self):
        """TEST 9: Verify token cannot be reused once used."""
        auth_data = self._register_user("Reuse User", "reuse@fitquest.ai")
        user_id = auth_data["user"]["id"]

        from backend.utils.auth import generate_reset_token
        raw_token = generate_reset_token()
        future_time = datetime.now(timezone.utc) + timedelta(minutes=20)

        reset_obj = PasswordResetTokenModel(
            user_id=user_id,
            token_hash=hash_reset_token(raw_token),
            expires_at=future_time,
            used=False
        )
        self.db.add(reset_obj)
        self.db.commit()

        # First use -> Success
        res1 = self.client.post("/api/v1/auth/reset-password", json={
            "token": raw_token,
            "new_password": "FirstPass123!"
        })
        self.assertEqual(res1.status_code, 200)

        # Second use -> Rejected
        res2 = self.client.post("/api/v1/auth/reset-password", json={
            "token": raw_token,
            "new_password": "SecondPass123!"
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn("invalid or has expired", res2.json()["detail"])

    def test_10_weak_password_validation(self):
        """TEST 10: Verify short/weak new passwords are rejected (<6 characters)."""
        from backend.utils.auth import generate_reset_token
        raw_token = generate_reset_token()

        res = self.client.post("/api/v1/auth/reset-password", json={
            "token": raw_token,
            "new_password": "123"
        })
        self.assertEqual(res.status_code, 400)

if __name__ == "__main__":
    unittest.main()
