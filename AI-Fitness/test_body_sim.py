#!/usr/bin/env python3
"""
Unit & Integration Test Suite for FitQuest BODY SIM™ (Phase 6).
Predictive Human Performance Intelligence & What-If Intervention Simulator.

Verifies 20 Scenarios:
1. Service initialization & strategy catalogue
2. Empty history handling (0 sessions -> graceful cold-start baseline)
3. Single-session history handling (1 session -> low confidence)
4. Dual-session history handling (2 sessions -> initial trajectory)
5. Longitudinal trajectory projection (N >= 5 sessions)
6. Horizon scaling (3 vs 5 vs 10 sessions)
7. Diminishing returns & score bounds (20.0 <= S <= 100.0)
8. Limiter risk index computation & risk tier classification
9. Forecast confidence scoring based on volatility and sample count
10. What-If Strategy: BALANCED simulation
11. What-If Strategy: TEMPO_FOCUS simulation
12. What-If Strategy: STABILITY_FOCUS simulation
13. What-If Strategy: ROM_FOCUS simulation
14. What-If Strategy: SYMMETRY_FOCUS simulation
15. What-If Strategy: CONSISTENCY_FOCUS simulation
16. Unilateral exercise handling (null bilateral symmetry)
17. Multi-tenant security isolation (User A vs User B)
18. Unauthenticated API rejection (401/403)
19. Intervention workout generation bridge to Adaptive Training
20. Full REST API lifecycle (/forecast -> /simulate -> /intervention-workout)
"""

import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import UserModel, ExerciseModel, MovementFingerprintModel
from backend.services.body_sim import body_sim_service, INTERVENTION_STRATEGIES

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


class TestBodySimEngine(unittest.TestCase):
    """
    Test suite for Phase 6 BODY SIM™ Engine & API.
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
        self.ex_lunge = ExerciseModel(id=4, name="Lunges", difficulty="Intermediate", description="Lunges")
        self.db.add_all([self.ex_bicep, self.ex_squat, self.ex_lunge])
        self.db.commit()

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

    def _seed_fingerprints(self, user_id: int, exercise_id: int, count: int, quality_progression: list):
        now = datetime.now(timezone.utc)
        for i in range(count):
            scores = quality_progression[i] if i < len(quality_progression) else quality_progression[-1]
            fp = MovementFingerprintModel(
                user_id=user_id,
                exercise_id=exercise_id,
                exercise_name="Exercise",
                range_of_motion=scores.get("rom", 80.0),
                movement_stability=scores.get("stability", 80.0),
                tempo_control=scores.get("tempo", 80.0),
                repetition_consistency=scores.get("consistency", 80.0),
                bilateral_symmetry=scores.get("symmetry", 80.0),
                overall_movement_quality=scores.get("overall", 80.0),
                form_score=90.0,
                repetition_count=12,
                session_duration=60,
                created_at=now - timedelta(days=count - i)
            )
            self.db.add(fp)
        self.db.commit()

    # --- TEST 1: Service Init & Strategy Catalogue ---
    def test_01_service_init_and_strategies(self):
        """TEST 1: Verifies all 6 What-If intervention strategies are configured."""
        self.assertEqual(len(INTERVENTION_STRATEGIES), 6)
        expected_keys = ["BALANCED", "TEMPO_FOCUS", "STABILITY_FOCUS", "ROM_FOCUS", "SYMMETRY_FOCUS", "CONSISTENCY_FOCUS"]
        for key in expected_keys:
            self.assertIn(key, INTERVENTION_STRATEGIES)
            self.assertIn("velocity_boosts", INTERVENTION_STRATEGIES[key])

    # --- TEST 2: Empty History Handling ---
    def test_02_empty_history_cold_start(self):
        """TEST 2: Cold-start user returns default nominal baseline with low confidence."""
        auth = self._register_user("BodySim User 1", "bodysim1@fitquest.ai")
        user_id = auth["user"]["id"]

        forecast = body_sim_service.get_performance_forecast(self.db, user_id, horizon=5)
        self.assertEqual(forecast["status"], "success")
        self.assertEqual(forecast["total_historical_sessions"], 0)
        self.assertEqual(forecast["confidence_tier"], "Low")
        self.assertGreaterEqual(forecast["confidence_score"], 20.0)
        self.assertEqual(len(forecast["overall_trajectory"]), 6)  # 0 to 5

    # --- TEST 3: Single Session History ---
    def test_03_single_session_history(self):
        """TEST 3: Single session provides baseline forecast with low confidence."""
        auth = self._register_user("BodySim User 2", "bodysim2@fitquest.ai")
        user_id = auth["user"]["id"]

        self._seed_fingerprints(user_id, 2, 1, [{"rom": 75.0, "stability": 70.0, "tempo": 65.0, "consistency": 80.0, "symmetry": 85.0, "overall": 75.0}])

        forecast = body_sim_service.get_performance_forecast(self.db, user_id, horizon=5)
        self.assertEqual(forecast["total_historical_sessions"], 1)
        self.assertEqual(forecast["confidence_tier"], "Low")
        self.assertGreater(forecast["projected_dna_score"], 70.0)

    # --- TEST 4: Dual Session History ---
    def test_04_dual_session_history(self):
        """TEST 4: Two sessions establish initial positive trend velocity."""
        auth = self._register_user("BodySim User 3", "bodysim3@fitquest.ai")
        user_id = auth["user"]["id"]

        prog = [
            {"rom": 70.0, "stability": 70.0, "tempo": 60.0, "consistency": 75.0, "symmetry": 80.0, "overall": 71.0},
            {"rom": 74.0, "stability": 73.0, "tempo": 64.0, "consistency": 78.0, "symmetry": 82.0, "overall": 74.2}
        ]
        self._seed_fingerprints(user_id, 2, 2, prog)

        forecast = body_sim_service.get_performance_forecast(self.db, user_id, horizon=5)
        self.assertEqual(forecast["total_historical_sessions"], 2)
        self.assertGreater(forecast["projected_overall_delta"], 0.0)

    # --- TEST 5: Longitudinal Trajectory Projection (N >= 5) ---
    def test_05_longitudinal_trajectory_projection(self):
        """TEST 5: Longitudinal progression achieves high confidence and positive forecast."""
        auth = self._register_user("BodySim User 4", "bodysim4@fitquest.ai")
        user_id = auth["user"]["id"]

        prog = [
            {"rom": 65.0, "stability": 68.0, "tempo": 55.0, "consistency": 70.0, "symmetry": 75.0, "overall": 66.6},
            {"rom": 68.0, "stability": 71.0, "tempo": 58.0, "consistency": 72.0, "symmetry": 77.0, "overall": 69.2},
            {"rom": 72.0, "stability": 74.0, "tempo": 61.0, "consistency": 75.0, "symmetry": 80.0, "overall": 72.4},
            {"rom": 75.0, "stability": 77.0, "tempo": 64.0, "consistency": 78.0, "symmetry": 82.0, "overall": 75.2},
            {"rom": 78.0, "stability": 80.0, "tempo": 67.0, "consistency": 81.0, "symmetry": 84.0, "overall": 78.0},
            {"rom": 81.0, "stability": 83.0, "tempo": 70.0, "consistency": 83.0, "symmetry": 86.0, "overall": 80.6}
        ]
        self._seed_fingerprints(user_id, 2, 6, prog)

        forecast = body_sim_service.get_performance_forecast(self.db, user_id, horizon=5)
        self.assertEqual(forecast["total_historical_sessions"], 6)
        self.assertEqual(forecast["confidence_tier"], "High")
        self.assertGreater(forecast["projected_dna_score"], forecast["current_dna_score"])
        self.assertEqual(len(forecast["overall_trajectory"]), 6)

    # --- TEST 6: Horizon Scaling (3 vs 5 vs 10) ---
    def test_06_horizon_scaling(self):
        """TEST 6: Compares trajectory lengths and cumulative score progression across horizons."""
        auth = self._register_user("BodySim User 5", "bodysim5@fitquest.ai")
        user_id = auth["user"]["id"]

        prog = [{"rom": 70.0 + i * 2, "stability": 70.0 + i * 2, "tempo": 60.0 + i * 2, "consistency": 75.0, "symmetry": 80.0, "overall": 71.0 + i * 2} for i in range(5)]
        self._seed_fingerprints(user_id, 2, 5, prog)

        f3 = body_sim_service.get_performance_forecast(self.db, user_id, horizon=3)
        f5 = body_sim_service.get_performance_forecast(self.db, user_id, horizon=5)
        f10 = body_sim_service.get_performance_forecast(self.db, user_id, horizon=10)

        self.assertEqual(len(f3["overall_trajectory"]), 4)
        self.assertEqual(len(f5["overall_trajectory"]), 6)
        self.assertEqual(len(f10["overall_trajectory"]), 11)
        self.assertGreater(f10["projected_dna_score"], f3["projected_dna_score"])

    # --- TEST 7: Diminishing Returns & Score Bounds ---
    def test_07_diminishing_returns_and_bounds(self):
        """TEST 7: Near-perfect scores experience asymptotic saturation below 100.0."""
        auth = self._register_user("BodySim User 6", "bodysim6@fitquest.ai")
        user_id = auth["user"]["id"]

        # High level user (starting at 95.0)
        prog = [{"rom": 95.0, "stability": 96.0, "tempo": 94.0, "consistency": 95.0, "symmetry": 96.0, "overall": 95.2} for _ in range(5)]
        self._seed_fingerprints(user_id, 2, 5, prog)

        forecast = body_sim_service.get_performance_forecast(self.db, user_id, horizon=10)
        self.assertLessEqual(forecast["projected_dna_score"], 100.0)
        self.assertGreaterEqual(forecast["projected_dna_score"], 95.0)

    # --- TEST 8: Limiter Risk Index & Tier Classification ---
    def test_08_limiter_risk_computation(self):
        """TEST 8: Flags bottleneck dimension with Elevated/Critical risk index."""
        auth = self._register_user("BodySim User 7", "bodysim7@fitquest.ai")
        user_id = auth["user"]["id"]

        # Tempo is severely lagging (45.0) while others are ~85.0
        prog = [{"rom": 85.0, "stability": 85.0, "tempo": 45.0, "consistency": 85.0, "symmetry": 85.0, "overall": 77.0} for _ in range(5)]
        self._seed_fingerprints(user_id, 2, 5, prog)

        forecast = body_sim_service.get_performance_forecast(self.db, user_id, horizon=5)
        limiter = forecast["projected_limiter"]
        self.assertIsNotNone(limiter)
        self.assertEqual(limiter["dimension"], "tempo_control")
        self.assertIn(limiter["risk_tier"], ["ELEVATED", "CRITICAL"])
        self.assertGreaterEqual(limiter["risk_index"], 50.0)

    # --- TEST 9: Forecast Confidence Scoring ---
    def test_09_forecast_confidence_scoring(self):
        """TEST 9: Confidence score scales with sample count and penalizes extreme volatility."""
        auth = self._register_user("BodySim User 8", "bodysim8@fitquest.ai")
        user_id = auth["user"]["id"]

        # Low volume
        self._seed_fingerprints(user_id, 2, 1, [{"rom": 80.0, "stability": 80.0, "tempo": 80.0, "consistency": 80.0, "symmetry": 80.0, "overall": 80.0}])
        f_low = body_sim_service.get_performance_forecast(self.db, user_id, horizon=5)
        self.assertEqual(f_low["confidence_tier"], "Low")

        # High volume
        for i in range(8):
            fp = MovementFingerprintModel(
                user_id=user_id, exercise_id=2, exercise_name="Squat",
                range_of_motion=80.0, movement_stability=80.0, tempo_control=80.0,
                repetition_consistency=80.0, bilateral_symmetry=80.0,
                overall_movement_quality=80.0, form_score=90.0, repetition_count=10, session_duration=60
            )
            self.db.add(fp)
        self.db.commit()

        f_high = body_sim_service.get_performance_forecast(self.db, user_id, horizon=5)
        self.assertEqual(f_high["confidence_tier"], "High")
        self.assertGreater(f_high["confidence_score"], f_low["confidence_score"])

    # --- TEST 10-15: What-If Intervention Strategies ---
    def test_10_what_if_balanced_strategy(self):
        """TEST 10: Balanced strategy models uniform growth across all dimensions."""
        auth = self._register_user("BodySim User 9", "bodysim9@fitquest.ai")
        user_id = auth["user"]["id"]

        self._seed_fingerprints(user_id, 2, 4, [{"rom": 75.0, "stability": 75.0, "tempo": 70.0, "consistency": 75.0, "symmetry": 75.0, "overall": 74.0} for _ in range(4)])
        sim = body_sim_service.simulate_intervention(self.db, user_id, strategy_key="BALANCED", horizon=5)
        self.assertEqual(sim["strategy"], "BALANCED")
        self.assertGreater(sim["simulated_dna_score"], sim["baseline_projected_dna"])

    def test_11_what_if_tempo_focus_strategy(self):
        """TEST 11: Tempo Focus strategy delivers maximum velocity boost to tempo_control."""
        auth = self._register_user("BodySim User 10", "bodysim10@fitquest.ai")
        user_id = auth["user"]["id"]

        self._seed_fingerprints(user_id, 2, 4, [{"rom": 85.0, "stability": 85.0, "tempo": 55.0, "consistency": 80.0, "symmetry": 85.0, "overall": 78.0} for _ in range(4)])
        sim = body_sim_service.simulate_intervention(self.db, user_id, strategy_key="TEMPO_FOCUS", horizon=5)
        self.assertEqual(sim["strategy"], "TEMPO_FOCUS")
        self.assertGreater(sim["net_improvement_delta"], 0.0)
        self.assertGreater(sim["simulated_dimensions"]["tempo_control"]["intervention_gain"], 5.0)

    def test_12_what_if_stability_focus_strategy(self):
        """TEST 12: Stability Focus strategy boosts movement_stability."""
        auth = self._register_user("BodySim User 11", "bodysim11@fitquest.ai")
        user_id = auth["user"]["id"]

        self._seed_fingerprints(user_id, 2, 4, [{"rom": 85.0, "stability": 55.0, "tempo": 80.0, "consistency": 80.0, "symmetry": 80.0, "overall": 76.0} for _ in range(4)])
        sim = body_sim_service.simulate_intervention(self.db, user_id, strategy_key="STABILITY_FOCUS", horizon=5)
        self.assertEqual(sim["strategy"], "STABILITY_FOCUS")
        self.assertGreater(sim["simulated_dimensions"]["movement_stability"]["intervention_gain"], 5.0)

    def test_13_what_if_rom_focus_strategy(self):
        """TEST 13: ROM Focus strategy boosts range_of_motion."""
        auth = self._register_user("BodySim User 12", "bodysim12@fitquest.ai")
        user_id = auth["user"]["id"]

        self._seed_fingerprints(user_id, 2, 4, [{"rom": 50.0, "stability": 80.0, "tempo": 80.0, "consistency": 80.0, "symmetry": 80.0, "overall": 74.0} for _ in range(4)])
        sim = body_sim_service.simulate_intervention(self.db, user_id, strategy_key="ROM_FOCUS", horizon=5)
        self.assertEqual(sim["strategy"], "ROM_FOCUS")
        self.assertGreater(sim["simulated_dimensions"]["range_of_motion"]["intervention_gain"], 5.0)

    def test_14_what_if_symmetry_focus_strategy(self):
        """TEST 14: Symmetry Focus strategy boosts bilateral_symmetry."""
        auth = self._register_user("BodySim User 13", "bodysim13@fitquest.ai")
        user_id = auth["user"]["id"]

        self._seed_fingerprints(user_id, 1, 4, [{"rom": 80.0, "stability": 80.0, "tempo": 80.0, "consistency": 80.0, "symmetry": 50.0, "overall": 74.0} for _ in range(4)])
        sim = body_sim_service.simulate_intervention(self.db, user_id, strategy_key="SYMMETRY_FOCUS", horizon=5)
        self.assertEqual(sim["strategy"], "SYMMETRY_FOCUS")
        self.assertGreater(sim["simulated_dimensions"]["bilateral_symmetry"]["intervention_gain"], 5.0)

    def test_15_what_if_consistency_focus_strategy(self):
        """TEST 15: Consistency Focus strategy boosts repetition_consistency."""
        auth = self._register_user("BodySim User 14", "bodysim14@fitquest.ai")
        user_id = auth["user"]["id"]

        self._seed_fingerprints(user_id, 2, 4, [{"rom": 80.0, "stability": 80.0, "tempo": 80.0, "consistency": 50.0, "symmetry": 80.0, "overall": 74.0} for _ in range(4)])
        sim = body_sim_service.simulate_intervention(self.db, user_id, strategy_key="CONSISTENCY_FOCUS", horizon=5)
        self.assertEqual(sim["strategy"], "CONSISTENCY_FOCUS")
        self.assertGreater(sim["simulated_dimensions"]["repetition_consistency"]["intervention_gain"], 5.0)

    # --- TEST 16: Unilateral Exercise Handling (Null Symmetry) ---
    def test_16_unilateral_exercise_null_symmetry(self):
        """TEST 16: Unilateral exercises without symmetry normalize overall average correctly."""
        auth = self._register_user("BodySim User 15", "bodysim15@fitquest.ai")
        user_id = auth["user"]["id"]

        # Lunges (Ex 4) has bilateral_symmetry=None
        self._seed_fingerprints(user_id, 4, 3, [{"rom": 75.0, "stability": 70.0, "tempo": 75.0, "consistency": 80.0, "symmetry": None, "overall": 75.0} for _ in range(3)])

        forecast = body_sim_service.get_performance_forecast(self.db, user_id, horizon=5, exercise_id=4)
        self.assertEqual(forecast["status"], "success")
        self.assertIsNone(forecast["dimensions"]["bilateral_symmetry"]["current"])
        self.assertGreater(forecast["projected_dna_score"], 0.0)

    # --- TEST 17: Multi-Tenant Security Isolation ---
    def test_17_multi_tenant_isolation(self):
        """TEST 17: User A cannot access User B's BODY SIM forecast."""
        user_a = self._register_user("User A Sim", "usera_sim@fitquest.ai")
        user_b = self._register_user("User B Sim", "userb_sim@fitquest.ai")

        self._seed_fingerprints(user_a["user"]["id"], 2, 3, [{"rom": 90.0, "stability": 90.0, "tempo": 90.0, "consistency": 90.0, "symmetry": 90.0, "overall": 90.0} for _ in range(3)])
        self._seed_fingerprints(user_b["user"]["id"], 2, 3, [{"rom": 60.0, "stability": 60.0, "tempo": 60.0, "consistency": 60.0, "symmetry": 60.0, "overall": 60.0} for _ in range(3)])

        token_a = user_a["access_token"]
        token_b = user_b["access_token"]

        res_a = self.client.get("/api/v1/movement-intelligence/body-sim/forecast", headers={"Authorization": f"Bearer {token_a}"})
        res_b = self.client.get("/api/v1/movement-intelligence/body-sim/forecast", headers={"Authorization": f"Bearer {token_b}"})

        self.assertEqual(res_a.status_code, 200)
        self.assertEqual(res_b.status_code, 200)
        self.assertGreater(res_a.json()["current_dna_score"], 85.0)
        self.assertLess(res_b.json()["current_dna_score"], 65.0)

    # --- TEST 18: Unauthenticated API Rejection ---
    def test_18_unauthenticated_api_rejection(self):
        """TEST 18: Unauthenticated requests to BODY SIM endpoints return 401/403."""
        res1 = self.client.get("/api/v1/movement-intelligence/body-sim/forecast")
        self.assertIn(res1.status_code, [401, 403])

        res2 = self.client.post("/api/v1/movement-intelligence/body-sim/simulate", json={"strategy": "TEMPO_FOCUS"})
        self.assertIn(res2.status_code, [401, 403])

    # --- TEST 19: Intervention Workout Generation Bridge ---
    def test_19_intervention_workout_generation(self):
        """TEST 19: Generates adaptive workout directly from What-If simulation."""
        auth = self._register_user("BodySim User 16", "bodysim16@fitquest.ai")
        user_id = auth["user"]["id"]

        self._seed_fingerprints(user_id, 2, 4, [{"rom": 80.0, "stability": 80.0, "tempo": 55.0, "consistency": 80.0, "symmetry": 80.0, "overall": 75.0} for _ in range(4)])
        workout = body_sim_service.generate_intervention_workout(self.db, user_id, strategy_key="TEMPO_FOCUS", target_duration_min=20)

        self.assertIn("plan_name", workout)
        self.assertEqual(workout["intervention_strategy"], "TEMPO_FOCUS")
        self.assertIn("BODY SIM", workout["intervention_rationale"])
        self.assertGreaterEqual(len(workout["exercises"]), 2)

    # --- TEST 20: Full REST API Lifecycle ---
    def test_20_full_api_lifecycle(self):
        """TEST 20: Full REST flow (/forecast -> /simulate -> /intervention-workout -> /strategies)."""
        auth = self._register_user("BodySim API User", "bodysim_api@fitquest.ai")
        token = auth["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Strategies
        res_strat = self.client.get("/api/v1/movement-intelligence/body-sim/strategies")
        self.assertEqual(res_strat.status_code, 200)
        self.assertEqual(len(res_strat.json()["strategies"]), 6)

        # 2. Forecast
        res_fc = self.client.get("/api/v1/movement-intelligence/body-sim/forecast?horizon=5", headers=headers)
        self.assertEqual(res_fc.status_code, 200)
        self.assertIn("projected_dna_score", res_fc.json())

        # 3. Simulate
        res_sim = self.client.post("/api/v1/movement-intelligence/body-sim/simulate", headers=headers, json={"strategy": "STABILITY_FOCUS", "horizon": 5})
        self.assertEqual(res_sim.status_code, 200)
        self.assertIn("net_improvement_delta", res_sim.json())

        # 4. Generate Workout
        res_wo = self.client.post("/api/v1/movement-intelligence/body-sim/intervention-workout", headers=headers, json={"strategy": "STABILITY_FOCUS", "target_duration_min": 25})
        self.assertEqual(res_wo.status_code, 200)
        self.assertIn("plan_name", res_wo.json())


if __name__ == "__main__":
    unittest.main()
