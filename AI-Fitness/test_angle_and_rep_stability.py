import time
import math
import unittest
import numpy as np

from utils.angles import calculate_angle, AngleSmoother
from utils.counter import BaseExerciseTracker, TemporalStateValidator
from utils.validation import MovementDisplacementTracker
from exercises.bicep_curl import BicepCurlTracker
from exercises.squat import SquatTracker

class TestAngleAndRepStability(unittest.TestCase):
    def setUp(self):
        self.smoother = AngleSmoother(alpha=0.25, deadband_deg=0.6, max_step_deg=90.0, window_size=3)
        self.validator = TemporalStateValidator(initial_state="START", min_confirm_frames=2, min_hold_sec=0.12)
        self.curl_tracker = BicepCurlTracker()
        self.squat_tracker = SquatTracker()

    def test_1_stable_angle_no_false_state_transition(self):
        """1. Stable angle → no false state transition."""
        angles = [90.0] * 10
        smoothed = [self.smoother.update(a) for a in angles]
        for s in smoothed:
            self.assertAlmostEqual(s, 90.0, delta=1.0)
            
        res, changed = self.validator.update("START", True)
        self.assertEqual(res, "START")
        self.assertFalse(changed)

    def test_2_small_angle_jitter_no_false_rep(self):
        """2. Small angle jitter → no false rep."""
        initial_reps = self.curl_tracker.rep_count
        jitter_angles = [160.0, 155.0, 162.0, 158.0, 161.0, 157.0]
        for a in jitter_angles:
            kpts = {
                "left_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
                "left_elbow": {"x": 200, "y": 200, "conf": 0.9, "valid": True},
                "left_wrist": {"x": 200 + int(math.sin(math.radians(a-90))*100), "y": 200 + int(math.cos(math.radians(a-90))*100), "conf": 0.9, "valid": True}
            }
            self.curl_tracker.process(kpts)
            
        self.assertEqual(self.curl_tracker.rep_count, initial_reps)

    def test_3_large_single_frame_angle_spike_no_false_rep(self):
        """3. Large single-frame angle spike → no false rep."""
        s = AngleSmoother()
        s.update(160.0)
        s.update(160.0)
        spike_val = s.update(50.0)
        # Median pre-filter discards 1-frame spike of 50.0 when window has [160, 160, 50] -> median is 160!
        self.assertAlmostEqual(spike_val, 160.0, delta=2.0)

    def test_4_multiple_noisy_frames_no_false_rep(self):
        """4. Multiple noisy frames → no false rep."""
        tracker = TemporalStateValidator(initial_state="START", min_confirm_frames=3)
        noisy_states = ["EXTENDED", "CURLED", "EXTENDED", "CURLED", "EXTENDED"]
        for st in noisy_states:
            val, changed = tracker.update(st, True)
            self.assertFalse(changed)
        self.assertNotEqual(tracker.current_state, "CURLED")

    def test_5_missing_keypoints_no_false_rep(self):
        """5. Missing keypoints → no false rep."""
        s = AngleSmoother()
        s.update(90.0)
        res = s.update(None)
        self.assertEqual(res, 90.0)

    def test_6_nan_angle_no_false_rep(self):
        """6. NaN angle → no false rep."""
        s = AngleSmoother()
        s.update(90.0)
        res = s.update(float("nan"))
        self.assertEqual(res, 90.0)

    def test_7_user_moving_toward_camera_no_false_rep(self):
        """7. User moving toward camera → no false rep."""
        disp_tracker = MovementDisplacementTracker(["left_shoulder", "right_shoulder"])
        kpts_far = {
            "left_shoulder": {"x": 200, "y": 200, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 240, "y": 200, "conf": 0.9, "valid": True}
        }
        disp_tracker.capture_start(kpts_far)

        kpts_near = {
            "left_shoulder": {"x": 160, "y": 150, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 280, "y": 150, "conf": 0.9, "valid": True}
        }
        disp_tracker.update(kpts_near)
        disp = disp_tracker.get_max_displacement()
        self.assertLess(disp, 250.0)

    def test_8_user_moving_away_from_camera_no_false_rep(self):
        """8. User moving away from camera → no false rep."""
        disp_tracker = MovementDisplacementTracker(["left_shoulder", "right_shoulder"])
        kpts_near = {
            "left_shoulder": {"x": 160, "y": 150, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 280, "y": 150, "conf": 0.9, "valid": True}
        }
        disp_tracker.capture_start(kpts_near)

        kpts_far = {
            "left_shoulder": {"x": 200, "y": 200, "conf": 0.9, "valid": True},
            "right_shoulder": {"x": 240, "y": 200, "conf": 0.9, "valid": True}
        }
        disp_tracker.update(kpts_far)
        disp = disp_tracker.get_max_displacement()
        self.assertLess(disp, 250.0)

    def test_9_genuine_exercise_movement_exactly_one_rep(self):
        """9. Genuine exercise movement → exactly +1 rep."""
        tracker = BicepCurlTracker()
        
        kpts_ext = {
            "left_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow": {"x": 200, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist": {"x": 200, "y": 300, "conf": 0.9, "valid": True}
        }
        kpts_curl = {
            "left_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow": {"x": 200, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist": {"x": 200, "y": 120, "conf": 0.9, "valid": True}
        }

        # Extended position
        for _ in range(5): tracker.process(kpts_ext)
        # Curled position
        for _ in range(5): tracker.process(kpts_curl)

        time.sleep(0.45) # Allow debounce time

        # Return to Extended position
        for _ in range(5): tracker.process(kpts_ext)

        self.assertEqual(tracker.rep_count, 1)

    def test_10_genuine_repeated_movement_correct_rep_count(self):
        """10. Genuine repeated movement → correct rep count."""
        tracker = BicepCurlTracker()
        kpts_ext = {
            "left_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow": {"x": 200, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist": {"x": 200, "y": 300, "conf": 0.9, "valid": True}
        }
        kpts_curl = {
            "left_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow": {"x": 200, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist": {"x": 200, "y": 120, "conf": 0.9, "valid": True}
        }

        for rep in range(2):
            for _ in range(5): tracker.process(kpts_ext)
            for _ in range(5): tracker.process(kpts_curl)
            time.sleep(0.45)
            for _ in range(5): tracker.process(kpts_ext)
            time.sleep(0.45)

        self.assertEqual(tracker.rep_count, 2)

    def test_11_incomplete_movement_zero_reps(self):
        """11. Incomplete movement → 0 reps."""
        tracker = BicepCurlTracker()
        kpts_ext = {
            "left_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow": {"x": 200, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist": {"x": 200, "y": 300, "conf": 0.9, "valid": True}
        }
        kpts_half = {
            "left_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow": {"x": 200, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist": {"x": 280, "y": 200, "conf": 0.9, "valid": True} # ~90 deg
        }
        for _ in range(5): tracker.process(kpts_ext)
        for _ in range(5): tracker.process(kpts_half)
        for _ in range(5): tracker.process(kpts_ext)

        self.assertEqual(tracker.rep_count, 0)

    def test_12_single_frame_threshold_crossing_zero_reps(self):
        """12. State threshold crossed for only one frame → 0 reps."""
        v = TemporalStateValidator("EXTENDED", min_confirm_frames=2)
        state, changed = v.update("EXTENDED", True)
        self.assertFalse(changed)
        state, changed = v.update("CURLED", True)
        self.assertEqual(state, "EXTENDED")
        self.assertFalse(changed)
        state, changed = v.update("EXTENDED", True)
        self.assertEqual(state, "EXTENDED")
        self.assertFalse(changed)

    def test_13_valid_state_maintained_for_required_duration_transition_accepted(self):
        """13. Valid state maintained for required duration → transition accepted."""
        v = TemporalStateValidator("EXTENDED", min_confirm_frames=2)
        v.update("CURLED", True)
        state, changed = v.update("CURLED", True)
        self.assertEqual(state, "CURLED")
        self.assertTrue(changed)

    def test_14_session_reset_clears_history(self):
        """14. Session reset clears smoothing/state history."""
        s = AngleSmoother()
        s.update(50.0)
        s.reset()
        self.assertIsNone(s.smoothed_value)
        self.assertEqual(len(s.window), 0)

    def test_15_exercise_switch_does_not_retain_previous_state(self):
        """15. Exercise switch does not retain previous exercise state."""
        tracker1 = BicepCurlTracker()
        tracker1.state = "CURLED"
        tracker2 = SquatTracker()
        self.assertEqual(tracker2.state, "STANDING")

    def test_16_no_duplicate_rep_from_holding_final_position(self):
        """16. No duplicate rep from holding the final position."""
        tracker = BicepCurlTracker()
        kpts_ext = {
            "left_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow": {"x": 200, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist": {"x": 200, "y": 300, "conf": 0.9, "valid": True}
        }
        kpts_curl = {
            "left_shoulder": {"x": 200, "y": 100, "conf": 0.9, "valid": True},
            "left_elbow": {"x": 200, "y": 200, "conf": 0.9, "valid": True},
            "left_wrist": {"x": 200, "y": 120, "conf": 0.9, "valid": True}
        }
        for _ in range(5): tracker.process(kpts_ext)
        for _ in range(5): tracker.process(kpts_curl)
        time.sleep(0.45)
        for _ in range(5): tracker.process(kpts_ext)
        self.assertEqual(tracker.rep_count, 1)

        for _ in range(10): tracker.process(kpts_ext)
        self.assertEqual(tracker.rep_count, 1)

    def test_17_existing_zero_rep_behavior_remains_intact(self):
        """17. Existing zero-rep behavior remains intact."""
        tracker = BicepCurlTracker()
        self.assertEqual(tracker.rep_count, 0)
        self.assertEqual(tracker.get_form_score(), 0.0)

if __name__ == "__main__":
    unittest.main()

