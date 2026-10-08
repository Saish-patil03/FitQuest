import time
import numpy as np
from utils import (
    calculate_angle,
    AngleSmoother,
    BaseExerciseTracker,
    are_landmarks_valid,
    check_body_orientation,
    MovementDisplacementTracker,
)

class GluteBridgeTracker(BaseExerciseTracker):
    """
    Multi-Layer Glute Bridge Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Supine Posture Check (Body Inclination <= 35.0° relative to horizontal)
    3. Full Hip Extension Alignment (Shoulder-Hip-Knee >= 160.0°)
    4. Vertical Hip Lift Displacement
    """
    def __init__(
        self,
        down_angle: float = 130.0,
        bridge_angle: float = 160.0,
        debounce_sec: float = 0.4,
        min_displacement_px: float = 25.0,
    ):
        super().__init__("Glute Bridge")
        self.down_angle = down_angle
        self.bridge_angle = bridge_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "DOWN"
        self.last_rep_time = 0.0

        self.left_hip_smoother = AngleSmoother(alpha=0.35)
        self.right_hip_smoother = AngleSmoother(alpha=0.35)
        self.max_angle_in_rep = 0.0
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_hip", "right_hip"]
        )

    def process(self, keypoints):
        # Layer 1: Landmark Visibility
        left_valid = are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"])
        right_valid = are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"])

        hip_angles = []
        if left_valid:
            hip_angles.append(self.left_hip_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])))
        if right_valid:
            hip_angles.append(self.right_hip_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"])))

        if not hip_angles:
            return self.build_result(
                "DOWN",
                feedback=["Position torso and legs in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position your torso and legs clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Orientation Check (Supine posture required)
        is_l_horiz, _ = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=40.0)
        is_r_horiz, _ = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=40.0)

        if not is_l_horiz and not is_r_horiz:
            return self.build_result(
                self.state,
                primary_angle=float(np.mean(hip_angles)),
                feedback=["Lie flat on back for glute bridge"],
                valid=True,
                feedback_code="INCORRECT_ORIENTATION",
                feedback_detail="Lie flat on your back for glute bridges.",
                feedback_priority=2,
            )

        avg_hip_angle = float(np.mean(hip_angles))
        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great glute bridge! Squeeze glutes at top."
        fb_priority = 7
        now = time.time()

        # Layer 3 & 4: State Machine & Movement Displacement
        if self.state == "DOWN":
            if avg_hip_angle >= self.bridge_angle:
                self.state = "BRIDGE"
                self.max_angle_in_rep = avg_hip_angle
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Squeeze glutes! Lower hips")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Great hip extension! Lower hips under control."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Lift Hips")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Drive through your heels to lift hips overhead."
                    fb_priority = 7

        elif self.state == "BRIDGE":
            self.displacement_tracker.update(keypoints)

            if avg_hip_angle > self.max_angle_in_rep:
                self.max_angle_in_rep = avg_hip_angle

            if avg_hip_angle <= self.down_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.max_angle_in_rep >= self.bridge_angle:
                        feedback_list.append("Great Bridge!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great glute bridge! Excellent hip drive."
                        fb_priority = 7
                    else:
                        feedback_list.append("Lift hips higher next time")
                        is_good_form = False
                        fb_code = "INSUFFICIENT_EXTENSION"
                        fb_detail = "Drive hips higher until shoulders, hips, and knees form a straight line."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Lift your hips vertically off the floor."
                    fb_priority = 5

                self.state = "DOWN"
                self.max_angle_in_rep = 0.0
            else:
                if is_good_form:
                    feedback_list.append("Lower Hips")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Lower hips smoothly back to floor."
                    fb_priority = 7

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(
            self.state,
            primary_angle=avg_hip_angle,
            feedback=feedback_list,
            valid=True,
            feedback_code=fb_code,
            feedback_detail=fb_detail,
            feedback_priority=fb_priority,
        )
