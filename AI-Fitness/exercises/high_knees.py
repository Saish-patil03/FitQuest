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

class HighKneesTracker(BaseExerciseTracker):
    """
    Multi-Layer High Knees Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Upright Posture & Torso Stability Check (Inclination <= 35.0°)
    3. Knee Height Elevation (Knee y <= Hip y + 35px) & Alternating Leg Anti-Cheating
    4. Movement Displacement & Repetition Sequence
    """
    def __init__(
        self,
        down_angle: float = 130.0,
        high_knee_angle: float = 95.0,
        debounce_sec: float = 0.3,
        min_displacement_px: float = 25.0,
    ):
        super().__init__("High Knees")
        self.down_angle = down_angle
        self.high_knee_angle = high_knee_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "DOWN"
        self.last_rep_time = 0.0
        self.last_active_leg = None  # Tracks "LEFT" vs "RIGHT"

        self.left_hip_smoother = AngleSmoother(alpha=0.35)
        self.right_hip_smoother = AngleSmoother(alpha=0.35)
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_knee", "right_knee"]
        )

    def process(self, keypoints):
        # Layer 1: Landmark Visibility
        required = ["left_shoulder", "right_shoulder", "left_hip", "right_hip", "left_knee", "right_knee"]
        if not are_landmarks_valid(keypoints, required):
            return self.build_result(
                "DOWN",
                feedback=["Position torso and legs in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position torso and legs clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Upright Posture & Torso Stability Check
        is_l_horiz, l_incline = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=40.0)
        is_r_horiz, r_incline = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=40.0)

        if is_l_horiz and is_r_horiz:
            return self.build_result(
                self.state,
                feedback=["Stand upright for high knees"],
                valid=True,
                feedback_code="INCORRECT_ORIENTATION",
                feedback_detail="Stand upright to perform high knees.",
                feedback_priority=2,
            )

        if l_incline < 60.0 or r_incline < 60.0:  # Excessive torso inclination while standing
            return self.build_result(
                self.state,
                feedback=["Keep torso upright"],
                valid=True,
                feedback_code="TORSO_LEANING",
                feedback_detail="Keep your torso upright and avoid using momentum.",
                feedback_priority=3,
            )


        l_hip_angle = calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])
        r_hip_angle = calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"])

        smooth_l = self.left_hip_smoother.update(l_hip_angle)
        smooth_r = self.right_hip_smoother.update(r_hip_angle)
        min_hip_angle = float(np.min([smooth_l, smooth_r]))

        # Identify active leg
        active_leg = "LEFT" if smooth_l < smooth_r else "RIGHT"

        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great High Knee! High drive."
        fb_priority = 7
        now = time.time()

        # Layer 3: Knee Elevation & Alternation Check
        p_hip = get_landmark_point(keypoints, f"{active_leg.lower()}_hip")
        p_knee = get_landmark_point(keypoints, f"{active_leg.lower()}_knee")

        if p_hip and p_knee and self.state == "HIGH_KNEE":
            # Knee height check: Knee must rise to hip height level
            if p_knee[1] > (p_hip[1] + 35.0):
                feedback_list.append("Drive knee higher")
                is_good_form = False
                fb_code = "KNEE_NOT_HIGH_ENOUGH"
                fb_detail = "Drive your knee higher toward your hip."
                fb_priority = 4

            # Alternation check: Must alternate left and right legs
            if self.last_active_leg == active_leg:
                feedback_list.append("Alternate knees")
                is_good_form = False
                fb_code = "ALTERNATION_ERROR"
                fb_detail = "Alternate your knees — left, then right."
                fb_priority = 3

        # Layer 4: State Machine & Movement Displacement
        if self.state == "DOWN":
            if min_hip_angle <= self.high_knee_angle:
                self.state = "HIGH_KNEE"
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("High knee reached!")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Peak knee drive reached! Drive down and switch."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Drive Knee High")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Drive your knee high toward hip height."
                    fb_priority = 7

        elif self.state == "HIGH_KNEE":
            self.displacement_tracker.update(keypoints)

            if min_hip_angle >= self.down_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now
                    self.last_active_leg = active_leg

                    if is_good_form:
                        feedback_list.append("Great Knee Drive!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great knee drive! Fast explosion."
                        fb_priority = 7
                    else:
                        feedback_list.append("Drive higher next time")
                        fb_code = "KNEE_NOT_HIGH_ENOUGH"
                        fb_detail = "Drive your knee higher toward your hip."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Lift your knees through a full range of motion."
                    fb_priority = 5

                self.state = "DOWN"
            else:
                if is_good_form:
                    feedback_list.append("Lower Knee")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Lower knee under control."
                    fb_priority = 7

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(
            self.state,
            primary_angle=min_hip_angle,
            feedback=feedback_list,
            valid=True,
            feedback_code=fb_code,
            feedback_detail=fb_detail,
            feedback_priority=fb_priority,
        )
