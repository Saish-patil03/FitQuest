import time
import numpy as np
from utils import (
    calculate_angle,
    calculate_distance,
    AngleSmoother,
    BaseExerciseTracker,
    are_landmarks_valid,
    get_landmark_point,
    check_body_orientation,
    MovementDisplacementTracker,
)

class JumpingJacksTracker(BaseExerciseTracker):
    """
    Multi-Layer Jumping Jacks Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence (Full body required)
    2. Spatial Upright Posture Check
    3. Coordinated Overhead Arm Elevation & Normalized Leg Separation Anti-Cheating
    4. Movement Displacement & Closed-Open-Closed Cycle Validation
    """
    def __init__(
        self,
        closed_angle: float = 60.0,
        open_angle: float = 135.0,
        debounce_sec: float = 0.3,
        min_displacement_px: float = 30.0,
    ):
        super().__init__("Jumping Jacks")
        self.closed_angle = closed_angle
        self.open_angle = open_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "CLOSED"
        self.last_rep_time = 0.0

        self.left_arm_smoother = AngleSmoother(alpha=0.35)
        self.right_arm_smoother = AngleSmoother(alpha=0.35)
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_wrist", "right_wrist", "left_ankle", "right_ankle"]
        )

    def process(self, keypoints):
        # Layer 1: Landmark Visibility (Requires full body)
        required = ["left_shoulder", "right_shoulder", "left_wrist", "right_wrist", "left_ankle", "right_ankle"]
        if not are_landmarks_valid(keypoints, required):
            return self.build_result(
                "CLOSED",
                feedback=["Position full body in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position full body, arms, and legs clearly in view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Upright Posture Check
        is_l_horiz, _ = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=40.0)
        is_r_horiz, _ = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=40.0)

        if is_l_horiz and is_r_horiz:
            return self.build_result(
                self.state,
                feedback=["Stand upright for jumping jacks"],
                valid=True,
                feedback_code="INCORRECT_ORIENTATION",
                feedback_detail="Stand upright to perform jumping jacks.",
                feedback_priority=2,
            )


        left_arm = calculate_angle(keypoints["left_hip"], keypoints["left_shoulder"], keypoints["left_wrist"])
        right_arm = calculate_angle(keypoints["right_hip"], keypoints["right_shoulder"], keypoints["right_wrist"])
        avg_arm_angle = float(np.mean([self.left_arm_smoother.update(left_arm), self.right_arm_smoother.update(right_arm)]))

        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great Jack! Controlled jump."
        fb_priority = 7
        now = time.time()

        # Layer 3: Coordinated Arm Elevation & Normalized Leg Separation Check
        p_sh_l = get_landmark_point(keypoints, "left_shoulder")
        p_sh_r = get_landmark_point(keypoints, "right_shoulder")
        p_ank_l = get_landmark_point(keypoints, "left_ankle")
        p_ank_r = get_landmark_point(keypoints, "right_ankle")

        dx_shoulders = abs(p_sh_l[0] - p_sh_r[0]) if p_sh_l and p_sh_r else 100.0
        dx_ankles = abs(p_ank_l[0] - p_ank_r[0]) if p_ank_l and p_ank_r else 0.0
        leg_separation_ratio = dx_ankles / max(dx_shoulders, 1.0)

        has_arms_up = (avg_arm_angle >= self.open_angle)
        has_legs_separated = (leg_separation_ratio >= 1.2)

        if self.state == "OPEN":
            if not has_arms_up and has_legs_separated:
                feedback_list.append("Raise arms higher")
                is_good_form = False
                fb_code = "ARM_NOT_HIGH_ENOUGH"
                fb_detail = "Raise your arms higher during the jumping jack."
                fb_priority = 4
            elif has_arms_up and not has_legs_separated:
                feedback_list.append("Spread feet wider")
                is_good_form = False
                fb_code = "LEGS_NOT_SEPARATED"
                fb_detail = "Spread your feet wider during the jump."
                fb_priority = 4

        # Layer 4: State Machine & Movement Displacement
        if self.state == "CLOSED":
            if has_arms_up and has_legs_separated:
                self.state = "OPEN"
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Open! Jump back in")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Arms and legs opened! Now jump back feet together."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Jump Out")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Jump feet apart and raise arms overhead."
                    fb_priority = 7

        elif self.state == "OPEN":
            self.displacement_tracker.update(keypoints)

            if avg_arm_angle <= self.closed_angle and leg_separation_ratio <= 1.0:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if is_good_form:
                        feedback_list.append("Great Jack!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great Jack! Excellent arm elevation and leg jump."
                        fb_priority = 7
                    else:
                        feedback_list.append("Full jump required next time")
                        fb_code = "JUMPING_JACK_INCOMPLETE"
                        fb_detail = "Open both your arms and legs fully before returning."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Use a full range of motion."
                    fb_priority = 5

                self.state = "CLOSED"
            else:
                if is_good_form:
                    feedback_list.append("Jump In")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Jump feet back together and lower arms to sides."
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
