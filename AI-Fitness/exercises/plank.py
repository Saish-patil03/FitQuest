import time
import numpy as np
from utils import (
    calculate_angle,
    AngleSmoother,
    BaseExerciseTracker,
    are_landmarks_valid,
    check_body_orientation,
    check_relative_elevation,
)

class PlankTracker(BaseExerciseTracker):
    """
    Multi-Layer Plank Duration Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Horizontal Body Orientation Check (Inclination <= 35.0°)
    3. Biomechanical Spine & Hip Height Alignment (No sagging hips, no piking)
    4. Continuous Position Hold Time Accumulator (Increments seconds only when form is 100% valid)
    """
    def __init__(self, min_straight_angle: float = 150.0):
        super().__init__("Plank")
        self.min_straight_angle = min_straight_angle
        self.state = "HOLDING"
        self.total_hold_sec = 0
        self.last_increment_time = time.time()
        self.body_line_smoother = AngleSmoother(alpha=0.35)

    def process(self, keypoints):
        # Layer 1: Landmark Visibility
        left_valid = are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_ankle"])
        right_valid = are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_ankle"])

        body_angles = []
        if left_valid:
            body_angles.append(self.body_line_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_ankle"])))
        if right_valid:
            body_angles.append(self.body_line_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_ankle"])))

        if not body_angles:
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"]):
                body_angles.append(self.body_line_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])))
            elif are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"]):
                body_angles.append(self.body_line_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"])))

        if not body_angles:
            return self.build_result(
                "HOLDING",
                feedback=["Position body in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position your body and key joints clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Horizontal Body Orientation Check
        is_l_horiz, l_incline = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=40.0)
        is_r_horiz, r_incline = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=40.0)

        if not is_l_horiz and not is_r_horiz:
            self.form_scores.append(0)
            return self.build_result(
                "HOLDING",
                primary_angle=float(np.mean(body_angles)),
                feedback=["Keep body horizontal for plank"],
                valid=True,
                feedback_code="BODY_NOT_HORIZONTAL",
                feedback_detail="Keep your body horizontal from shoulders to hips for plank.",
                feedback_priority=2,
            )

        avg_body_angle = float(np.mean(body_angles))
        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = f"Hold Plank! {self.total_hold_sec}s"
        fb_priority = 7
        now = time.time()

        # Layer 3: Biomechanical Spine & Hip Height Check
        if avg_body_angle < self.min_straight_angle:
            is_good_form = False
            # Check if hips sagged downward below shoulder line
            hip_y = keypoints.get("left_hip", keypoints.get("right_hip", {})).get("y", 0)
            sh_y = keypoints.get("left_shoulder", keypoints.get("right_shoulder", {})).get("y", 0)
            
            if hip_y > (sh_y + 40.0):  # Hips sagging lower on screen (y is higher value)
                feedback_list.append("Raise hips — avoid sagging core")
                fb_code = "HIP_TOO_LOW"
                fb_detail = "Raise your hips and engage your core — avoid sagging."
                fb_priority = 3
            elif hip_y < (sh_y - 40.0):  # Hips piking upward (y is lower value)
                feedback_list.append("Lower hips — keep body level")
                fb_code = "HIP_TOO_HIGH"
                fb_detail = "Lower your hips and keep your body in a level plank."
                fb_priority = 3
            else:
                feedback_list.append("Keep back straight")
                fb_code = "BACK_NOT_STRAIGHT"
                fb_detail = "Keep your back straight and maintain a strong plank position."
                fb_priority = 3

        # Layer 4: Continuous Hold Time Accumulator
        if is_good_form:
            if now - self.last_increment_time >= 1.0:
                self.total_hold_sec += 1
                self.rep_count = self.total_hold_sec
                self.last_increment_time = now
            feedback_list.append(f"Hold Plank! {self.total_hold_sec}s")
            fb_detail = f"Hold Plank! {self.total_hold_sec}s"
            self.form_scores.append(1)
        else:
            self.last_increment_time = now  # Pause hold timer on bad form
            self.form_scores.append(0)

        return self.build_result(
            "HOLDING",
            primary_angle=avg_body_angle,
            feedback=feedback_list,
            valid=True,
            feedback_code=fb_code,
            feedback_detail=fb_detail,
            feedback_priority=fb_priority,
        )
