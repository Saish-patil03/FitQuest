import unittest
import time
import numpy as np
from exercises.plank import PlankTracker
from exercises.situps import SitUpsTracker
from exercises.crunches import CrunchesTracker
from exercises.leg_raise import LegRaisesTracker
from exercises.russian_twist import RussianTwistTracker
from exercises.bicycle_crunch import BicycleCrunchTracker

class TestPhase4DCoreTrackers(unittest.TestCase):

    def test_1_plank_validation(self):
        """TEST 1: Plank - Correct position, standing posture, sagging hips, and duration timer."""
        tracker = PlankTracker(min_straight_angle=150.0)

        # 1. Missing landmarks
        res_missing = tracker.process({})
        self.assertFalse(res_missing["valid"])
        self.assertEqual(res_missing["feedback_code"], "LANDMARKS_MISSING")

        # 2. Standing upright posture (inclination > 40 deg)
        standing_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_ankle":    {"x": 100, "y": 450, "conf": 0.9, "valid": True},
        }
        res_stand = tracker.process(standing_kpts)
        self.assertEqual(res_stand["feedback_code"], "BODY_NOT_HORIZONTAL")

        # 3. Hips sagging low (y_hip > y_shoulder + 40px)
        sagging_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 250, "y": 160, "conf": 0.9, "valid": True},  # Sagging low
            "left_ankle":    {"x": 400, "y": 100, "conf": 0.9, "valid": True},
        }
        for _ in range(4):
            res_sag = tracker.process(sagging_kpts)
        self.assertIn(res_sag["feedback_code"], ["HIP_TOO_LOW", "BACK_NOT_STRAIGHT"])

        # 4. Valid horizontal plank posture (straight line)
        valid_plank_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 250, "y": 100, "conf": 0.9, "valid": True},
            "left_ankle":    {"x": 400, "y": 100, "conf": 0.9, "valid": True},
        }
        for _ in range(6):
            tracker.process(valid_plank_kpts)
        tracker.last_increment_time = time.time() - 1.1
        res_valid = tracker.process(valid_plank_kpts)
        self.assertEqual(res_valid["feedback_code"], "GOOD_FORM")
        self.assertGreaterEqual(tracker.total_hold_sec, 1)

    def test_2_situps_validation(self):
        """TEST 2: Sit-ups - Valid sit-up rep & missing landmarks."""
        tracker = SitUpsTracker(down_angle=130.0, up_angle=90.0, min_displacement_px=35.0)

        # 1. Missing landmarks
        res_missing = tracker.process({})
        self.assertFalse(res_missing["valid"])

        # 2. Down posture flat on back (Hip angle ~180 deg)
        down_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 400, "y": 100, "conf": 0.9, "valid": True},
        }
        # 3. Up seated posture (Hip angle ~70 deg <= 90 deg, shoulder moved 150px)
        up_kpts = {
            "left_shoulder": {"x": 250, "y": 180, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 300, "y": 100, "conf": 0.9, "valid": True},
        }

        for _ in range(8):
            tracker.process(down_kpts)
        for _ in range(8):
            tracker.process(up_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res_rep = tracker.process(down_kpts)

        self.assertEqual(tracker.rep_count, 1)

    def test_3_crunches_validation(self):
        """TEST 3: Crunches - Valid crunch rep & posture check."""
        tracker = CrunchesTracker(down_angle=150.0, crunch_angle=140.0, min_displacement_px=20.0)


        down_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 400, "y": 100, "conf": 0.9, "valid": True},
        }
        crunch_kpts = {
            "left_shoulder": {"x": 200, "y": 180, "conf": 0.9, "valid": True},  # Hip angle 135 deg <= 138 deg
            "left_hip":      {"x": 280, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 400, "y": 100, "conf": 0.9, "valid": True},
        }

        for _ in range(8):
            tracker.process(down_kpts)
        for _ in range(8):
            tracker.process(crunch_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res_rep = tracker.process(down_kpts)

        self.assertEqual(tracker.rep_count, 1)

    def test_4_leg_raises_validation(self):
        """TEST 4: Leg Raises - Valid leg raise & bent knee anti-cheating."""
        tracker = LegRaisesTracker(down_angle=145.0, raised_angle=110.0, min_displacement_px=40.0)

        down_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 450, "y": 100, "conf": 0.9, "valid": True},
            "left_ankle":    {"x": 600, "y": 100, "conf": 0.9, "valid": True},
        }
        raised_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 300, "y": 250, "conf": 0.9, "valid": True},  # Straight legs overhead
            "left_ankle":    {"x": 300, "y": 400, "conf": 0.9, "valid": True},  # Raised 300px
        }

        # Bent knee cheat keypoints (knee angle = 90 deg < 135 deg)
        bent_knee_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 300, "y": 250, "conf": 0.9, "valid": True},
            "left_ankle":    {"x": 400, "y": 250, "conf": 0.9, "valid": True},  # Knee bent 90 deg
        }
        tracker.state = "RAISED"
        res_bent = tracker.process(bent_knee_kpts)
        self.assertEqual(res_bent["feedback_code"], "INSUFFICIENT_EXTENSION")

        tracker.state = "DOWN"
        for _ in range(8):
            tracker.process(down_kpts)
        for _ in range(8):
            tracker.process(raised_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res_rep = tracker.process(down_kpts)

        self.assertEqual(tracker.rep_count, 1)

    def test_5_russian_twists_validation(self):
        """TEST 5: Russian Twists - Valid alternating twist & flat supine posture rejection."""
        tracker = RussianTwistTracker(twist_angle=50.0, center_angle=40.0, min_displacement_px=40.0)

        # Lying flat posture (orientation invalid: incline <= 20 deg)
        flat_kpts = {
            "left_shoulder":  {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":       {"x": 400, "y": 100, "conf": 0.9, "valid": True},  # Horizontal incline
            "right_hip":      {"x": 400, "y": 100, "conf": 0.9, "valid": True},
        }
        res_flat = tracker.process(flat_kpts)
        self.assertEqual(res_flat["feedback_code"], "INCORRECT_ORIENTATION")

        center_kpts = {
            "left_shoulder":  {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":       {"x": 150, "y": 200, "conf": 0.9, "valid": True},  # Seated V-sit
            "right_wrist":    {"x": 150, "y": 150, "conf": 0.9, "valid": True},
        }
        twist_kpts = {
            "left_shoulder":  {"x": 100, "y": 130, "conf": 0.9, "valid": True},  # Torso twisted (30px tilt)
            "right_shoulder": {"x": 200, "y": 80,  "conf": 0.9, "valid": True},
            "left_hip":       {"x": 150, "y": 200, "conf": 0.9, "valid": True},
            "right_wrist":    {"x": 50,  "y": 150, "conf": 0.9, "valid": True},  # Wrists displaced 100px
        }

        for _ in range(8):
            tracker.process(center_kpts)
        for _ in range(8):
            tracker.process(twist_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res_rep = tracker.process(center_kpts)

        self.assertEqual(tracker.rep_count, 1)



    def test_6_bicycle_crunches_validation(self):
        """TEST 6: Bicycle Crunches - Valid cross-body crunch & missing landmarks."""
        tracker = BicycleCrunchTracker(crunch_angle=90.0, min_displacement_px=30.0)

        # 1. Missing landmarks
        res_missing = tracker.process({})
        self.assertFalse(res_missing["valid"])

        extended_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 250, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 80,  "conf": 0.9, "valid": True},
            "right_knee":    {"x": 400, "y": 100, "conf": 0.9, "valid": True},
        }
        crunched_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 250, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "right_knee":    {"x": 230, "y": 100, "conf": 0.9, "valid": True},  # Opposite elbow & knee meet (dist = 30px <= 80px)
        }

        for _ in range(8):
            tracker.process(extended_kpts)
        for _ in range(8):
            tracker.process(crunched_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res_rep = tracker.process(extended_kpts)

        self.assertEqual(tracker.rep_count, 1)

if __name__ == "__main__":
    unittest.main()
