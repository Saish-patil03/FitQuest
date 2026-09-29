import unittest
from exercises import ExerciseRegistry
from utils import calculate_angle, get_body_inclination, AngleSmoother

class Test20ExerciseSystem(unittest.TestCase):
    def test_utils_math(self):
        # 90 degree angle
        self.assertAlmostEqual(calculate_angle((0, 1), (0, 0), (1, 0)), 90.0, places=1)
        # Inclination
        self.assertEqual(get_body_inclination((100, 100), (300, 100)), 0.0)

    def test_all_20_trackers_instantiation(self):
        for choice in range(1, 21):
            tracker = ExerciseRegistry.get_tracker(choice)
            self.assertIsNotNone(tracker)
            self.assertTrue(len(tracker.name) > 0)

    def test_bicep_curl_tracking(self):
        tracker = ExerciseRegistry.get_tracker(1) # Bicep Curl
        mock_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
        }
        res = tracker.process(mock_kpts)
        self.assertEqual(res["exercise"], "Bicep Curl")
        self.assertTrue(res["valid"])

    def test_squat_tracking(self):
        tracker = ExerciseRegistry.get_tracker(2) # Squat
        mock_kpts = {
            "left_hip":   {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":  {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_ankle": {"x": 100, "y": 300, "conf": 0.9, "valid": True},
        }
        res = tracker.process(mock_kpts)
        self.assertEqual(res["exercise"], "Squat")
        self.assertTrue(res["valid"])

    def test_shoulder_press_tracking(self):
        tracker = ExerciseRegistry.get_tracker(5) # Shoulder Press
        mock_kpts = {
            "left_hip":      {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_shoulder": {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 100, "conf": 0.9, "valid": True},
        }
        res = tracker.process(mock_kpts)
        self.assertEqual(res["exercise"], "Shoulder Press")
        self.assertTrue(res["valid"])

    def test_plank_tracking(self):
        tracker = ExerciseRegistry.get_tracker(9) # Plank
        mock_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_ankle":    {"x": 300, "y": 100, "conf": 0.9, "valid": True},
        }
        res = tracker.process(mock_kpts)
        self.assertEqual(res["exercise"], "Plank")
        self.assertTrue(res["valid"])

if __name__ == "__main__":
    unittest.main()
