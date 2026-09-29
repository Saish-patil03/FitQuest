import unittest
import time
import numpy as np
import cv2
from exercises.pushup import PushUpTracker
from exercises.bicep_curl import BicepCurlTracker
from pose import PoseDetector
from utils.validation import FeedbackStabilizer, FEEDBACK_CODES

class TestPhase3FeedbackAndOverlay(unittest.TestCase):

    def test_1_valid_pushup_feedback(self):
        """TEST 1: Valid Push-Up → GOOD_FORM."""
        tracker = PushUpTracker(up_angle=150.0, down_angle=110.0, min_displacement_px=5.0)
        valid_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
            "left_knee":     {"x": 400, "y": 100, "conf": 0.9, "valid": True},
        }
        res = tracker.process(valid_kpts)
        self.assertEqual(res["feedback_code"], "GOOD_FORM")
        self.assertEqual(res["feedback_priority"], 7)

    def test_2_standing_person_pushup_feedback(self):
        """TEST 2: Standing person moving arms → BODY_NOT_HORIZONTAL."""
        tracker = PushUpTracker()
        standing_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 110, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 100, "y": 400, "conf": 0.9, "valid": True}, # Vertical inclination
        }
        res = tracker.process(standing_kpts)
        self.assertEqual(res["feedback_code"], "BODY_NOT_HORIZONTAL")
        self.assertEqual(res["feedback_priority"], 2)
        self.assertIn("Keep your body horizontal", res["feedback_detail"])

    def test_3_pushup_incorrect_body_line_feedback(self):
        """TEST 3: Push-Up with sagging hips → BACK_NOT_STRAIGHT."""
        tracker = PushUpTracker()
        sagging_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 200, "y": 250, "conf": 0.9, "valid": True}, # Sagging hip (angle < 140)
            "left_knee":     {"x": 300, "y": 100, "conf": 0.9, "valid": True},
        }
        res = tracker.process(sagging_kpts)
        self.assertEqual(res["feedback_code"], "BACK_NOT_STRAIGHT")
        self.assertEqual(res["feedback_priority"], 3)
        self.assertIn("back straight", res["feedback_detail"])

    def test_4_pushup_insufficient_movement_feedback(self):
        """TEST 4: Push-Up with insufficient displacement → INSUFFICIENT_MOVEMENT."""
        tracker = PushUpTracker(up_angle=150.0, down_angle=110.0, min_displacement_px=200.0)
        up_kpts = {

            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 100, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 100, "conf": 0.9, "valid": True},
        }
        tiny_down_kpts = {
            "left_shoulder": {"x": 100, "y": 102, "conf": 0.9, "valid": True},  # 2px displacement
            "left_elbow":    {"x": 200, "y": 120, "conf": 0.9, "valid": True},  # Elbow bent < 110 deg
            "left_wrist":    {"x": 100, "y": 300, "conf": 0.9, "valid": True},
            "left_hip":      {"x": 300, "y": 102, "conf": 0.9, "valid": True},
        }
        for _ in range(6):
            tracker.process(up_kpts)
        for _ in range(6):
            tracker.process(tiny_down_kpts)
        time.sleep(0.45)
        insufficient_codes = []
        for _ in range(6):
            res = tracker.process(up_kpts)
            insufficient_codes.append(res["feedback_code"])
        self.assertIn("INSUFFICIENT_MOVEMENT", insufficient_codes)



    def test_5_missing_landmarks_feedback(self):
        """TEST 5: Missing landmarks → LANDMARKS_MISSING."""
        tracker = PushUpTracker()
        missing_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.1, "valid": False},
        }
        res = tracker.process(missing_kpts)
        self.assertFalse(res["valid"])
        self.assertEqual(res["feedback_code"], "LANDMARKS_MISSING")
        self.assertEqual(res["feedback_priority"], 1)

    def test_6_bicep_curl_elbow_misaligned_feedback(self):
        """TEST 6: Bicep curl with excessive elbow drift → ELBOW_MISALIGNED."""
        tracker = BicepCurlTracker()
        drift_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 200, "y": 150, "conf": 0.9, "valid": True}, # dx = 100 > 80
            "left_wrist":    {"x": 200, "y": 250, "conf": 0.9, "valid": True},
        }
        res = tracker.process(drift_kpts)
        self.assertEqual(res["feedback_code"], "ELBOW_MISALIGNED")
        self.assertEqual(res["feedback_priority"], 3)
        self.assertIn("upper arm still", res["feedback_detail"])

    def test_7_correct_bicep_curl_feedback(self):
        """TEST 7: Correct Bicep Curl → GOOD_FORM."""
        tracker = BicepCurlTracker()
        good_kpts = {
            "left_shoulder": {"x": 100, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow":    {"x": 110, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist":    {"x": 110, "y": 300, "conf": 0.9, "valid": True},
        }
        res = tracker.process(good_kpts)
        self.assertEqual(res["feedback_code"], "GOOD_FORM")
        self.assertEqual(res["feedback_priority"], 7)

    def test_8_feedback_stabilizer_priority_override_and_holding(self):
        """TEST 8: FeedbackStabilizer overrides higher priority immediately and holds lower priority."""
        stabilizer = FeedbackStabilizer(min_hold_sec=0.4)

        # 1. Starts at GOOD_FORM (P7)
        c1, m1, p1 = stabilizer.update("GOOD_FORM")
        self.assertEqual(c1, "GOOD_FORM")

        # 2. High priority error (P2) overrides immediately
        c2, m2, p2 = stabilizer.update("BODY_NOT_HORIZONTAL")
        self.assertEqual(c2, "BODY_NOT_HORIZONTAL")
        self.assertEqual(p2, 2)

        # 3. Lower priority error (P4) within hold window does NOT override P2
        c3, m3, p3 = stabilizer.update("INSUFFICIENT_DEPTH")
        self.assertEqual(c3, "BODY_NOT_HORIZONTAL")

        # 4. Critical error (P1) overrides P2 immediately
        c4, m4, p4 = stabilizer.update("LANDMARKS_MISSING")
        self.assertEqual(c4, "LANDMARKS_MISSING")
        self.assertEqual(p4, 1)

    def test_9_opencv_hud_rendering_and_text_wrapping(self):
        """TEST 9: OpenCV HUD rendering executes cleanly without clipping or error on 640x480 frame."""
        detector = PoseDetector(model_path="models/pose_model.pt")
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        mock_tracker_info = {
            "exercise": "Push-up",
            "rep_count": 5,
            "state": "UP",
            "primary_angle": 165.2,
            "form_score": 90.0,
            "feedback": ["Horizontal body posture required"],
            "feedback_code": "BODY_NOT_HORIZONTAL",
            "feedback_detail": "Keep your body horizontal from shoulders to hips and maintain a straight plank.",
            "feedback_priority": 2,
            "valid": True
        }

        # Render HUD on dummy frame
        detector.draw_hud(dummy_frame, mock_tracker_info, body_detected=True)
        self.assertEqual(dummy_frame.shape, (480, 640, 3))

if __name__ == "__main__":
    unittest.main()
