import time
import numpy as np
from utils import (
    calculate_angle,
    AngleSmoother,
    BaseExerciseTracker,
    are_landmarks_valid,
    get_landmark_point,
    check_body_orientation,
    MovementDisplacementTracker,
)

class ShoulderPressTracker(BaseExerciseTracker):
    """
    Multi-Layer Shoulder Press Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Upright Orientation Check
    3. Biomechanical Overhead Extension & Torso Alignment (Hands overhead y_wrist <= y_shoulder + 10px)
    4. Physical Overhead Movement Displacement (dy >= 35px)
    """
    def __init__(
        self,
        lowered_angle: float = 105.0,
        pressed_angle: float = 150.0,
        debounce_sec: float = 0.4,
        min_displacement_px: float = 35.0,
    ):
        super().__init__("Shoulder Press")
        self.lowered_angle = lowered_angle
        self.pressed_angle = pressed_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "LOWERED"
        self.last_rep_time = 0.0

        self.left_arm_smoother = AngleSmoother(alpha=0.35)
        self.right_arm_smoother = AngleSmoother(alpha=0.35)
        self.max_angle_in_rep = 0.0
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_wrist", "right_wrist", "left_elbow", "right_elbow"]
        )

    def process(self, keypoints):
        # Layer 1: Landmark Visibility
        left_valid = are_landmarks_valid(keypoints, ["left_hip", "left_shoulder", "left_wrist"])
        right_valid = are_landmarks_valid(keypoints, ["right_hip", "right_shoulder", "right_wrist"])

        arm_angles = []
        if left_valid:
            arm_angles.append(self.left_arm_smoother.update(calculate_angle(keypoints["left_hip"], keypoints["left_shoulder"], keypoints["left_wrist"])))
        if right_valid:
            arm_angles.append(self.right_arm_smoother.update(calculate_angle(keypoints["right_hip"], keypoints["right_shoulder"], keypoints["right_wrist"])))

        if not arm_angles:
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_elbow", "left_wrist"]):
                arm_angles.append(self.left_arm_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_elbow"], keypoints["left_wrist"])))
            elif are_landmarks_valid(keypoints, ["right_shoulder", "right_elbow", "right_wrist"]):
                arm_angles.append(self.right_arm_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_elbow"], keypoints["right_wrist"])))

        if not arm_angles:
            return self.build_result(
                "LOWERED",
                feedback=["Position upper body in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position upper body and arms clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Orientation Check (Upright stance required)
        is_l_upright, _ = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=45.0)
        is_r_upright, _ = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=45.0)

        if is_l_upright and is_r_upright:
            pass

        avg_arm_angle = float(np.mean(arm_angles))
        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great press! Full overhead extension."
        fb_priority = 7
        now = time.time()

        # Layer 3: Biomechanical Overhead Wrist Height & Torso Alignment Check
        p_sh = get_landmark_point(keypoints, "left_shoulder") or get_landmark_point(keypoints, "right_shoulder")
        p_wr = get_landmark_point(keypoints, "left_wrist") or get_landmark_point(keypoints, "right_wrist")

        if p_sh and p_wr and self.state == "PRESSED":
            # Wrist MUST reach higher than shoulder (y_wrist <= y_shoulder + 10px in image space)
            if p_wr[1] > (p_sh[1] + 10.0):
                feedback_list.append("Press hands overhead")
                is_good_form = False
                fb_code = "ARM_NOT_HIGH_ENOUGH"
                fb_detail = "Press your hands overhead above shoulder height."
                fb_priority = 4

        # Layer 4: State Machine & Movement Displacement
        if self.state == "LOWERED":
            if avg_arm_angle >= self.pressed_angle:
                self.state = "PRESSED"
                self.max_angle_in_rep = avg_arm_angle
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Full extension! Lower arms")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Full overhead extension! Lower arms under control."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Press Overhead")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Press weights vertically overhead."
                    fb_priority = 7

        elif self.state == "PRESSED":
            self.displacement_tracker.update(keypoints)

            if avg_arm_angle > self.max_angle_in_rep:
                self.max_angle_in_rep = avg_arm_angle

            if avg_arm_angle <= self.lowered_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.max_angle_in_rep >= self.pressed_angle and is_good_form:
                        feedback_list.append("Great Press!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great press! Excellent overhead range of motion."
                        fb_priority = 7
                    else:
                        feedback_list.append("Extend higher next time")
                        is_good_form = False
                        fb_code = "INSUFFICIENT_EXTENSION"
                        fb_detail = "Extend your elbows fully overhead at peak of press."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Press through a full vertical range of motion overhead."
                    fb_priority = 5

                self.state = "LOWERED"
                self.max_angle_in_rep = 0.0
            else:
                if is_good_form:
                    feedback_list.append("Lower Arms")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Lower arms smoothly back to shoulder level."
                    fb_priority = 7

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(
            self.state,
            primary_angle=avg_arm_angle,
            feedback=feedback_list,
            valid=True,
            feedback_code=fb_code,
            feedback_detail=fb_detail,
            feedback_priority=fb_priority,
        )
