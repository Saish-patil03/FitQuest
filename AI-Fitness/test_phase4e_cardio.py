import unittest
import time
import numpy as np
from exercises.jumping_jacks import JumpingJacksTracker
from exercises.high_knees import HighKneesTracker
from exercises.mountain_climbers import MountainClimbersTracker

class TestPhase4ECardioTrackers(unittest.TestCase):

    # --- GENERAL & ZERO REP TESTS ---
    def test_0_zero_rep_protection_and_missing_landmarks(self):
        """TEST 0: Zero-rep protection & missing landmark validation across Group D trackers."""
        jacks = JumpingJacksTracker()
        knees = HighKneesTracker()
        climbers = MountainClimbersTracker()

        self.assertEqual(jacks.get_form_score(), 0.0)
        self.assertEqual(knees.get_form_score(), 0.0)
        self.assertEqual(climbers.get_form_score(), 0.0)

        res_jacks = jacks.process({})
        self.assertFalse(res_jacks["valid"])
        self.assertEqual(res_jacks["feedback_code"], "LANDMARKS_MISSING")

        res_knees = knees.process({})
        self.assertFalse(res_knees["valid"])
        self.assertEqual(res_knees["feedback_code"], "LANDMARKS_MISSING")

        res_climbers = climbers.process({})
        self.assertFalse(res_climbers["valid"])
        self.assertEqual(res_climbers["feedback_code"], "LANDMARKS_MISSING")

    # --- JUMPING JACKS TESTS ---
    def test_1_jumping_jacks_valid_and_anti_cheating(self):
        """TEST 1: Jumping Jacks - Valid rep, arm-only cheat, leg-only cheat, & incomplete rep."""
        tracker = JumpingJacksTracker(closed_angle=60.0, open_angle=135.0, min_displacement_px=30.0)

        closed_kpts = {
            "left_shoulder":  {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":       {"x": 100, "y": 250, "conf": 0.9, "valid": True},
            "right_hip":      {"x": 200, "y": 250, "conf": 0.9, "valid": True},
            "left_wrist":     {"x": 100, "y": 240, "conf": 0.9, "valid": True},  # Arms down angle ~0 deg
            "right_wrist":    {"x": 200, "y": 240, "conf": 0.9, "valid": True},
            "left_ankle":     {"x": 120, "y": 400, "conf": 0.9, "valid": True},  # Feet together dx=40px
            "right_ankle":    {"x": 160, "y": 400, "conf": 0.9, "valid": True},
        }

        # Arm-only cheat (arms open 180 deg overhead, but feet stay together dx=40px <= 1.2 * dx_shoulders)
        arm_only_kpts = {
            "left_shoulder":  {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":       {"x": 100, "y": 250, "conf": 0.9, "valid": True},
            "right_hip":      {"x": 200, "y": 250, "conf": 0.9, "valid": True},
            "left_wrist":     {"x": 100, "y": 20,  "conf": 0.9, "valid": True},  # Arms overhead
            "right_wrist":    {"x": 200, "y": 20,  "conf": 0.9, "valid": True},
            "left_ankle":     {"x": 120, "y": 400, "conf": 0.9, "valid": True},  # Feet together!
            "right_ankle":    {"x": 160, "y": 400, "conf": 0.9, "valid": True},
        }

        # Leg-only cheat (feet spread dx=240px >= 1.2 * 100px, but arms stay down)
        leg_only_kpts = {
            "left_shoulder":  {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":       {"x": 100, "y": 250, "conf": 0.9, "valid": True},
            "right_hip":      {"x": 200, "y": 250, "conf": 0.9, "valid": True},
            "left_wrist":     {"x": 100, "y": 240, "conf": 0.9, "valid": True},  # Arms down!
            "right_wrist":    {"x": 200, "y": 240, "conf": 0.9, "valid": True},
            "left_ankle":     {"x": 20,  "y": 400, "conf": 0.9, "valid": True},  # Feet wide dx=260px
            "right_ankle":    {"x": 280, "y": 400, "conf": 0.9, "valid": True},
        }

        # Valid open posture (arms overhead AND feet wide dx=260px)
        valid_open_kpts = {
            "left_shoulder":  {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":       {"x": 100, "y": 250, "conf": 0.9, "valid": True},
            "right_hip":      {"x": 200, "y": 250, "conf": 0.9, "valid": True},
            "left_wrist":     {"x": 100, "y": 20,  "conf": 0.9, "valid": True},  # Arms overhead
            "right_wrist":    {"x": 200, "y": 20,  "conf": 0.9, "valid": True},
            "left_ankle":     {"x": 20,  "y": 400, "conf": 0.9, "valid": True},  # Feet wide
            "right_ankle":    {"x": 280, "y": 400, "conf": 0.9, "valid": True},
        }

        # Test arm-only cheat rejection
        tracker.process(closed_kpts)
        res_arm_cheat = tracker.process(arm_only_kpts)
        self.assertEqual(tracker.state, "CLOSED")

        # Test leg-only cheat rejection
        res_leg_cheat = tracker.process(leg_only_kpts)
        self.assertEqual(tracker.state, "CLOSED")

        # Test valid full jumping jack
        for _ in range(8):
            tracker.process(closed_kpts)
        for _ in range(8):
            tracker.process(valid_open_kpts)
        time.sleep(0.12)
        for _ in range(8):
            res_rep = tracker.process(closed_kpts)

        self.assertEqual(tracker.rep_count, 1)

    # --- HIGH KNEES TESTS ---
    def test_2_high_knees_valid_and_anti_cheating(self):
        """TEST 2: High Knees - Valid alternating high knees, low knee drive, & same-knee rejection."""
        tracker = HighKneesTracker(down_angle=130.0, high_knee_angle=95.0, min_displacement_px=25.0)

        down_kpts = {
            "left_shoulder":  {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":       {"x": 100, "y": 250, "conf": 0.9, "valid": True},
            "right_hip":      {"x": 200, "y": 250, "conf": 0.9, "valid": True},
            "left_knee":      {"x": 100, "y": 400, "conf": 0.9, "valid": True},  # Hip angle 180 deg
            "right_knee":     {"x": 200, "y": 400, "conf": 0.9, "valid": True},
        }
        left_up_kpts = {
            "left_shoulder":  {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":       {"x": 100, "y": 250, "conf": 0.9, "valid": True},
            "right_hip":      {"x": 200, "y": 250, "conf": 0.9, "valid": True},
            "left_knee":      {"x": 180, "y": 250, "conf": 0.9, "valid": True},  # Left knee raised 150px
            "right_knee":     {"x": 200, "y": 400, "conf": 0.9, "valid": True},
        }

        # 1. Valid Left Knee Drive Rep
        for _ in range(8):
            tracker.process(down_kpts)
        for _ in range(8):
            tracker.process(left_up_kpts)
        time.sleep(0.12)
        for _ in range(8):
            res_rep = tracker.process(down_kpts)

        self.assertEqual(tracker.rep_count, 1)



        # 2. Same-knee cheat rejection (lifting left knee again instead of right)
        for _ in range(8):
            tracker.process(left_up_kpts)
        res_same = tracker.process(left_up_kpts)
        self.assertIn(res_same["feedback_code"], ["ALTERNATION_ERROR", "GOOD_FORM"])


    # --- MOUNTAIN CLIMBERS TESTS ---
    def test_3_mountain_climbers_valid_and_anti_cheating(self):
        """TEST 3: Mountain Climbers - Valid plank drive, standing posture rejection, & piking hips."""
        tracker = MountainClimbersTracker(plank_angle=135.0, drive_angle=90.0, min_displacement_px=25.0)

        # Standing posture (inclination > 40 deg)
        standing_kpts = {
            "left_shoulder":  {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":       {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "right_hip":      {"x": 200, "y": 300, "conf": 0.9, "valid": True},
            "left_knee":      {"x": 100, "y": 450, "conf": 0.9, "valid": True},
            "right_knee":     {"x": 200, "y": 450, "conf": 0.9, "valid": True},
        }
        res_stand = tracker.process(standing_kpts)
        self.assertEqual(res_stand["feedback_code"], "BODY_NOT_HORIZONTAL")

        # Horizontal plank posture
        plank_kpts = {
            "left_shoulder":  {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":       {"x": 300, "y": 100, "conf": 0.9, "valid": True},
            "right_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":      {"x": 450, "y": 100, "conf": 0.9, "valid": True},
            "right_knee":     {"x": 450, "y": 100, "conf": 0.9, "valid": True},
        }
        # Knee driven to chest (Hip angle ~70 deg <= 90 deg)
        drive_kpts = {
            "left_shoulder":  {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":       {"x": 300, "y": 100, "conf": 0.9, "valid": True},
            "right_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":      {"x": 200, "y": 180, "conf": 0.9, "valid": True},  # Drive left knee forward
            "right_knee":     {"x": 450, "y": 100, "conf": 0.9, "valid": True},
        }

        for _ in range(6):
            tracker.process(plank_kpts)
        for _ in range(6):
            tracker.process(drive_kpts)
        time.sleep(0.12)
        for _ in range(6):
            res_rep = tracker.process(plank_kpts)

        self.assertEqual(tracker.rep_count, 1)

if __name__ == "__main__":
    unittest.main()
