#!/usr/bin/env python3
"""
Unit & Integration Test Suite for FitQuest Movement Fingerprint & Movement Evolution System (Phase 2).

Verifies:
1. Fingerprint model creation and field validation
2. Fingerprint database persistence & linking with WorkoutSessionModel
3. Retrieve authenticated user's movement history (GET /movement-intelligence/history)
4. Multi-user data isolation (User A cannot access User B's fingerprints)
5. Unauthenticated / unknown user rejection (401/403)
6. Exercise filtering on historical queries (exercise_id)
7. Evolution calculation across multiple sessions
8. Baseline calculation for single-session history
9. Improving trend classification (delta >= +3%)
10. Stable trend classification (within +/- 3%)
11. Declining trend classification (delta <= -3%)
12. Unilateral symmetry handling (returns None without penalty)
13. Zero/empty history graceful handling
14. Duplicate session protection (idempotent save_fingerprint)
15. Session historical comparison endpoint (GET /movement-intelligence/comparison)
"""

import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import UserModel, ExerciseModel, WorkoutSessionModel, MovementFingerprintModel
from backend.services.movement_fingerprint_service import movement_fingerprint_service
from backend.services.movement_intelligence import MovementAnalyzer

# Isolated in-memory SQLite database for robust, fast, isolated testing
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


class TestMovementFingerprintAndEvolution(unittest.TestCase):
    """
    Comprehensive test suite for Phase 2 Persistent Movement Intelligence.
    """

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
        # Clean tables before each test
        self.db.query(MovementFingerprintModel).delete()
        self.db.query(WorkoutSessionModel).delete()
        self.db.query(UserModel).delete()
        self.db.query(ExerciseModel).delete()
        self.db.commit()

        # Seed standard test exercises
        self.ex_squat = ExerciseModel(id=1, name="Squat", difficulty="Intermediate", description="Squat exercise")
        self.ex_lunge = ExerciseModel(id=2, name="Lunges", difficulty="Intermediate", description="Unilateral lunge")
        self.db.add_all([self.ex_squat, self.ex_lunge])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _register_user(self, name: str, email: str) -> dict:
        res = self.client.post("/api/v1/auth/register", json={
            "name": name,
            "email": email,
            "password": "Password123!",
            "fitness_goal": "Strength",
            "experience_level": "Intermediate"
        })
        return res.json()

    # --- TEST 1: Fingerprint Model Instantiation ---
    def test_01_fingerprint_model_instantiation(self):
        """TEST 1: Model can be instantiated with valid biomechanical metrics."""
        fp = MovementFingerprintModel(
            user_id=1,
            exercise_id=1,
            exercise_name="Squat",
            range_of_motion=92.5,
            movement_stability=88.0,
            tempo_control=85.0,
            repetition_consistency=90.0,
            bilateral_symmetry=94.0,
            overall_movement_quality=89.5,
            form_score=95.0,
            repetition_count=10,
            session_duration=45
        )
        self.assertEqual(fp.exercise_name, "Squat")
        self.assertEqual(fp.range_of_motion, 92.5)
        self.assertEqual(fp.bilateral_symmetry, 94.0)

    # --- TEST 2: Fingerprint Persistence & Workout Linking ---
    def test_02_fingerprint_persistence_and_session_linking(self):
        """TEST 2: save_fingerprint persists record linked to workout_sessions.id."""
        auth_data = self._register_user("Persist User", "persist@fitquest.ai")
        user_id = auth_data["user"]["id"]

        session = WorkoutSessionModel(
            user_id=user_id,
            exercise_id=self.ex_squat.id,
            repetitions=12,
            duration_sec=50,
            form_score=92.0
        )
        self.db.add(session)
        self.db.commit()

        m_intel = {
            "movement_signature": {
                "rom_score": 88.0,
                "stability_score": 84.0,
                "tempo_score": 82.0,
                "consistency_score": 86.0,
                "symmetry_score": 90.0,
                "movement_quality_score": 86.5
            }
        }

        fp = movement_fingerprint_service.save_fingerprint(
            db=self.db,
            user_id=user_id,
            exercise_id=self.ex_squat.id,
            exercise_name="Squat",
            movement_intelligence=m_intel,
            workout_session_id=session.id,
            form_score=92.0,
            repetition_count=12,
            session_duration=50
        )

        self.assertIsNotNone(fp)
        self.assertEqual(fp.workout_session_id, session.id)
        self.assertEqual(fp.overall_movement_quality, 86.5)

        # Verify query
        saved = self.db.query(MovementFingerprintModel).filter(
            MovementFingerprintModel.workout_session_id == session.id
        ).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.user_id, user_id)

    # --- TEST 3: Retrieve Authenticated User History ---
    def test_03_retrieve_authenticated_user_history(self):
        """TEST 3: GET /movement-intelligence/history returns user's historical fingerprints."""
        auth_data = self._register_user("History User", "history@fitquest.ai")
        token = auth_data["access_token"]
        user_id = auth_data["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create 2 fingerprints
        for i in range(2):
            movement_fingerprint_service.save_fingerprint(
                db=self.db,
                user_id=user_id,
                exercise_id=self.ex_squat.id,
                exercise_name="Squat",
                movement_intelligence={"movement_signature": {"rom_score": 80 + i, "stability_score": 85, "tempo_score": 80, "consistency_score": 80, "symmetry_score": 85, "movement_quality_score": 82 + i}},
                form_score=90.0,
                repetition_count=10,
                session_duration=40
            )

        res = self.client.get("/api/v1/workouts/movement-intelligence/history", headers=headers)
        self.assertEqual(res.status_code, 200)
        items = res.json()["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["exercise_name"], "Squat")

    # --- TEST 4: Strict Multi-User Isolation ---
    def test_04_multi_user_data_isolation(self):
        """TEST 4: User A cannot see User B's movement fingerprints."""
        user_a = self._register_user("User A", "usera@fitquest.ai")
        user_b = self._register_user("User B", "userb@fitquest.ai")

        # Save fingerprint for User A
        movement_fingerprint_service.save_fingerprint(
            db=self.db,
            user_id=user_a["user"]["id"],
            exercise_id=self.ex_squat.id,
            exercise_name="Squat",
            movement_intelligence={"movement_signature": {"rom_score": 90, "stability_score": 90, "tempo_score": 90, "consistency_score": 90, "symmetry_score": 90, "movement_quality_score": 90}},
            form_score=90.0,
            repetition_count=10,
            session_duration=40
        )

        # User B queries history
        res_b = self.client.get(
            "/api/v1/workouts/movement-intelligence/history",
            headers={"Authorization": f"Bearer {user_b['access_token']}"}
        )
        self.assertEqual(res_b.status_code, 200)
        self.assertEqual(len(res_b.json()["items"]), 0, "User B must not see User A's movement fingerprints!")

    # --- TEST 5: Unauthenticated User Rejection ---
    def test_05_unauthenticated_user_rejection(self):
        """TEST 5: Unauthenticated requests to movement endpoints return 401/403."""
        res = self.client.get("/api/v1/workouts/movement-intelligence/history")
        self.assertIn(res.status_code, [401, 403])

        res_evo = self.client.get("/api/v1/workouts/movement-intelligence/evolution")
        self.assertIn(res_evo.status_code, [401, 403])

    # --- TEST 6: Exercise Filtering ---
    def test_06_exercise_filtering(self):
        """TEST 6: Querying with exercise_id returns only matching exercise records."""
        auth_data = self._register_user("Filter User", "filter@fitquest.ai")
        token = auth_data["access_token"]
        user_id = auth_data["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Add Squat and Lunge fingerprints
        movement_fingerprint_service.save_fingerprint(
            db=self.db,
            user_id=user_id,
            exercise_id=self.ex_squat.id,
            exercise_name="Squat",
            movement_intelligence={"movement_signature": {"rom_score": 85, "stability_score": 85, "tempo_score": 85, "consistency_score": 85, "symmetry_score": 85, "movement_quality_score": 85}}
        )
        movement_fingerprint_service.save_fingerprint(
            db=self.db,
            user_id=user_id,
            exercise_id=self.ex_lunge.id,
            exercise_name="Lunges",
            movement_intelligence={"movement_signature": {"rom_score": 75, "stability_score": 75, "tempo_score": 75, "consistency_score": 75, "symmetry_score": None, "movement_quality_score": 75}}
        )

        res_squat = self.client.get(f"/api/v1/workouts/movement-intelligence/history?exercise_id={self.ex_squat.id}", headers=headers)
        items = res_squat.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["exercise_name"], "Squat")

    # --- TEST 7 & 8: Evolution Baseline (1 session) ---
    def test_07_evolution_baseline_single_session(self):
        """TEST 7 & 8: Single session evolution establishes baseline with 0 change."""
        auth_data = self._register_user("Single Session User", "single@fitquest.ai")
        token = auth_data["access_token"]
        user_id = auth_data["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        movement_fingerprint_service.save_fingerprint(
            db=self.db,
            user_id=user_id,
            exercise_id=self.ex_squat.id,
            exercise_name="Squat",
            movement_intelligence={"movement_signature": {"rom_score": 72.0, "stability_score": 70.0, "tempo_score": 68.0, "consistency_score": 75.0, "symmetry_score": 80.0, "movement_quality_score": 72.5}}
        )

        res = self.client.get(f"/api/v1/workouts/movement-intelligence/evolution?exercise_id={self.ex_squat.id}", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["sessions_analyzed"], 1)
        self.assertEqual(data["overall"]["trend"], "baseline")
        self.assertEqual(data["overall"]["initial"], 72.5)
        self.assertEqual(data["overall"]["latest"], 72.5)
        self.assertEqual(data["overall"]["change"], 0.0)

    # --- TEST 9: Improving Trend Detection ---
    def test_09_improving_trend_detection(self):
        """TEST 9: Multi-session quality gain >= +3% classified as improving."""
        auth_data = self._register_user("Improving User", "improving@fitquest.ai")
        user_id = auth_data["user"]["id"]

        # Session 1: Baseline 70.0
        fp1 = MovementFingerprintModel(
            user_id=user_id,
            exercise_id=self.ex_squat.id,
            exercise_name="Squat",
            range_of_motion=70.0,
            movement_stability=70.0,
            tempo_control=70.0,
            repetition_consistency=70.0,
            bilateral_symmetry=70.0,
            overall_movement_quality=70.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=5)
        )
        # Session 2: Latest 88.0 (+18.0)
        fp2 = MovementFingerprintModel(
            user_id=user_id,
            exercise_id=self.ex_squat.id,
            exercise_name="Squat",
            range_of_motion=88.0,
            movement_stability=86.0,
            tempo_control=84.0,
            repetition_consistency=90.0,
            bilateral_symmetry=92.0,
            overall_movement_quality=88.0,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add_all([fp1, fp2])
        self.db.commit()

        evo = movement_fingerprint_service.calculate_evolution(self.db, user_id, self.ex_squat.id)
        self.assertEqual(evo["sessions_analyzed"], 2)
        self.assertEqual(evo["overall"]["trend"], "improving")
        self.assertEqual(evo["overall"]["change"], 18.0)
        self.assertGreater(evo["overall"]["change_pct"], 20.0)
        self.assertIn("improved", evo["ai_insight"].lower())

    # --- TEST 10: Stable Trend Detection ---
    def test_10_stable_trend_detection(self):
        """TEST 10: Multi-session quality change within +/- 3% classified as stable."""
        auth_data = self._register_user("Stable User", "stable@fitquest.ai")
        user_id = auth_data["user"]["id"]

        fp1 = MovementFingerprintModel(
            user_id=user_id, exercise_id=self.ex_squat.id, exercise_name="Squat",
            range_of_motion=80.0, movement_stability=80.0, tempo_control=80.0,
            repetition_consistency=80.0, bilateral_symmetry=80.0, overall_movement_quality=80.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=2)
        )
        fp2 = MovementFingerprintModel(
            user_id=user_id, exercise_id=self.ex_squat.id, exercise_name="Squat",
            range_of_motion=81.0, movement_stability=80.5, tempo_control=80.0,
            repetition_consistency=81.0, bilateral_symmetry=80.0, overall_movement_quality=80.5,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add_all([fp1, fp2])
        self.db.commit()

        evo = movement_fingerprint_service.calculate_evolution(self.db, user_id, self.ex_squat.id)
        self.assertEqual(evo["overall"]["trend"], "stable")
        self.assertEqual(evo["overall"]["change"], 0.5)

    # --- TEST 11: Declining Trend Detection ---
    def test_11_declining_trend_detection(self):
        """TEST 11: Multi-session quality drop <= -3% classified as declining."""
        auth_data = self._register_user("Declining User", "declining@fitquest.ai")
        user_id = auth_data["user"]["id"]

        fp1 = MovementFingerprintModel(
            user_id=user_id, exercise_id=self.ex_squat.id, exercise_name="Squat",
            range_of_motion=85.0, movement_stability=85.0, tempo_control=85.0,
            repetition_consistency=85.0, bilateral_symmetry=85.0, overall_movement_quality=85.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=3)
        )
        fp2 = MovementFingerprintModel(
            user_id=user_id, exercise_id=self.ex_squat.id, exercise_name="Squat",
            range_of_motion=72.0, movement_stability=70.0, tempo_control=71.0,
            repetition_consistency=74.0, bilateral_symmetry=75.0, overall_movement_quality=72.0,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add_all([fp1, fp2])
        self.db.commit()

        evo = movement_fingerprint_service.calculate_evolution(self.db, user_id, self.ex_squat.id)
        self.assertEqual(evo["overall"]["trend"], "declining")
        self.assertEqual(evo["overall"]["change"], -13.0)

    # --- TEST 12: Missing Symmetry Handling (Unilateral) ---
    def test_12_unilateral_symmetry_handling(self):
        """TEST 12: Unilateral exercise returns bilateral_symmetry = None without breaking evolution."""
        auth_data = self._register_user("Unilateral User", "unilateral@fitquest.ai")
        user_id = auth_data["user"]["id"]

        movement_fingerprint_service.save_fingerprint(
            db=self.db,
            user_id=user_id,
            exercise_id=self.ex_lunge.id,
            exercise_name="Lunges",
            movement_intelligence={"movement_signature": {"rom_score": 82, "stability_score": 80, "tempo_score": 78, "consistency_score": 84, "symmetry_score": None, "movement_quality_score": 81}}
        )

        evo = movement_fingerprint_service.calculate_evolution(self.db, user_id, self.ex_lunge.id)
        self.assertIsNone(evo["metrics"]["symmetry"]["initial"])
        self.assertIsNone(evo["metrics"]["symmetry"]["latest"])
        self.assertFalse(evo["metrics"]["symmetry"]["available"])
        self.assertEqual(evo["overall"]["latest"], 81.0)

    # --- TEST 13: Zero/Empty History Graceful Handling ---
    def test_13_zero_history_graceful_handling(self):
        """TEST 13: Zero historical sessions returns structured empty state with helpful guidance."""
        auth_data = self._register_user("Empty User", "empty@fitquest.ai")
        user_id = auth_data["user"]["id"]

        evo = movement_fingerprint_service.calculate_evolution(self.db, user_id, self.ex_squat.id)
        self.assertEqual(evo["sessions_analyzed"], 0)
        self.assertEqual(evo["overall"]["trend"], "baseline")
        self.assertEqual(len(evo["timeline"]), 0)
        self.assertIn("No movement history", evo["ai_insight"])

    # --- TEST 14: Duplicate Session Protection ---
    def test_14_duplicate_session_protection(self):
        """TEST 14: Calling save_fingerprint multiple times for same workout_session_id does not duplicate."""
        auth_data = self._register_user("Dedup User", "dedup@fitquest.ai")
        user_id = auth_data["user"]["id"]

        session = WorkoutSessionModel(user_id=user_id, exercise_id=self.ex_squat.id, repetitions=10, duration_sec=40, form_score=90.0)
        self.db.add(session)
        self.db.commit()

        m_intel = {"movement_signature": {"rom_score": 85, "stability_score": 85, "tempo_score": 85, "consistency_score": 85, "symmetry_score": 85, "movement_quality_score": 85}}

        fp1 = movement_fingerprint_service.save_fingerprint(
            db=self.db, user_id=user_id, exercise_id=self.ex_squat.id, exercise_name="Squat",
            movement_intelligence=m_intel, workout_session_id=session.id
        )
        fp2 = movement_fingerprint_service.save_fingerprint(
            db=self.db, user_id=user_id, exercise_id=self.ex_squat.id, exercise_name="Squat",
            movement_intelligence=m_intel, workout_session_id=session.id
        )

        self.assertEqual(fp1.id, fp2.id)
        total_fps = self.db.query(MovementFingerprintModel).filter(
            MovementFingerprintModel.workout_session_id == session.id
        ).count()
        self.assertEqual(total_fps, 1, "Duplicate fingerprints must not be created for the same session.")

    # --- TEST 15: Session Historical Comparison Endpoint ---
    def test_15_session_comparison_endpoint(self):
        """TEST 15: GET /movement-intelligence/comparison returns this_session vs previous_avg."""
        auth_data = self._register_user("Compare User", "compare@fitquest.ai")
        token = auth_data["access_token"]
        user_id = auth_data["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Add 2 historical sessions with avg 80.0
        for i in [78.0, 82.0]:
            movement_fingerprint_service.save_fingerprint(
                db=self.db, user_id=user_id, exercise_id=self.ex_squat.id, exercise_name="Squat",
                movement_intelligence={"movement_signature": {"rom_score": i, "stability_score": i, "tempo_score": i, "consistency_score": i, "symmetry_score": i, "movement_quality_score": i}}
            )

        # Compare current 88.0 score
        res = self.client.get(
            f"/api/v1/workouts/movement-intelligence/comparison?exercise_id={self.ex_squat.id}&quality_score=88.0",
            headers=headers
        )
        self.assertEqual(res.status_code, 200)
        comp = res.json()
        self.assertTrue(comp["has_history"])
        self.assertEqual(comp["this_session"], 88.0)
        self.assertEqual(comp["previous_avg"], 80.0)
        self.assertEqual(comp["change"], 8.0)
        self.assertEqual(comp["trend"], "improving")

    # --- TEST 16: Automatic Persistence on Workout Ingest ---
    def test_16_automatic_fingerprint_persistence_during_workout_ingest(self):
        """TEST 16: POST /api/v1/workouts automatically persists MovementFingerprintModel."""
        auth_data = self._register_user("Auto Persist User", "autopersist@fitquest.ai")
        token = auth_data["access_token"]
        user_id = auth_data["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "session_data": {
                "user_id": user_id,
                "exercise_id": self.ex_squat.id,
                "repetitions": 12,
                "duration_sec": 45,
                "form_score": 92.0
            },
            "movement_intelligence": {
                "movement_signature": {
                    "rom_score": 88.0,
                    "stability_score": 85.0,
                    "tempo_score": 82.0,
                    "consistency_score": 89.0,
                    "symmetry_score": 91.0,
                    "movement_quality_score": 87.0
                }
            }
        }

        res = self.client.post("/api/v1/workouts", json=payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        workout_session_id = res.json()["id"]

        # Verify fingerprint was automatically persisted
        saved_fp = self.db.query(MovementFingerprintModel).filter(
            MovementFingerprintModel.workout_session_id == workout_session_id
        ).first()

        self.assertIsNotNone(saved_fp)
        self.assertEqual(saved_fp.user_id, user_id)
        self.assertEqual(saved_fp.overall_movement_quality, 87.0)
        self.assertEqual(saved_fp.range_of_motion, 88.0)
        self.assertEqual(saved_fp.bilateral_symmetry, 91.0)


if __name__ == "__main__":
    unittest.main()
