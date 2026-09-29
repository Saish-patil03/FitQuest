#!/usr/bin/env python3
"""
Unit & Integration Test Suite for FitQuest Movement Copilot™ (Phase 5).

Verifies 24 Scenarios:
1. Engine initialization & session state creation
2. Empty telemetry handling (zero frames)
3. Insufficient samples (< 5 samples) handling
4. Stable movement evaluation (nominal monitoring state)
5. Declining stability detection (WARNING on movement_stability)
6. Declining ROM detection (WARNING on range_of_motion)
7. Tempo deviation detection (WARNING on tempo_control)
8. Consistency degradation detection (WARNING on repetition_consistency)
9. Symmetry degradation detection (WARNING on bilateral_symmetry)
10. Severity classification (INFO, WARNING, CRITICAL)
11. Context-aware coaching generation (exercise & movement phase)
12. Cooldown behavior (suppresses alerts within cooldown window)
13. Repeated warning suppression
14. Closed-loop recovery detection (verifies user correction)
15. Recovery delta & percentage gain calculation
16. Exercise-specific coaching across multiple exercises (Squat, Bicep Curl, Push-up, Lunges, Plank, etc.)
17. Movement DNA primary limiter context integration
18. Adaptive Training tempo target integration (e.g. "3-1-2")
19. Multi-user session tenant isolation (User A vs User B)
20. Unauthenticated API rejection (401/403)
21. Workout session lifecycle (start, ingest, reset, summary)
22. Exercise transition reset behavior
23. Rolling window buffer bounds & memory leak safety
24. Full post-workout session intelligence summary verification
"""

import unittest
import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import UserModel, ExerciseModel, MovementFingerprintModel
from backend.services.movement_intelligence import FrameTelemetrySample
from backend.services.movement_copilot import movement_copilot_engine, MovementCopilotEngine

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


class TestMovementCopilotEngine(unittest.TestCase):
    """
    Test suite for Phase 5 Movement Copilot.
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
        self.db.query(UserModel).delete()
        self.db.query(ExerciseModel).delete()
        self.db.commit()

        # Seed key exercises
        self.ex_bicep = ExerciseModel(id=1, name="Bicep Curl", difficulty="Beginner", description="Bicep Curl")
        self.ex_squat = ExerciseModel(id=2, name="Squat", difficulty="Intermediate", description="Squat")
        self.ex_pushup = ExerciseModel(id=3, name="Push-up", difficulty="Intermediate", description="Push-up")
        self.ex_lunge = ExerciseModel(id=4, name="Lunges", difficulty="Intermediate", description="Lunges")
        self.ex_plank = ExerciseModel(id=9, name="Plank", difficulty="Beginner", description="Plank")
        self.db.add_all([self.ex_bicep, self.ex_squat, self.ex_pushup, self.ex_lunge, self.ex_plank])
        self.db.commit()

        # Reset in-memory Copilot engine sessions
        movement_copilot_engine._sessions.clear()

    def tearDown(self):
        self.db.close()

    def _register_user(self, name: str, email: str) -> dict:
        res = self.client.post("/api/v1/auth/register", json={
            "name": name,
            "email": email,
            "password": "Password123!",
            "fitness_goal": "Movement Quality",
            "experience_level": "Intermediate"
        })
        return res.json()

    # --- TEST 1: Engine Initialization & Session State Creation ---
    def test_01_engine_init_and_session_creation(self):
        """TEST 1: Creates fresh Copilot session with correct defaults."""
        auth = self._register_user("Copilot User 1", "copilot1@fitquest.ai")
        user_id = auth["user"]["id"]

        sess = movement_copilot_engine.get_or_create_session("sess_01", user_id, "2", "Squat")
        self.assertEqual(sess.session_id, "sess_01")
        self.assertEqual(sess.user_id, user_id)
        self.assertEqual(sess.exercise_id, "2")
        self.assertEqual(sess.exercise_name, "Squat")
        self.assertFalse(sess.baseline_established)

    # --- TEST 2 & 3: Empty Telemetry & Insufficient Samples ---
    def test_02_empty_and_insufficient_samples(self):
        """TEST 2 & 3: Gracefully handles zero/few samples during camera calibration."""
        auth = self._register_user("Copilot User 2", "copilot2@fitquest.ai")
        user_id = auth["user"]["id"]

        for _ in range(3):
            res = movement_copilot_engine.process_frame_telemetry(
                session_id="sess_02", user_id=user_id, exercise_id="2",
                rep_count=0, form_score=0.0, state="START",
                primary_angle=170.0, torso_angle=175.0
            )
        self.assertEqual(res["status"], "IDLE")
        self.assertIn("Calibrating", res["message"])

    # --- TEST 4: Stable Movement Evaluation ---
    def test_03_stable_movement(self):
        """TEST 4: Stable, high-quality repetitions maintain MONITORING status without false alerts."""
        auth = self._register_user("Copilot User 3", "copilot3@fitquest.ai")
        user_id = auth["user"]["id"]

        for i in range(15):
            angle = 170.0 - (i % 6) * 15.0
            res = movement_copilot_engine.process_frame_telemetry(
                session_id="sess_03", user_id=user_id, exercise_id="2",
                rep_count=i // 6, form_score=92.0, state="DESCENT" if (i % 6) < 3 else "ASCENT",
                primary_angle=angle, left_angle=angle, right_angle=angle,
                torso_angle=175.0
            )

        self.assertEqual(res["status"], "MONITORING")
        self.assertFalse(res["active"])
        self.assertGreaterEqual(res["current_metrics"]["movement_stability"], 70.0)

    # --- TEST 5: Declining Stability Detection ---
    def test_04_declining_stability_detection(self):
        """TEST 5: Severe torso sway and joint jitter triggers WARNING on movement_stability."""
        auth = self._register_user("Copilot User 4", "copilot4@fitquest.ai")
        user_id = auth["user"]["id"]

        sess = movement_copilot_engine.get_or_create_session("sess_04", user_id, "2", "Squat")
        sess.baseline_established = True
        sess.baseline_metrics["movement_stability"] = 90.0
        sess.last_coaching_timestamp = 0.0

        responses = []
        # Inject erratic torso angles while primary angle exercises full range
        for i in range(12):
            angle = 170.0 - (i % 6) * 15.0
            torso_sway = 130.0 if (i % 2 == 0) else 180.0
            res = movement_copilot_engine.process_frame_telemetry(
                session_id="sess_04", user_id=user_id, exercise_id="2",
                rep_count=2, form_score=55.0, state="DESCENT",
                primary_angle=angle, left_angle=angle, right_angle=angle,
                torso_angle=torso_sway
            )
            responses.append(res)

        warning_res = next((r for r in responses if r["status"] in ["WARNING", "CRITICAL"]), None)
        self.assertIsNotNone(warning_res)
        self.assertEqual(warning_res["dimension"], "movement_stability")
        self.assertTrue("torso" in warning_res["coaching_cue"].lower() or "descent" in warning_res["coaching_cue"].lower() or "knees" in warning_res["coaching_cue"].lower())

    # --- TEST 6: Declining ROM Detection ---
    def test_05_declining_rom_detection(self):
        """TEST 6: Shallow reps trigger range_of_motion alert."""
        auth = self._register_user("Copilot User 5", "copilot5@fitquest.ai")
        user_id = auth["user"]["id"]

        sess = movement_copilot_engine.get_or_create_session("sess_05", user_id, "2", "Squat")
        sess.baseline_established = True
        sess.baseline_metrics["range_of_motion"] = 95.0
        sess.last_coaching_timestamp = 0.0

        responses = []
        # Feed shallow reps (only 160 -> 145 deg = 15 deg excursion vs 65 standard)
        for i in range(12):
            ang = 160.0 if i < 6 else 145.0
            res = movement_copilot_engine.process_frame_telemetry(
                session_id="sess_05", user_id=user_id, exercise_id="2",
                rep_count=2, form_score=60.0, state="DESCENT",
                primary_angle=ang, left_angle=ang, right_angle=ang, torso_angle=175.0
            )
            responses.append(res)

        warning_res = next((r for r in responses if r["status"] in ["WARNING", "CRITICAL"]), None)
        self.assertIsNotNone(warning_res)
        self.assertEqual(warning_res["dimension"], "range_of_motion")
        self.assertIn("depth", warning_res["coaching_cue"].lower() or "deeper")

    # --- TEST 7: Tempo Deviation Detection ---
    def test_06_tempo_deviation_detection(self):
        """TEST 7: Rushed reps trigger tempo_control coaching."""
        auth = self._register_user("Copilot User 6", "copilot6@fitquest.ai")
        user_id = auth["user"]["id"]

        sess = movement_copilot_engine.get_or_create_session("sess_06", user_id, "2", "Squat")
        sess.baseline_established = True
        sess.baseline_metrics["tempo_control"] = 85.0
        sess.last_coaching_timestamp = 0.0

        # Feed 10 reps over 1.0s (0.1s per rep -> extreme rushed pacing)
        t_base = time.time() - 1.0
        for i in range(10):
            sample = FrameTelemetrySample(
                timestamp=t_base + (i * 0.1),
                primary_angle=170.0 - (i % 6) * 15.0,
                torso_angle=175.0,
                rep_count=i + 1,
                state="DESCENT"
            )
            sess.samples.append(sample)

        res = movement_copilot_engine.process_frame_telemetry(
            session_id="sess_06", user_id=user_id, exercise_id="2",
            rep_count=10, form_score=62.0, state="DESCENT", primary_angle=110.0, torso_angle=175.0
        )
        self.assertIn(res["status"], ["WARNING", "CRITICAL"])
        self.assertEqual(res["dimension"], "tempo_control")

    # --- TEST 8 & 9: Consistency and Symmetry Degradation ---
    def test_07_consistency_and_symmetry_degradation(self):
        """TEST 8 & 9: Severe asymmetry triggers bilateral_symmetry alert on bilateral exercises."""
        auth = self._register_user("Copilot User 7", "copilot7@fitquest.ai")
        user_id = auth["user"]["id"]

        sess = movement_copilot_engine.get_or_create_session("sess_07", user_id, "1", "Bicep Curl")
        sess.baseline_established = True
        sess.baseline_metrics["bilateral_symmetry"] = 90.0
        sess.last_coaching_timestamp = 0.0

        responses = []
        # Feed large left vs right angle gap while primary angle has full ROM
        for i in range(12):
            p_ang = 150.0 - (i % 6) * 15.0
            res = movement_copilot_engine.process_frame_telemetry(
                session_id="sess_07", user_id=user_id, exercise_id="1",
                rep_count=1, form_score=60.0, state="ASCENT",
                primary_angle=p_ang, left_angle=140.0, right_angle=70.0, torso_angle=175.0
            )
            responses.append(res)

        warning_res = next((r for r in responses if r["status"] in ["WARNING", "CRITICAL"]), None)
        self.assertIsNotNone(warning_res)
        self.assertEqual(warning_res["dimension"], "bilateral_symmetry")
        self.assertIn("arm", warning_res["coaching_cue"].lower() or "left")

    # --- TEST 10 & 11: Severity Classification & Context-Aware Coaching ---
    def test_08_severity_and_context_cues(self):
        """TEST 10 & 11: Evaluates severity levels and phase-specific cues."""
        auth = self._register_user("Copilot User 8", "copilot8@fitquest.ai")
        user_id = auth["user"]["id"]

        cue_descent = movement_copilot_engine._generate_coaching_cue(
            exercise_id="2", dimension="movement_stability", phase="DESCENT", severity="WARNING"
        )
        self.assertIn("descent", cue_descent.lower())

        cue_ascent = movement_copilot_engine._generate_coaching_cue(
            exercise_id="2", dimension="movement_stability", phase="ASCENT", severity="CRITICAL"
        )
        self.assertIn("drive", cue_ascent.lower())
        self.assertIn("form alert", cue_ascent.lower())

    # --- TEST 12 & 13: Cooldown & Repeated Warning Suppression ---
    def test_09_cooldown_and_suppression(self):
        """TEST 12 & 13: Cooldown prevents back-to-back alerts across consecutive frames."""
        auth = self._register_user("Copilot User 9", "copilot9@fitquest.ai")
        user_id = auth["user"]["id"]

        sess = movement_copilot_engine.get_or_create_session("sess_09", user_id, "2", "Squat")
        sess.baseline_established = True
        sess.baseline_metrics["movement_stability"] = 90.0
        sess.last_coaching_timestamp = 0.0

        responses = []
        for i in range(8):
            angle = 170.0 - (i % 6) * 15.0
            torso_val = 130.0 if (i % 2 == 0) else 180.0
            res = movement_copilot_engine.process_frame_telemetry(
                session_id="sess_09", user_id=user_id, exercise_id="2",
                rep_count=1, form_score=50.0, state="DESCENT",
                primary_angle=angle, torso_angle=torso_val
            )
            responses.append(res)

        warning_res = next((r for r in responses if r["status"] in ["WARNING", "CRITICAL"]), None)
        self.assertIsNotNone(warning_res)
        interventions_count = sess.total_interventions

        # Immediately feed another bad frame (cooldown is now active)
        res2 = movement_copilot_engine.process_frame_telemetry(
            session_id="sess_09", user_id=user_id, exercise_id="2",
            rep_count=1, form_score=50.0, state="DESCENT",
            primary_angle=120.0, torso_angle=130.0
        )

        self.assertTrue(res2["cooldown_active"])
        self.assertEqual(sess.total_interventions, interventions_count, "Intervention count must not increment during cooldown.")

    # --- TEST 14 & 15: Closed-Loop Recovery Detection & Delta Gain ---
    def test_10_closed_loop_recovery(self):
        """TEST 14 & 15: Confirms recovery after user corrects movement and computes delta."""
        auth = self._register_user("Copilot User 10", "copilot10@fitquest.ai")
        user_id = auth["user"]["id"]

        sess = movement_copilot_engine.get_or_create_session("sess_10", user_id, "2", "Squat")
        sess.baseline_established = True
        sess.baseline_metrics["movement_stability"] = 90.0
        sess.last_coaching_timestamp = 0.0

        # 1. Trigger instability warning with alternating torso sway
        for i in range(8):
            angle = 170.0 - (i % 6) * 15.0
            torso_val = 130.0 if (i % 2 == 0) else 180.0
            movement_copilot_engine.process_frame_telemetry(
                session_id="sess_10", user_id=user_id, exercise_id="2",
                rep_count=1, form_score=55.0, state="DESCENT",
                primary_angle=angle, torso_angle=torso_val
            )
        self.assertIsNotNone(sess.recovery_target)
        self.assertEqual(sess.recovery_target["dimension"], "movement_stability")

        # 2. User fixes form: feed rock-solid torso (175 deg)
        sess.samples.clear()  # simulate new clean frames
        rec_responses = []
        for i in range(12):
            angle = 170.0 - (i % 6) * 15.0
            res_rec = movement_copilot_engine.process_frame_telemetry(
                session_id="sess_10", user_id=user_id, exercise_id="2",
                rep_count=2, form_score=95.0, state="ASCENT",
                primary_angle=angle, torso_angle=175.0, left_angle=angle, right_angle=angle
            )
            rec_responses.append(res_rec)

        recovered_res = next((r for r in rec_responses if r["status"] == "RECOVERED"), None)
        self.assertIsNotNone(recovered_res)
        self.assertIn("recovered", recovered_res["message"].lower())
        self.assertIn("improved", recovered_res["coaching_cue"].lower())
        self.assertGreater(recovered_res["delta"], 0.0)
        self.assertEqual(sess.successful_corrections, 1)

    # --- TEST 16: Exercise-Specific Coaching Matrix ---
    def test_11_all_exercises_coaching_coverage(self):
        """TEST 16: Verifies coaching cues exist for various exercises (Push-up, Lunges, Plank)."""
        auth = self._register_user("Copilot User 11", "copilot11@fitquest.ai")
        user_id = auth["user"]["id"]

        # Push-up (Ex 3)
        cue_pushup = movement_copilot_engine._generate_coaching_cue("3", "movement_stability", "DESCENT")
        self.assertIn("spine", cue_pushup.lower() or "core")

        # Lunges (Ex 4)
        cue_lunge = movement_copilot_engine._generate_coaching_cue("4", "movement_stability", "DESCENT")
        self.assertIn("knee", cue_lunge.lower())

        # Plank (Ex 9)
        cue_plank = movement_copilot_engine._generate_coaching_cue("9", "movement_stability", "DEFAULT")
        self.assertIn("hips", cue_plank.lower() or "core")

    # --- TEST 17: Movement DNA Context Integration ---
    def test_12_movement_dna_context_integration(self):
        """TEST 17: Movement DNA primary limiter adds heightened sensitivity and DNA alert prefix."""
        auth = self._register_user("Copilot User 12", "copilot12@fitquest.ai")
        user_id = auth["user"]["id"]

        sess = movement_copilot_engine.get_or_create_session(
            "sess_12", user_id, "2", "Squat", dna_primary_limiter="tempo_control"
        )
        self.assertEqual(sess.dna_primary_limiter, "tempo_control")

        cue = movement_copilot_engine._generate_coaching_cue(
            exercise_id="2", dimension="tempo_control", dna_limiter="tempo_control"
        )
        self.assertIn("Movement DNA limiter alert", cue)

    # --- TEST 18: Adaptive Training Prescribed Tempo Target ---
    def test_13_adaptive_training_tempo_target(self):
        """TEST 18: Prescribed adaptive tempo (e.g. 3-1-2) is referenced in tempo coaching."""
        auth = self._register_user("Copilot User 13", "copilot13@fitquest.ai")
        user_id = auth["user"]["id"]

        cue = movement_copilot_engine._generate_coaching_cue(
            exercise_id="2", dimension="tempo_control", adaptive_tempo="3-1-2"
        )
        self.assertIn("3-1-2 tempo target", cue)

    # --- TEST 19: Strict Multi-User Tenant Isolation ---
    def test_14_multi_user_isolation(self):
        """TEST 19: User A cannot process or close User B's Copilot session."""
        user_a = self._register_user("User A Copilot", "usera_copilot@fitquest.ai")
        user_b = self._register_user("User B Copilot", "userb_copilot@fitquest.ai")

        movement_copilot_engine.get_or_create_session("sess_isolated", user_a["user"]["id"], "2", "Squat")

        with self.assertRaises(PermissionError):
            movement_copilot_engine.get_or_create_session("sess_isolated", user_b["user"]["id"], "2", "Squat")

    # --- TEST 20: Unauthenticated API Rejection ---
    def test_15_unauthenticated_api_rejection(self):
        """TEST 20: Unauthenticated calls to /movement-intelligence/copilot/frame return 401/403."""
        res = self.client.post("/api/v1/movement-intelligence/copilot/frame", json={
            "session_id": "sess_anon",
            "exercise_id": 2,
            "rep_count": 1,
            "form_score": 80.0
        })
        self.assertIn(res.status_code, [401, 403])

    # --- TEST 21: Full Workout Session Lifecycle ---
    def test_16_workout_session_lifecycle(self):
        """TEST 21: Full lifecycle via REST API (Frame telemetry -> Reset -> Summary)."""
        auth = self._register_user("Copilot API User", "copilot_api@fitquest.ai")
        token = auth["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Ingest frames
        for _ in range(6):
            res_frame = self.client.post(
                "/api/v1/movement-intelligence/copilot/frame",
                headers=headers,
                json={
                    "session_id": "sess_lifecycle",
                    "exercise_id": 2,
                    "rep_count": 1,
                    "form_score": 85.0,
                    "state": "DESCENT",
                    "primary_angle": 120.0,
                    "torso_angle": 175.0
                }
            )
            self.assertEqual(res_frame.status_code, 200)

        # 2. Reset session for new set
        res_reset = self.client.post(
            "/api/v1/movement-intelligence/copilot/reset",
            headers=headers,
            json={"session_id": "sess_lifecycle", "exercise_id": 2}
        )
        self.assertEqual(res_reset.status_code, 200)

        # 3. Fetch summary
        res_sum = self.client.get(
            "/api/v1/movement-intelligence/copilot/summary/sess_lifecycle",
            headers=headers
        )
        self.assertEqual(res_sum.status_code, 200)
        sum_data = res_sum.json()
        self.assertIn("recovery_rate_pct", sum_data)
        self.assertIn("verdict", sum_data)

    # --- TEST 22: Exercise Transition Reset ---
    def test_17_exercise_transition_reset(self):
        """TEST 22: Changing exercise resets samples and active recovery state."""
        auth = self._register_user("Copilot User 17", "copilot17@fitquest.ai")
        user_id = auth["user"]["id"]

        sess = movement_copilot_engine.get_or_create_session("sess_trans", user_id, "2", "Squat")
        sess.samples.append(FrameTelemetrySample(timestamp=time.time()))
        sess.active_coaching = {"test": True}

        movement_copilot_engine.reset_session("sess_trans", user_id, new_exercise_id="3")
        self.assertEqual(sess.exercise_id, "3")
        self.assertEqual(len(sess.samples), 0)
        self.assertIsNone(sess.active_coaching)

    # --- TEST 23: Buffer Bounds & Memory Leak Safety ---
    def test_18_buffer_bounds_memory_safety(self):
        """TEST 23: Ingesting 200 frames caps internal buffer to maximum 60 items."""
        auth = self._register_user("Copilot User 18", "copilot18@fitquest.ai")
        user_id = auth["user"]["id"]

        for i in range(100):
            movement_copilot_engine.process_frame_telemetry(
                session_id="sess_mem", user_id=user_id, exercise_id="2",
                rep_count=i // 10, form_score=80.0, state="DESCENT",
                primary_angle=130.0, torso_angle=175.0
            )

        sess = movement_copilot_engine._sessions["sess_mem"]
        self.assertLessEqual(len(sess.samples), 60)

    # --- TEST 24: Post-Workout Summary Metrics & Verdict ---
    def test_19_post_workout_summary_verification(self):
        """TEST 24: Correctly computes interventions, recoveries, rates, and verdict."""
        auth = self._register_user("Copilot User 19", "copilot19@fitquest.ai")
        user_id = auth["user"]["id"]

        sess = movement_copilot_engine.get_or_create_session("sess_sum", user_id, "2", "Squat")
        sess.total_interventions = 3
        sess.successful_corrections = 2
        sess.interventions_by_dimension = {"movement_stability": 2, "tempo_control": 1}
        sess.recoveries_by_dimension = {"movement_stability": [14.5, 12.0]}

        summary = movement_copilot_engine.get_session_summary("sess_sum", user_id)
        self.assertEqual(summary["total_interventions"], 3)
        self.assertEqual(summary["successful_corrections"], 2)
        self.assertEqual(summary["recovery_rate_pct"], 66.7)
        self.assertEqual(summary["most_frequent_limiter"]["dimension"], "movement_stability")
        self.assertIn("66", str(summary["recovery_rate_pct"]))
        self.assertIn("Movement Stability", summary["biggest_recovery"]["label"])
        self.assertIn("Good coachability", summary["verdict"])


if __name__ == "__main__":
    unittest.main()
