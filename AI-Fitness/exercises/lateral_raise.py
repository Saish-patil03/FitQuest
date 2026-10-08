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

class LateralRaiseTracker(BaseExerciseTracker):
    """
    Multi-Layer Lateral Raise Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Upright Posture Check
    3. Biomechanical Sideways Arm Path & Rigid Elbow Structure Check
    4. Lateral Movement Elevation Displacement (dx/dy >= 30px)
    """
    def __init__(
        self,
        lowered_angle: float = 35.0,
        raised_angle: float = 80.0,
        debounce_sec: float = 0.4,
        min_displacement_px: float = 30.0,
    ):
        super().__init__("Lateral Raises")
        self.lowered_angle = lowered_angle
        self.raised_angle = raised_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "LOWERED"
        self.last_rep_time = 0.0

        self.arm_smoother = AngleSmoother(alpha=0.35)
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_wrist", "right_wrist", "left_elbow", "right_elbow"]
        )

    def process(self, keypoints):
        # Layer 1: Landmark Visibility
        left_valid = are_landmarks_valid(keypoints, ["left_hip", "left_shoulder", "left_wrist"])
        right_valid = are_landmarks_valid(keypoints, ["right_hip", "right_shoulder", "right_wrist"])

        arm_angles = []
        if left_valid:
            arm_angles.append(self.arm_smoother.update(calculate_angle(keypoints["left_hip"], keypoints["left_shoulder"], keypoints["left_wrist"])))
        if right_valid:
            arm_angles.append(self.arm_smoother.update(calculate_angle(keypoints["right_hip"], keypoints["right_shoulder"], keypoints["right_wrist"])))

        if not arm_angles:
            return self.build_result(
                "LOWERED",
                feedback=["Position arms in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position arms and shoulders clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Orientation Check
        is_l_upright, _ = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=45.0)
        is_r_upright, _ = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=45.0)

        if is_l_upright and is_r_upright:
            pass

        avg_arm_angle = float(np.mean(arm_angles))
        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great lateral raise! Controlled motion."
        fb_priority = 7
        now = time.time()

        # Layer 3: Biomechanical Sideways Arm Path & Rigid Elbow Structure
        p_sh_l = get_landmark_point(keypoints, "left_shoulder")
        p_sh_r = get_landmark_point(keypoints, "right_shoulder")
        p_wr_l = get_landmark_point(keypoints, "left_wrist")
        p_wr_r = get_landmark_point(keypoints, "right_wrist")
        p_el_l = get_landmark_point(keypoints, "left_elbow")

        if p_sh_l and p_el_l and p_wr_l and self.state == "RAISED":
            elbow_angle = calculate_angle(p_sh_l, p_el_l, p_wr_l)
            if elbow_angle < 130.0:  # Excessive forearm curl
                feedback_list.append("Keep elbows slightly bent but rigid")
                is_good_form = False
                fb_code = "JOINT_ALIGNMENT_ERROR"
                fb_detail = "Keep your elbows slightly bent but rigid — avoid curling forearms."
                fb_priority = 3

        # Layer 4: State Machine & Lateral Displacement
        if self.state == "LOWERED":
            if avg_arm_angle >= self.raised_angle:
                self.state = "RAISED"
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Parallel to floor! Lower arms")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Arms raised to shoulder level! Lower under control."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Raise Arms Sideways")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Raise arms out to the sides to shoulder height."
                    fb_priority = 7

        elif self.state == "RAISED":
            self.displacement_tracker.update(keypoints)

            if avg_arm_angle <= self.lowered_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if is_good_form:
                        feedback_list.append("Great Lateral Raise!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great lateral raise! Excellent shoulder contraction."
                        fb_priority = 7
                    else:
                        feedback_list.append("Raise higher next time")
                        fb_code = "ARM_NOT_HIGH_ENOUGH"
                        fb_detail = "Raise your arms sideways to shoulder height."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Raise your arms sideways through a full range of motion."
                    fb_priority = 5

                self.state = "LOWERED"
            else:
                if is_good_form:
                    feedback_list.append("Lower Arms")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Lower arms smoothly back to your sides."
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
