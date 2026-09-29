import unittest
import time
from exercises.pushup import PushUpTracker
from utils.validation import (
    validate_landmarks,
    check_body_orientation,
    calculate_distance,
    MovementDisplacementTracker,
)

class TestPushUpMultiLayerValidation(unittest.TestCase):

    def test_validation_utilities(self):
        # 1. Landmark Validation
        kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 200, "conf": 0.2, "valid": False},
        }
        self.assertTrue(validate_landmarks(kpts, ["left_shoulder"], min_conf=0.5))
        self.assertFalse(validate_landmarks(kpts, ["left_elbow"], min_conf=0.5))

        # 2. Body Orientation Check (Horizontal vs Vertical)
        horiz_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
        }
        is_h, inc_h = check_body_orientation(horiz_kpts, "left_shoulder", "left_hip", max_horizontal_deg=45.0)
        self.assertTrue(is_h)
        self.assertLessEqual(inc_h, 45.0)

        vert_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 100, "y": 300, "conf": 0.9, "valid": True},
        }
        is_v, inc_v = check_body_orientation(vert_kpts, "left_shoulder", "left_hip", max_horizontal_deg=45.0)
        self.assertFalse(is_v)
        self.assertGreater(inc_v, 60.0)

        # 3. Displacement Tracker
        disp_tracker = MovementDisplacementTracker(["left_shoulder"])
        disp_tracker.capture_start(horiz_kpts)
        moved_kpts = {
            "left_shoulder": {"x": 100, "y": 150, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 150, "conf": 0.9, "valid": True},
        }
        disp_tracker.update(moved_kpts)
        self.assertEqual(disp_tracker.get_max_displacement(), 50.0)

    def test_1_valid_pushup(self):
        """TEST 1: Valid horizontal push-up pose → accepted and counted."""
        tracker = PushUpTracker(up_angle=150.0, down_angle=110.0, debounce_sec=0.1, min_displacement_px=5.0)

        up_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 400, "y": 100, "conf": 0.9, "valid": True},
        }

        down_kpts = {
            "left_shoulder": {"x": 100, "y": 130, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 200, "y": 120, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 130, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 400, "y": 130, "conf": 0.9, "valid": True},
        }

        res1 = tracker.process(up_kpts)
        self.assertEqual(tracker.state, "UP")
        self.assertEqual(tracker.rep_count, 0)

        for _ in range(8):
            tracker.process(down_kpts)
        self.assertEqual(tracker.state, "DOWN")

        time.sleep(0.45)
        for _ in range(8):
            tracker.process(up_kpts)

        self.assertEqual(tracker.state, "UP")
        self.assertEqual(tracker.rep_count, 1)

    def test_2_standing_person_arm_movement_rejected(self):
        """TEST 2 & ANTI-CHEATING: Standing person with push-up-like elbow angle → REJECTED."""
        tracker = PushUpTracker(up_angle=150.0, down_angle=110.0, debounce_sec=0.1)

        # Standing posture (inclination ~ 90 deg)
        standing_up_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 100, "y": 400, "conf": 0.9, "valid": True},  # Vertical alignment!
            "left_knee":     {"x": 100, "y": 500, "conf": 0.9, "valid": True},
        }

        standing_down_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 200, "y": 100, "conf": 0.9, "valid": True},  # Bent elbow!
            "left_wrist":    {"x": 100, "y": 110, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 100, "y": 400, "conf": 0.9, "valid": True},  # Still vertical!
            "left_knee":     {"x": 100, "y": 500, "conf": 0.9, "valid": True},
        }

        res_up = tracker.process(standing_up_kpts)
        self.assertEqual(tracker.state, "UP")

        # Try to push down while standing
        for _ in range(5):
            res_down = tracker.process(standing_down_kpts)

        # State MUST REMAIN UP and rep count MUST REMAIN 0!
        self.assertEqual(tracker.state, "UP")
        self.assertEqual(tracker.rep_count, 0)
        self.assertIn("Horizontal body posture required", res_down["feedback"])

        time.sleep(0.15)
        for _ in range(5):
            tracker.process(standing_up_kpts)

        self.assertEqual(tracker.rep_count, 0)
        self.assertEqual(tracker.get_form_score(), 0.0)

    def test_3_incorrect_body_orientation_rejected(self):
        """TEST 3: Correct arm angle but angled/upright body orientation → rejected."""
        tracker = PushUpTracker(up_angle=150.0, down_angle=110.0, max_inclination_deg=30.0)

        # Angled at 60 degrees (e.g. leaning against wall)
        angled_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 110, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 200, "y": 273, "conf": 0.9, "valid": True},  # 60 degree inclination
        }

        res = tracker.process(angled_kpts)
        self.assertEqual(tracker.rep_count, 0)
        self.assertIn("Horizontal body posture required", res["feedback"])

    def test_4_insufficient_movement_rejected(self):
        """TEST 4: Correct body orientation but insufficient movement → rejected."""
        tracker = PushUpTracker(up_angle=150.0, down_angle=110.0, debounce_sec=0.1, min_displacement_px=20.0)

        up_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
        }

        # Virtually no movement (less than 20px)
        tiny_move_down_kpts = {
            "left_shoulder": {"x": 100, "y": 101, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 102, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
        }

        tracker.process(up_kpts)
        tracker.process(tiny_move_down_kpts)
        time.sleep(0.15)
        tracker.process(up_kpts)

        self.assertEqual(tracker.rep_count, 0)

    def test_5_missing_low_confidence_landmarks(self):
        """TEST 5: Missing or low-confidence critical landmarks → rejected."""
        tracker = PushUpTracker()

        low_conf_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.1, "valid": False},
            "left_elbow":    {"x": 100, "y": 200, "conf": 0.1, "valid": False},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.1, "valid": False},
        }

        res = tracker.process(low_conf_kpts)
        self.assertFalse(res["valid"])
        self.assertEqual(tracker.rep_count, 0)

    def test_7_multiple_valid_pushups(self):
        """TEST 7: Multiple valid push-ups → correct rep count."""
        tracker = PushUpTracker(up_angle=150.0, down_angle=110.0, debounce_sec=0.05, min_displacement_px=5.0)

        up_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 400, "y": 100, "conf": 0.9, "valid": True},
        }

        down_kpts = {
            "left_shoulder": {"x": 100, "y": 130, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 200, "y": 120, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 130, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 400, "y": 130, "conf": 0.9, "valid": True},
        }

        for _ in range(3):
            for _ in range(8):
                tracker.process(down_kpts)
            time.sleep(0.45)
            for _ in range(8):
                tracker.process(up_kpts)
            time.sleep(0.45)


        self.assertEqual(tracker.rep_count, 3)
        self.assertGreater(tracker.get_form_score(), 0.0)

    def test_8_zero_rep_protection(self):
        """TEST 8: Zero-rep session → existing zero-rep protection remains intact."""
        tracker = PushUpTracker()
        self.assertEqual(tracker.rep_count, 0)
        self.assertEqual(tracker.get_form_score(), 0.0)

if __name__ == "__main__":
    unittest.main()
