import unittest
import time
from exercise import calculate_angle, AngleSmoother, PushUpTracker, SquatTracker, SitUpTracker, ExerciseController

class TestExerciseMathAndTrackers(unittest.TestCase):
    def test_calculate_angle_90_deg(self):
        a = (0, 1)
        b = (0, 0)
        c = (1, 0)
        angle = calculate_angle(a, b, c)
        self.assertAlmostEqual(angle, 90.0, places=1)

    def test_calculate_angle_180_deg(self):
        a = (-1, 0)
        b = (0, 0)
        c = (1, 0)
        angle = calculate_angle(a, b, c)
        self.assertAlmostEqual(angle, 180.0, places=1)

    def test_angle_smoother(self):
        smoother = AngleSmoother(alpha=0.5)
        v1 = smoother.update(100.0)
        self.assertEqual(v1, 100.0)
        v2 = smoother.update(120.0)
        self.assertEqual(v2, 110.0)

    def test_pushup_state_machine(self):
        tracker = PushUpTracker(up_angle=150.0, down_angle=110.0, debounce_sec=0.1)

        up_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 300, "y": 100, "conf": 0.9, "valid": True},
        }

        down_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 110, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 300, "y": 100, "conf": 0.9, "valid": True},
        }

        res_up = tracker.process(up_kpts)
        self.assertEqual(tracker.state, "UP")
        self.assertIsNotNone(res_up["primary_angle"])
        self.assertEqual(tracker.rep_count, 0)

        for _ in range(5):
            tracker.process(down_kpts)
        self.assertEqual(tracker.state, "DOWN")

        time.sleep(0.15)
        for _ in range(5):
            tracker.process(up_kpts)
        self.assertEqual(tracker.state, "UP")
        self.assertEqual(tracker.rep_count, 1)

    def test_squat_state_machine(self):
        tracker = SquatTracker(standing_angle=150.0, squat_angle=110.0, debounce_sec=0.1)

        standing_kpts = {
            "left_hip":   {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":  {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_ankle": {"x": 100, "y": 300, "conf": 0.9, "valid": True},
        }

        squat_kpts = {
            "left_hip":   {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":  {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_ankle": {"x": 100, "y": 300, "conf": 0.9, "valid": True},
        }

        res_stand = tracker.process(standing_kpts)
        self.assertEqual(tracker.state, "STANDING")
        self.assertIsNotNone(res_stand["primary_angle"])
        self.assertEqual(tracker.rep_count, 0)

        for _ in range(5):
            tracker.process(squat_kpts)
        self.assertEqual(tracker.state, "SQUAT")

        time.sleep(0.15)
        for _ in range(5):
            tracker.process(standing_kpts)
        self.assertEqual(tracker.state, "STANDING")
        self.assertEqual(tracker.rep_count, 1)

    def test_situp_state_machine(self):
        tracker = SitUpTracker(down_angle=135.0, up_angle=85.0, debounce_sec=0.1)

        down_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 300, "y": 100, "conf": 0.9, "valid": True},
        }

        up_kpts = {
            "left_shoulder": {"x": 250, "y": 180, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 300, "y": 100, "conf": 0.9, "valid": True},
        }

        res_down = tracker.process(down_kpts)
        self.assertEqual(tracker.state, "DOWN")
        self.assertIsNotNone(res_down["primary_angle"])
        self.assertEqual(tracker.rep_count, 0)

        for _ in range(5):
            tracker.process(up_kpts)
        self.assertEqual(tracker.state, "UP")

        time.sleep(0.15)
        for _ in range(5):
            tracker.process(down_kpts)
        self.assertEqual(tracker.state, "DOWN")
        self.assertEqual(tracker.rep_count, 1)

if __name__ == "__main__":
    unittest.main()
