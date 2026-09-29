import unittest
import time
import numpy as np
from exercises.squat import SquatTracker
from exercises.lunges import LungesTracker
from exercises.side_lunge import SideLungeTracker
from exercises.glute_bridge import GluteBridgeTracker
from exercises.calf_raise import CalfRaiseTracker

class TestPhase4BLowerBodyTrackers(unittest.TestCase):

    def test_squat_anti_cheating_and_validation(self):
        """TEST 1: Squat - Valid squat vs standing nod & missing landmarks."""
        tracker = SquatTracker()

        # Missing landmarks
        res_missing = tracker.process({})
        self.assertFalse(res_missing["valid"])
        self.assertEqual(res_missing["feedback_code"], "LANDMARKS_MISSING")

        # Valid standing posture
        stand_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_ankle":    {"x": 100, "y": 400, "conf": 0.9, "valid": True},
        }
        res_stand = tracker.process(stand_kpts)
        self.assertTrue(res_stand["valid"])
        self.assertEqual(res_stand["feedback_code"], "GOOD_FORM")

        # Deep squat position
        squat_kpts = {
            "left_shoulder": {"x": 100, "y": 150, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 100, "y": 250, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 180, "y": 250, "conf": 0.9, "valid": True},  # Bent < 110°
            "left_ankle":    {"x": 100, "y": 400, "conf": 0.9, "valid": True},
        }
        for _ in range(8):
            tracker.process(stand_kpts)
        for _ in range(8):
            tracker.process(squat_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res_rep = tracker.process(stand_kpts)

        self.assertEqual(tracker.rep_count, 1)

    def test_lunges_anti_cheating_and_validation(self):
        """TEST 2: Lunges - Lunge depth and posture validation."""
        tracker = LungesTracker()

        stand_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_ankle":    {"x": 100, "y": 400, "conf": 0.9, "valid": True},
        }
        lunge_kpts = {
            "left_shoulder": {"x": 100, "y": 140, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 100, "y": 240, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 170, "y": 240, "conf": 0.9, "valid": True},
            "left_ankle":    {"x": 100, "y": 400, "conf": 0.9, "valid": True},
        }

        for _ in range(8):
            tracker.process(stand_kpts)
        for _ in range(8):
            tracker.process(lunge_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res = tracker.process(stand_kpts)

        self.assertEqual(tracker.rep_count, 1)

    def test_side_lunge_anti_cheating(self):
        """TEST 3: Side Lunge - Lateral displacement & straight leg check."""
        tracker = SideLungeTracker()

        stand_kpts = {
            "left_hip":   {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":  {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_ankle": {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "right_hip":  {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "right_knee": {"x": 200, "y": 200, "conf": 0.9, "valid": True},
            "right_ankle":{"x": 200, "y": 300, "conf": 0.9, "valid": True},
        }
        side_lunge_kpts = {
            "left_hip":   {"x": 150, "y": 140, "conf": 0.9, "valid": True},  # Shifted right 50px
            "left_knee":  {"x": 220, "y": 140, "conf": 0.9, "valid": True},  # Left knee bent < 115°
            "left_ankle": {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "right_hip":  {"x": 250, "y": 140, "conf": 0.9, "valid": True},
            "right_knee": {"x": 250, "y": 220, "conf": 0.9, "valid": True},  # Right leg straight
            "right_ankle":{"x": 250, "y": 300, "conf": 0.9, "valid": True},
        }

        for _ in range(8):
            tracker.process(stand_kpts)
        for _ in range(8):
            tracker.process(side_lunge_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res = tracker.process(stand_kpts)

        self.assertEqual(tracker.rep_count, 1)

    def test_glute_bridge_supine_and_extension(self):
        """TEST 4: Glute Bridge - Supine orientation check and hip elevation."""
        tracker = GluteBridgeTracker()

        # Standing keypoints (orientation invalid for glute bridge: inclination > 40)
        standing_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 100, "y": 300, "conf": 0.9, "valid": True},  # Vertical vector
            "left_knee":     {"x": 100, "y": 450, "conf": 0.9, "valid": True},
        }
        res_orient = tracker.process(standing_kpts)
        self.assertEqual(res_orient["feedback_code"], "INCORRECT_ORIENTATION")

        # Flat supine keypoints on floor: hip bent (angle ~98 < 130 deg)
        down_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 250, "conf": 0.9, "valid": True},  # Hip lower on floor (dy=150px)
            "left_knee":     {"x": 450, "y": 100, "conf": 0.9, "valid": True},
        }
        # Bridge keypoints: hips lifted high (straight line angle 180 >= 160 deg)
        bridge_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},  # Hips lifted 150px
            "left_knee":     {"x": 450, "y": 100, "conf": 0.9, "valid": True},
        }

        for _ in range(8):
            tracker.process(down_kpts)
        for _ in range(8):
            tracker.process(bridge_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res = tracker.process(down_kpts)

        self.assertEqual(tracker.rep_count, 1)

    def test_calf_raise_displacement_and_knees(self):
        """TEST 5: Calf Raise - Vertical heel displacement & knee straightness."""
        tracker = CalfRaiseTracker()

        # Flat heel stance (angle 180 deg)
        flat_kpts = {
            "left_hip":   {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":  {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_ankle": {"x": 100, "y": 300, "conf": 0.9, "valid": True},
        }
        # Raised heel stance (ankle lifted 30px, ratio = 70/100 -> effective angle 126 <= 135 deg)
        raised_kpts = {
            "left_hip":   {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":  {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_ankle": {"x": 100, "y": 270, "conf": 0.9, "valid": True},  # Heel raised 30px
        }

        for _ in range(8):
            tracker.process(flat_kpts)
        for _ in range(8):
            tracker.process(raised_kpts)
        time.sleep(0.45)
        for _ in range(8):
            res = tracker.process(flat_kpts)

        self.assertEqual(tracker.rep_count, 1)





if __name__ == "__main__":
    unittest.main()
