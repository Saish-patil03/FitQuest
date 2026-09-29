#!/usr/bin/env python3
"""
Unit & Integration Test Suite for FitQuest Closed-Loop Adaptive AI Training Engine (Phase 3).

Verifies:
1. Adaptive profile creation with valid movement history
2. Graceful empty history handling (zero workouts)
3. Single-session baseline profile generation
4. Primary and secondary weakness identification
5. Strongest metric identification
6. Declining metric detection across historical sessions
7. Improving metric detection across historical sessions
8. Exercise recommendation scoring and priority ranking
9. Full adaptive workout generation with exercises, sets, reps, and tempos
10. Explainability rationale generation for recommended exercises
11. Adaptation confidence score calculation (Low / Moderate / High)
12. Difficulty & volume adaptation based on historical movement quality
13. Strict multi-tenant data isolation (User A vs User B)
14. Unauthenticated user request rejection (401/403)
15. REST API endpoint validation (/profile, /recommendations, /generate, /latest, /impact)
16. Interoperability with structured workout execution pipeline
17. Full closed-loop feedback verification (history -> adapt -> simulate session -> impact)
"""

import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import (
    UserModel,
    ExerciseModel,
    WorkoutSessionModel,
    MovementFingerprintModel,
    StructuredWorkoutSessionModel
)
from backend.services.adaptive_training import adaptive_training_engine
from backend.services.movement_fingerprint_service import movement_fingerprint_service

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


class TestAdaptiveTrainingEngine(unittest.TestCase):
    """
    Comprehensive test suite for Phase 3 Adaptive Training Engine.
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
        self.db.query(MovementFingerprintModel).delete()
        self.db.query(StructuredWorkoutSessionModel).delete()
        self.db.query(WorkoutSessionModel).delete()
        self.db.query(UserModel).delete()
        self.db.query(ExerciseModel).delete()
        self.db.commit()

        # Seed key test exercises
        self.ex_squat = ExerciseModel(id=2, name="Squat", difficulty="Intermediate", description="Squat exercise")
        self.ex_pushup = ExerciseModel(id=3, name="Push-up", difficulty="Intermediate", description="Push-up exercise")
        self.ex_lunge = ExerciseModel(id=4, name="Lunges", difficulty="Intermediate", description="Lunges exercise")
        self.ex_bridge = ExerciseModel(id=10, name="Glute Bridge", difficulty="Beginner", description="Glute Bridge exercise")
        self.db.add_all([self.ex_squat, self.ex_pushup, self.ex_lunge, self.ex_bridge])
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

    # --- TEST 1 & 2: Empty History Profile Handling ---
    def test_01_empty_history_profile_handling(self):
        """TEST 1 & 2: Empty workout history returns structured default profile with Low confidence."""
        auth = self._register_user("New User", "new@fitquest.ai")
        user_id = auth["user"]["id"]

        profile = adaptive_training_engine.get_user_adaptive_profile(self.db, user_id)
        self.assertEqual(profile["total_sessions_analyzed"], 0)
        self.assertEqual(profile["confidence"], "Low")
        self.assertIn("first workout", profile["summary_insight"].lower())
        self.assertEqual(profile["metric_status"]["range_of_motion"], "N/A")

    # --- TEST 3: Single-Session Baseline Profile Generation ---
    def test_02_single_session_baseline_profile(self):
        """TEST 3: Single session establishes baseline with Low/Baseline confidence."""
        auth = self._register_user("Baseline User", "baseline@fitquest.ai")
        user_id = auth["user"]["id"]

        # 1 Squat session: ROM 92, Stability 65, Tempo 60, Consistency 75, Symmetry 88
        fp = MovementFingerprintModel(
            user_id=user_id, exercise_id=2, exercise_name="Squat",
            range_of_motion=92.0, movement_stability=65.0, tempo_control=60.0,
            repetition_consistency=75.0, bilateral_symmetry=88.0, overall_movement_quality=76.0,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(fp)
        self.db.commit()

        profile = adaptive_training_engine.get_user_adaptive_profile(self.db, user_id)
        self.assertEqual(profile["total_sessions_analyzed"], 1)
        self.assertEqual(profile["confidence"], "Low")
        self.assertEqual(profile["weakest_area"], "tempo_control")
        self.assertEqual(profile["strongest_area"], "range_of_motion")

    # --- TEST 4 & 5: Weakness & Strength Identification ---
    def test_03_weakness_and_strength_identification(self):
        """TEST 4 & 5: Correctly identifies lowest limiter and strongest biomechanical metric."""
        auth = self._register_user("Limiter User", "limiter@fitquest.ai")
        user_id = auth["user"]["id"]

        # Multi-session: Stability is lowest (58.0), Tempo is secondary (64.0), ROM is strongest (94.0)
        for i in range(3):
            fp = MovementFingerprintModel(
                user_id=user_id, exercise_id=2, exercise_name="Squat",
                range_of_motion=94.0, movement_stability=58.0, tempo_control=64.0,
                repetition_consistency=80.0, bilateral_symmetry=90.0, overall_movement_quality=77.0,
                created_at=datetime.now(timezone.utc) - timedelta(days=3 - i)
            )
            self.db.add(fp)
        self.db.commit()

        profile = adaptive_training_engine.get_user_adaptive_profile(self.db, user_id)
        self.assertEqual(profile["primary_focus"], "movement_stability")
        self.assertEqual(profile["secondary_focus"], "tempo_control")
        self.assertEqual(profile["strongest_area"], "range_of_motion")
        self.assertEqual(profile["metric_status"]["movement_stability"], "NEEDS ATTENTION")
        self.assertEqual(profile["metric_status"]["range_of_motion"], "STRONG")

    # --- TEST 6 & 7: Declining & Improving Metric Trajectories ---
    def test_04_declining_and_improving_metric_detection(self):
        """TEST 6 & 7: Detects exercise-specific declining and improving trends."""
        auth = self._register_user("Trend User", "trend@fitquest.ai")
        user_id = auth["user"]["id"]

        # Squat declining: 85.0 -> 72.0 (-13.0)
        fp_sq1 = MovementFingerprintModel(
            user_id=user_id, exercise_id=2, exercise_name="Squat",
            range_of_motion=85.0, movement_stability=85.0, tempo_control=85.0,
            repetition_consistency=85.0, bilateral_symmetry=85.0, overall_movement_quality=85.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=4)
        )
        fp_sq2 = MovementFingerprintModel(
            user_id=user_id, exercise_id=2, exercise_name="Squat",
            range_of_motion=72.0, movement_stability=70.0, tempo_control=71.0,
            repetition_consistency=74.0, bilateral_symmetry=75.0, overall_movement_quality=72.0,
            created_at=datetime.now(timezone.utc)
        )
        # Push-up improving: 70.0 -> 88.0 (+18.0)
        fp_pu1 = MovementFingerprintModel(
            user_id=user_id, exercise_id=3, exercise_name="Push-up",
            range_of_motion=70.0, movement_stability=70.0, tempo_control=70.0,
            repetition_consistency=70.0, bilateral_symmetry=70.0, overall_movement_quality=70.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=4)
        )
        fp_pu2 = MovementFingerprintModel(
            user_id=user_id, exercise_id=3, exercise_name="Push-up",
            range_of_motion=88.0, movement_stability=88.0, tempo_control=88.0,
            repetition_consistency=88.0, bilateral_symmetry=88.0, overall_movement_quality=88.0,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add_all([fp_sq1, fp_sq2, fp_pu1, fp_pu2])
        self.db.commit()

        profile = adaptive_training_engine.get_user_adaptive_profile(self.db, user_id)
        self.assertIn("Squat", profile["declining_exercises"])
        self.assertIn("Push-up", profile["improving_exercises"])

    # --- TEST 8: Exercise Recommendation Scoring & Priority Ranking ---
    def test_05_exercise_recommendation_scoring(self):
        """TEST 8: Ranks exercises addressing user's primary/secondary biomechanical needs."""
        auth = self._register_user("Rec User", "rec@fitquest.ai")
        user_id = auth["user"]["id"]

        # Set Stability as primary limiter
        for _ in range(2):
            fp = MovementFingerprintModel(
                user_id=user_id, exercise_id=2, exercise_name="Squat",
                range_of_motion=90.0, movement_stability=55.0, tempo_control=75.0,
                repetition_consistency=85.0, bilateral_symmetry=90.0, overall_movement_quality=79.0
            )
            self.db.add(fp)
        self.db.commit()

        recs = adaptive_training_engine.get_exercise_recommendations(self.db, user_id)
        self.assertGreater(len(recs), 0)
        # Top recommendations must include stability-focused exercises
        top_names = [r["exercise_name"] for r in recs[:5]]
        self.assertTrue(any(ex in top_names for ex in ["Plank", "Glute Bridge", "Lunges", "Squat"]))
        self.assertIn(recs[0]["priority"], ["HIGH", "OPTIMAL"])

    # --- TEST 9 & 10: Full Adaptive Workout Generation & Explainability ---
    def test_06_adaptive_workout_generation_and_explainability(self):
        """TEST 9 & 10: Generates multi-exercise plan with custom tempos, cues, and explainability."""
        auth = self._register_user("Workout Gen User", "gen@fitquest.ai")
        user_id = auth["user"]["id"]

        for _ in range(3):
            fp = MovementFingerprintModel(
                user_id=user_id, exercise_id=2, exercise_name="Squat",
                range_of_motion=92.0, movement_stability=58.0, tempo_control=68.0,
                repetition_consistency=80.0, bilateral_symmetry=90.0, overall_movement_quality=76.8
            )
            self.db.add(fp)
        self.db.commit()

        plan = adaptive_training_engine.generate_adaptive_workout(self.db, user_id, target_duration_min=20)
        self.assertIsNotNone(plan)
        self.assertIn("Adaptive Session", plan["title"])
        self.assertIn("Movement Stability", plan["title"])
        self.assertGreaterEqual(len(plan["exercises"]), 3)

        first_ex = plan["exercises"][0]
        self.assertIn("target_tempo", first_ex)
        self.assertIn("focus", first_ex)
        self.assertIn("selection_reason", first_ex)
        self.assertTrue(len(first_ex["selection_reason"]) > 10, "Explainable rationale must be provided.")

    # --- TEST 11: Adaptation Confidence Calculation ---
    def test_07_adaptation_confidence_scaling(self):
        """TEST 11: Confidence scales from Low (1 session) to Moderate (2-3) to High (4+)."""
        auth = self._register_user("Confidence User", "conf@fitquest.ai")
        user_id = auth["user"]["id"]

        # 1 session -> Low
        fp1 = MovementFingerprintModel(user_id=user_id, exercise_id=2, exercise_name="Squat", range_of_motion=80, movement_stability=80, tempo_control=80, repetition_consistency=80, overall_movement_quality=80)
        self.db.add(fp1)
        self.db.commit()
        prof1 = adaptive_training_engine.get_user_adaptive_profile(self.db, user_id)
        self.assertEqual(prof1["confidence"], "Low")

        # 3 sessions -> Moderate
        for _ in range(2):
            self.db.add(MovementFingerprintModel(user_id=user_id, exercise_id=2, exercise_name="Squat", range_of_motion=80, movement_stability=80, tempo_control=80, repetition_consistency=80, overall_movement_quality=80))
        self.db.commit()
        prof3 = adaptive_training_engine.get_user_adaptive_profile(self.db, user_id)
        self.assertEqual(prof3["confidence"], "Moderate")

        # 5 sessions -> High
        for _ in range(2):
            self.db.add(MovementFingerprintModel(user_id=user_id, exercise_id=2, exercise_name="Squat", range_of_motion=80, movement_stability=80, tempo_control=80, repetition_consistency=80, overall_movement_quality=80))
        self.db.commit()
        prof5 = adaptive_training_engine.get_user_adaptive_profile(self.db, user_id)
        self.assertEqual(prof5["confidence"], "High")

    # --- TEST 12: Difficulty Adaptation ---
    def test_08_difficulty_adaptation(self):
        """TEST 12: Adapts workout difficulty and tempo cues according to movement limiter."""
        auth = self._register_user("Diff User", "diff@fitquest.ai")
        user_id = auth["user"]["id"]

        fp = MovementFingerprintModel(
            user_id=user_id, exercise_id=2, exercise_name="Squat",
            range_of_motion=85.0, movement_stability=50.0, tempo_control=52.0,
            repetition_consistency=80.0, bilateral_symmetry=85.0, overall_movement_quality=70.0
        )
        self.db.add(fp)
        self.db.commit()

        plan = adaptive_training_engine.generate_adaptive_workout(self.db, user_id)
        # For low stability/tempo, tempo should emphasize eccentric descent (e.g. 2-1-2 or 3-1-2)
        tempos = [e["target_tempo"] for e in plan["exercises"]]
        self.assertTrue(any("3-1-2" in t or "2-1-2" in t for t in tempos))

    # --- TEST 13: Strict Multi-Tenant Data Isolation ---
    def test_09_multi_tenant_isolation(self):
        """TEST 13: User A's adaptive profile cannot see User B's movement history."""
        user_a = self._register_user("User A", "user_a@fitquest.ai")
        user_b = self._register_user("User B", "user_b@fitquest.ai")

        # Save 3 low-stability sessions for User A
        for _ in range(3):
            self.db.add(MovementFingerprintModel(
                user_id=user_a["user"]["id"], exercise_id=2, exercise_name="Squat",
                range_of_motion=95.0, movement_stability=40.0, tempo_control=85.0,
                repetition_consistency=85.0, bilateral_symmetry=90.0, overall_movement_quality=79.0
            ))
        self.db.commit()

        # User B queries profile via API
        res_b = self.client.get(
            "/api/v1/adaptive-training/profile",
            headers={"Authorization": f"Bearer {user_b['access_token']}"}
        )
        self.assertEqual(res_b.status_code, 200)
        profile_b = res_b.json()
        self.assertEqual(profile_b["total_sessions_analyzed"], 0, "User B must have 0 sessions!")
        self.assertEqual(profile_b["confidence"], "Low")

    # --- TEST 14: Unauthenticated Request Rejection ---
    def test_10_unauthenticated_request_rejection(self):
        """TEST 14: Unauthenticated API calls return 401/403."""
        endpoints = [
            "/api/v1/adaptive-training/profile",
            "/api/v1/adaptive-training/recommendations",
            "/api/v1/adaptive-training/generate",
            "/api/v1/adaptive-training/latest"
        ]
        for ep in endpoints:
            if "generate" in ep:
                res = self.client.post(ep)
            else:
                res = self.client.get(ep)
            self.assertIn(res.status_code, [401, 403], f"Endpoint {ep} must require auth.")

    # --- TEST 15: REST API Endpoint Validation ---
    def test_11_rest_api_endpoint_validation(self):
        """TEST 15: All adaptive endpoints return valid status 200/201 with correct schemas."""
        auth = self._register_user("API User", "api_user@fitquest.ai")
        headers = {"Authorization": f"Bearer {auth['access_token']}"}
        user_id = auth["user"]["id"]

        # Seed 2 sessions
        for _ in range(2):
            self.db.add(MovementFingerprintModel(
                user_id=user_id, exercise_id=2, exercise_name="Squat",
                range_of_motion=88.0, movement_stability=70.0, tempo_control=68.0,
                repetition_consistency=82.0, bilateral_symmetry=85.0, overall_movement_quality=78.6
            ))
        self.db.commit()

        # 1. GET /profile
        res_prof = self.client.get("/api/v1/adaptive-training/profile", headers=headers)
        self.assertEqual(res_prof.status_code, 200)
        self.assertEqual(res_prof.json()["total_sessions_analyzed"], 2)

        # 2. GET /recommendations
        res_recs = self.client.get("/api/v1/adaptive-training/recommendations", headers=headers)
        self.assertEqual(res_recs.status_code, 200)
        self.assertIsInstance(res_recs.json(), list)

        # 3. POST /generate
        res_gen = self.client.post("/api/v1/adaptive-training/generate", headers=headers)
        self.assertEqual(res_gen.status_code, 200)
        plan = res_gen.json()
        self.assertIn("exercises", plan)

        # 4. GET /latest
        res_latest = self.client.get("/api/v1/adaptive-training/latest", headers=headers)
        self.assertEqual(res_latest.status_code, 200)

        # 5. GET /impact
        res_impact = self.client.get(f"/api/v1/adaptive-training/impact?exercise_id=2", headers=headers)
        self.assertEqual(res_impact.status_code, 200)
        self.assertTrue(res_impact.json()["has_history"])

    # --- TEST 16: Interoperability with Structured Workout Pipeline ---
    def test_12_structured_workout_pipeline_interoperability(self):
        """TEST 16: Generated adaptive plan can be directly passed to structured workout start."""
        auth = self._register_user("Interoperable User", "interop@fitquest.ai")
        token = auth["access_token"]
        user_id = auth["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Generate adaptive plan
        res_gen = self.client.post("/api/v1/adaptive-training/generate", headers=headers)
        plan = res_gen.json()

        # Start structured workout using generated custom_exercises
        start_payload = {
            "title": plan["title"],
            "category": plan["category"],
            "custom_exercises": plan["exercises"]
        }
        res_start = self.client.post("/api/v1/structured-workouts/start", json=start_payload, headers=headers)
        self.assertEqual(res_start.status_code, 201)
        session_data = res_start.json()
        self.assertEqual(session_data["plan_title"], plan["title"])
        self.assertEqual(session_data["total_exercises"], len(plan["exercises"]))

    # --- TEST 17: Full Closed-Loop Feedback Verification ---
    def test_13_full_closed_loop_feedback_verification(self):
        """TEST 17: Closed-loop verification: History -> Adapt -> Simulate Workout -> Impact Evaluation."""
        auth = self._register_user("Closed Loop User", "closedloop@fitquest.ai")
        token = auth["access_token"]
        user_id = auth["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Baseline session with low stability: 58.0
        fp1 = MovementFingerprintModel(
            user_id=user_id, exercise_id=2, exercise_name="Squat",
            range_of_motion=88.0, movement_stability=58.0, tempo_control=70.0,
            repetition_consistency=80.0, bilateral_symmetry=85.0, overall_movement_quality=76.2,
            created_at=datetime.now(timezone.utc) - timedelta(days=2)
        )
        self.db.add(fp1)
        self.db.commit()

        # 2. Adaptive profile identifies Stability as limiter
        prof_before = adaptive_training_engine.get_user_adaptive_profile(self.db, user_id)
        self.assertEqual(prof_before["primary_focus"], "movement_stability")

        # 3. User performs adapted session -> stability improves to 78.0 (+20.0 pts)
        fp2 = MovementFingerprintModel(
            user_id=user_id, exercise_id=2, exercise_name="Squat",
            range_of_motion=90.0, movement_stability=78.0, tempo_control=76.0,
            repetition_consistency=85.0, bilateral_symmetry=90.0, overall_movement_quality=83.8,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(fp2)
        self.db.commit()

        # 4. Evaluate Adaptation Impact
        impact = adaptive_training_engine.get_adaptation_impact(self.db, user_id, 2)
        self.assertTrue(impact["has_history"])
        self.assertEqual(impact["trend"], "improving")
        self.assertGreater(impact["change_stability"], 15.0)
        self.assertIn("improved", impact["message"].lower())


if __name__ == "__main__":
    unittest.main()
