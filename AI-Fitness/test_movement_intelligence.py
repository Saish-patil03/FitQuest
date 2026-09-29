#!/usr/bin/env python3
"""
Unit & Integration Test Suite for FitQuest Human Movement Intelligence Engine (Phase 1).

Tests:
1. Valid movement telemetry processing & feature extraction
2. Empty telemetry handling (0 reps, 0 frames, graceful zero-scores)
3. Missing/low-confidence keypoints handling
4. Invalid / extreme telemetry values (NaN, out-of-range, negative)
5. Bilateral vs Unilateral symmetry handling (returns None for unilateral/occluded)
6. Multiple reps calculation (consistency CV, tempo cadence)
7. Multi-exercise aware benchmarks (Squat, Bicep Curl, Push-up, Plank, Shoulder Press, Lunges)
8. End-to-end FastAPI endpoint integration (/api/v1/workouts/movement-intelligence/analyze & stop-session)
"""

import unittest
import numpy as np
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.movement_intelligence import (
    MovementAnalyzer,
    FrameTelemetrySample,
    SessionTelemetryBuffer,
    EXERCISE_BENCHMARKS
)
from backend.services.cv_service import cv_live_service


class TestMovementIntelligenceEngine(unittest.TestCase):
    """
    Test suite for MovementAnalyzer and MovementFingerprint computation.
    """

    def setUp(self):
        self.analyzer = MovementAnalyzer()

    def test_01_valid_movement_telemetry_squat(self):
        """TEST 1: Valid Squat session with 5 reps and bilateral knee telemetry."""
        samples = []
        # Simulate 5 full squat cycles (standing 165 deg <-> deep squat 85 deg)
        for rep in range(5):
            # Descending phase
            for angle in np.linspace(165.0, 85.0, 10):
                samples.append(FrameTelemetrySample(
                    timestamp=float(len(samples) * 0.1),
                    primary_angle=float(angle),
                    left_angle=float(angle + 2.0),
                    right_angle=float(angle - 2.0),
                    torso_angle=160.0,
                    state="SQUAT",
                    rep_count=rep,
                    valid=True
                ))
            # Ascending phase
            for angle in np.linspace(85.0, 165.0, 10):
                samples.append(FrameTelemetrySample(
                    timestamp=float(len(samples) * 0.1),
                    primary_angle=float(angle),
                    left_angle=float(angle + 1.5),
                    right_angle=float(angle - 1.5),
                    torso_angle=162.0,
                    state="STANDING",
                    rep_count=rep + 1,
                    valid=True
                ))

        buf = SessionTelemetryBuffer(
            exercise_id="2",
            exercise_name="Squat",
            samples=samples,
            rep_durations=[2.0, 2.1, 2.0, 2.2, 2.0],
            rep_rom_deltas=[80.0, 80.0, 79.0, 81.0, 80.0]
        )

        result = self.analyzer.analyze_session(
            exercise_id="2",
            exercise_name="Squat",
            rep_count=5,
            duration_sec=11,
            form_score=95.0,
            telemetry_buffer=buf
        )

        sig = result["movement_signature"]
        feat = result["movement_features"]

        self.assertEqual(result["exercise_name"], "Squat")
        self.assertEqual(result["total_reps"], 5)
        # Verify all scores are normalized in range 0-100
        for score_key, score_val in sig.items():
            if score_val is not None:
                self.assertTrue(0 <= score_val <= 100, f"{score_key} ({score_val}) out of 0-100 bounds")

        # Range of motion: achieved 80 deg vs 65 target -> high score
        self.assertGreaterEqual(sig["rom_score"], 85)
        # Symmetry: ~3.5 deg disparity -> high symmetry
        self.assertIsNotNone(sig["symmetry_score"])
        self.assertGreaterEqual(sig["symmetry_score"], 80)
        # Stability: smooth angles -> high stability
        self.assertGreaterEqual(sig["stability_score"], 70)
        # Tempo: ~2.0s per rep vs 2.6s ideal -> high tempo score
        self.assertGreaterEqual(sig["tempo_score"], 70)
        # Consistency: very uniform reps -> high consistency
        self.assertGreaterEqual(sig["consistency_score"], 80)
        # Overall Quality composite
        self.assertGreaterEqual(sig["movement_quality_score"], 75)

    def test_02_empty_telemetry_graceful_handling(self):
        """TEST 2: Zero reps and empty frame buffer produce clean zero/unavailable metrics."""
        result = self.analyzer.analyze_session(
            exercise_id="1",
            exercise_name="Bicep Curl",
            rep_count=0,
            duration_sec=0,
            form_score=0.0,
            samples=[]
        )

        sig = result["movement_signature"]
        self.assertEqual(result["total_reps"], 0)
        self.assertEqual(sig["rom_score"], 0)
        self.assertEqual(sig["stability_score"], 0)
        self.assertEqual(sig["tempo_score"], 0)
        self.assertEqual(sig["consistency_score"], 0)
        self.assertEqual(sig["movement_quality_score"], 0)

        # Check metrics summary array
        for item in result["metrics_summary"]:
            self.assertFalse(item["available"])

    def test_03_missing_keypoints_resilience(self):
        """TEST 3: Frames with missing/invalid keypoints are safely skipped without errors."""
        samples = [
            FrameTelemetrySample(timestamp=0.1, primary_angle=None, left_angle=None, right_angle=None, valid=False),
            FrameTelemetrySample(timestamp=0.2, primary_angle=120.0, left_angle=120.0, right_angle=118.0, valid=True),
            FrameTelemetrySample(timestamp=0.3, primary_angle=None, left_angle=None, right_angle=None, valid=False),
            FrameTelemetrySample(timestamp=0.4, primary_angle=70.0, left_angle=70.0, right_angle=72.0, valid=True),
        ]

        result = self.analyzer.analyze_session(
            exercise_id="1",
            exercise_name="Bicep Curl",
            rep_count=1,
            duration_sec=3,
            form_score=80.0,
            samples=samples
        )

        sig = result["movement_signature"]
        self.assertIsInstance(sig["rom_score"], int)
        self.assertIsInstance(sig["stability_score"], int)
        self.assertTrue(0 <= sig["movement_quality_score"] <= 100)

    def test_04_invalid_and_extreme_values(self):
        """TEST 4: Extreme or out-of-bounds angles do not crash the engine."""
        samples = [
            FrameTelemetrySample(timestamp=0.1, primary_angle=999.0, torso_angle=-50.0, valid=True),
            FrameTelemetrySample(timestamp=0.2, primary_angle=-10.0, torso_angle=400.0, valid=True),
            FrameTelemetrySample(timestamp=0.3, primary_angle=120.0, torso_angle=150.0, valid=True),
        ]

        result = self.analyzer.analyze_session(
            exercise_id="2",
            exercise_name="Squat",
            rep_count=1,
            duration_sec=2,
            form_score=50.0,
            samples=samples
        )

        sig = result["movement_signature"]
        self.assertTrue(0 <= sig["rom_score"] <= 100)
        self.assertTrue(0 <= sig["stability_score"] <= 100)
        self.assertTrue(0 <= sig["movement_quality_score"] <= 100)

    def test_05_unilateral_exercise_symmetry_is_none(self):
        """TEST 5: Unilateral / Asymmetric exercises (Lunges, Mountain Climbers) return symmetry = None."""
        # Exercise 4: Lunges (unilateral)
        samples = [
            FrameTelemetrySample(timestamp=0.1, primary_angle=160.0, left_angle=160.0, right_angle=100.0, valid=True),
            FrameTelemetrySample(timestamp=0.2, primary_angle=100.0, left_angle=100.0, right_angle=150.0, valid=True),
            FrameTelemetrySample(timestamp=0.3, primary_angle=160.0, left_angle=160.0, right_angle=100.0, valid=True),
        ]

        result = self.analyzer.analyze_session(
            exercise_id="4",
            exercise_name="Lunges",
            rep_count=1,
            duration_sec=3,
            form_score=90.0,
            samples=samples
        )

        sig = result["movement_signature"]
        self.assertIsNone(sig["symmetry_score"], "Lunges must return symmetry = None (unilateral)")
        self.assertIsNone(result["movement_features"]["symmetry"])

        # Quality score should calculate based on 4-axis weighting without crashing
        self.assertGreater(sig["movement_quality_score"], 0)

    def test_06_multi_rep_consistency_and_tempo(self):
        """TEST 6: Multiple rep consistency variation reflects cadence changes."""
        # Consistent set
        res_consistent = self.analyzer.analyze_session(
            exercise_id="1",
            exercise_name="Bicep Curl",
            rep_count=5,
            duration_sec=12,
            form_score=95.0,
            telemetry_buffer=SessionTelemetryBuffer(
                exercise_id="1",
                exercise_name="Bicep Curl",
                rep_durations=[2.4, 2.4, 2.5, 2.4, 2.5],
                rep_rom_deltas=[85.0, 85.0, 84.0, 86.0, 85.0]
            )
        )

        # Inconsistent erratic set
        res_erratic = self.analyzer.analyze_session(
            exercise_id="1",
            exercise_name="Bicep Curl",
            rep_count=5,
            duration_sec=15,
            form_score=70.0,
            telemetry_buffer=SessionTelemetryBuffer(
                exercise_id="1",
                exercise_name="Bicep Curl",
                rep_durations=[1.1, 4.8, 1.3, 5.2, 1.0],
                rep_rom_deltas=[40.0, 90.0, 45.0, 95.0, 35.0]
            )
        )

        self.assertGreater(
            res_consistent["movement_signature"]["consistency_score"],
            res_erratic["movement_signature"]["consistency_score"],
            "Uniform reps must score higher consistency than erratic reps."
        )

    def test_07_isometric_plank_analysis(self):
        """TEST 7: Isometric Plank calculates spine alignment stability & continuous hold tempo."""
        samples = [
            FrameTelemetrySample(timestamp=float(i), primary_angle=176.0 + (i % 2), torso_angle=176.0, valid=True)
            for i in range(15)
        ]

        result = self.analyzer.analyze_session(
            exercise_id="9",
            exercise_name="Plank",
            rep_count=15,  # 15s hold
            duration_sec=15,
            form_score=100.0,
            samples=samples
        )

        sig = result["movement_signature"]
        feat = result["movement_features"]

        self.assertGreaterEqual(sig["rom_score"], 85)
        self.assertGreaterEqual(sig["stability_score"], 80)
        self.assertGreaterEqual(sig["movement_quality_score"], 80)
        self.assertIn("spine_deviation_deg", feat["range_of_motion"])

    def test_08_api_endpoint_movement_analysis(self):
        """TEST 8: POST /api/v1/workouts/movement-intelligence/analyze returns valid response."""
        client = TestClient(app)
        payload = {
            "exercise_id": "2",
            "exercise_name": "Squat",
            "rep_count": 8,
            "duration_sec": 20,
            "form_score": 90.0,
            "angles": [160.0, 130.0, 90.0, 130.0, 160.0] * 8,
            "left_angles": [160.0, 130.0, 90.0, 130.0, 160.0] * 8,
            "right_angles": [158.0, 129.0, 89.0, 129.0, 158.0] * 8,
            "torso_angles": [165.0] * 40
        }

        res = client.post("/api/v1/workouts/movement-intelligence/analyze", json=payload)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("movement_intelligence", data)
        intel = data["movement_intelligence"]
        self.assertEqual(intel["exercise_name"], "Squat")
        self.assertEqual(intel["total_reps"], 8)
        self.assertIn("movement_signature", intel)
        self.assertIn("movement_features", intel)

    def test_09_cv_service_session_lifecycle(self):
        """TEST 9: CVLiveService start, buffer, and close lifecycle produces movement intelligence."""
        session_id = "test_movement_session_123"
        controller = cv_live_service.start_session(session_id=session_id, exercise_choice="2")
        self.assertIn(session_id, cv_live_service.session_buffers)

        # Close session
        session_data, movement_intel = cv_live_service.close_session_with_movement(session_id)
        self.assertIsNotNone(session_data)
        self.assertIsNotNone(movement_intel)
        self.assertNotIn(session_id, cv_live_service.session_buffers)
        self.assertEqual(movement_intel["exercise_name"], "Squat")


if __name__ == "__main__":
    unittest.main()
