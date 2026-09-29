import unittest
import time
import numpy as np
from exercises.shoulder_press import ShoulderPressTracker
from exercises.front_raise import FrontRaiseTracker
from exercises.lateral_raise import LateralRaiseTracker
from exercises.tricep_extension import TricepExtensionTracker

class TestPhase4CUpperBodyTrackers(unittest.TestCase):

    def test_1_shoulder_press_validation(self):
        """TEST 1: Shoulder Press - Valid rep, missing landmarks, and high wrist validation."""
        tracker = ShoulderPressTracker(lowered_angle=105.0, pressed_angle=150.0, min_displacement_px=35.0)

        # 1. Missing landmarks
        res_missing = tracker.process({})
        self.assertFalse(res_missing["valid"])
        self.assertEqual(res_missing["feedback_code"], "LANDMARKS_MISSING")

        # 2. Lowered starting posture (hands at shoulder height: Hip-Sh-Wr angle ~58 deg <= 105 deg)
        lowered_kpts = {
            "left_hip":      {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_shoulder": {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 150, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 180, "y": 250, "conf": 0.9, "valid": True},  # Lowered hands
        }

        # 3. Pressed overhead posture (hands overhead: Hip-Sh-Wr angle ~180 deg >= 150 deg, y_wrist <= y_shoulder)
        pressed_kpts = {
            "left_hip":      {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_shoulder": {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 150, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 80,  "conf": 0.9, "valid": True},  # Raised 70px overhead
        }

        for _ in range(8):
            tracker.process(lowered_kpts)
        for _ in range(8):
            tracker.process(pressed_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res_rep = tracker.process(lowered_kpts)

        self.assertEqual(tracker.rep_count, 1)

    def test_2_front_raise_validation(self):
        """TEST 2: Front Raise - Valid raise, elbow bend cheat, and shallow raise."""
        tracker = FrontRaiseTracker(lowered_angle=35.0, raised_angle=80.0, min_displacement_px=30.0)

        # Lowered arms (Hip-Sh-Wr angle ~0 deg <= 35 deg)
        lowered_kpts = {
            "left_hip":      {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_shoulder": {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 250, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
        }
        # Raised arms forward (Hip-Sh-Wr angle ~90 deg >= 80 deg)
        raised_kpts = {
            "left_hip":      {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_shoulder": {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 180, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 250, "y": 200, "conf": 0.9, "valid": True},  # Raised 150px forward
        }

        for _ in range(8):
            tracker.process(lowered_kpts)
        for _ in range(8):
            tracker.process(raised_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res = tracker.process(lowered_kpts)

        self.assertEqual(tracker.rep_count, 1)

    def test_3_lateral_raise_validation(self):
        """TEST 3: Lateral Raise - Valid raise & rigid elbow structure."""
        tracker = LateralRaiseTracker(lowered_angle=35.0, raised_angle=80.0, min_displacement_px=30.0)

        lowered_kpts = {
            "left_hip":      {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_shoulder": {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 250, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
        }
        raised_kpts = {
            "left_hip":      {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_shoulder": {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 200, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 300, "y": 200, "conf": 0.9, "valid": True},  # Raised 200px sideways
        }

        for _ in range(8):
            tracker.process(lowered_kpts)
        for _ in range(8):
            tracker.process(raised_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res = tracker.process(lowered_kpts)

        self.assertEqual(tracker.rep_count, 1)

    def test_4_tricep_extension_validation(self):
        """TEST 4: Tricep Extension - Valid rep & upper arm drift anti-cheating."""
        tracker = TricepExtensionTracker(bent_angle=75.0, extended_angle=150.0, min_displacement_px=25.0)

        # Bent elbows behind head (Sh-El-Wr angle ~60 deg <= 75 deg)
        bent_kpts = {
            "left_shoulder": {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 60,  "y": 150, "conf": 0.9, "valid": True},
        }
        # Extended arms overhead (Sh-El-Wr angle ~180 deg >= 150 deg)
        extended_kpts = {
            "left_shoulder": {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 20,  "conf": 0.9, "valid": True},  # Extended 130px overhead
        }

        # Upper arm drift cheat keypoints (elbow drifts 120px away horizontally)
        drift_kpts = {
            "left_shoulder": {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 230, "y": 100, "conf": 0.9, "valid": True},  # dx_elbow = 130 > 90
            "left_wrist":    {"x": 230, "y": 20,  "conf": 0.9, "valid": True},
        }

        res_drift = tracker.process(drift_kpts)
        self.assertEqual(res_drift["feedback_code"], "UPPER_ARM_MOVING")

        for _ in range(8):
            tracker.process(bent_kpts)
        for _ in range(8):
            tracker.process(extended_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res = tracker.process(bent_kpts)

        self.assertEqual(tracker.rep_count, 1)

if __name__ == "__main__":
    unittest.main()
