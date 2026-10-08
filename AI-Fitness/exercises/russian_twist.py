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

class RussianTwistTracker(BaseExerciseTracker):
    """
    Multi-Layer Russian Twist Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Seated V-Sit Orientation Check
    3. Biomechanical Shoulder Rotation vs Hand-Only Movement Anti-Cheating
    4. Lateral Wrist Displacement across Body Midline (dx >= 40.0px)

    Note on 2D Camera Limitation:
    A single 2D webcam measures projected X/Y shoulder axis tilt & wrist lateral swing.
    True 3D Z-axis rotation is approximated via planar projection.
    """
    def __init__(
        self,
        twist_angle: float = 50.0,
        center_angle: float = 40.0,
        debounce_sec: float = 0.3,
        min_displacement_px: float = 40.0,
    ):


        super().__init__("Russian Twists")
        self.twist_angle = twist_angle
        self.center_angle = center_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "CENTER"
        self.last_rep_time = 0.0
        self.twist_smoother = AngleSmoother(alpha=0.35)
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_wrist", "right_wrist"]
        )

    def process(self, keypoints):
        # Layer 1: Landmark Visibility
        if not are_landmarks_valid(keypoints, ["left_shoulder", "right_shoulder"]):
            return self.build_result(
                "CENTER",
                feedback=["Position upper body in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position torso and arms clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Orientation Check (Seated V-sit posture check)
        is_l_horiz, l_incline = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=80.0)
        is_r_horiz, r_incline = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=80.0)

        # If lying completely flat (inclination <= 20°)
        if is_l_horiz and is_r_horiz and l_incline <= 20.0 and r_incline <= 20.0:
            return self.build_result(
                self.state,
                primary_angle=180.0,
                feedback=["Sit up in V-sit for twists"],
                valid=True,
                feedback_code="INCORRECT_ORIENTATION",
                feedback_detail="Sit in a V-sit posture on the floor for Russian twists.",
                feedback_priority=2,
            )

        # Measure shoulder/arm rotation angle relative to midline
        p_wr = get_landmark_point(keypoints, "right_wrist") or get_landmark_point(keypoints, "left_wrist") or get_landmark_point(keypoints, "right_shoulder")
        raw_twist = calculate_angle(keypoints["left_shoulder"], keypoints["right_shoulder"], p_wr)
        smooth_twist = self.twist_smoother.update(raw_twist)

        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great Russian twist! Controlled rotation."
        fb_priority = 7
        now = time.time()

        # Layer 3: Shoulder Rotation vs Hand-Only Movement Check
        p_sh_l = get_landmark_point(keypoints, "left_shoulder")
        p_sh_r = get_landmark_point(keypoints, "right_shoulder")
        if p_sh_l and p_sh_r and self.state == "TWIST":
            shoulder_tilt = abs(p_sh_l[1] - p_sh_r[1])
            # If shoulders remain completely flat while hands move (hand-only cheat)
            if shoulder_tilt < 5.0 and abs(smooth_twist - self.twist_angle) > 30.0:
                feedback_list.append("Rotate torso and shoulders")
                is_good_form = False
                fb_code = "TORSO_ROTATION_INSUFFICIENT"
                fb_detail = "Rotate your torso and shoulders — don't move only your hands."
                fb_priority = 3

        # Layer 4: State Machine & Lateral Displacement
        if self.state == "CENTER":
            if smooth_twist <= self.twist_angle:
                self.state = "TWIST"
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Twist complete! Return center")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Torso twisted! Return back through center posture."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Twist Torso")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Rotate torso and shoulders side to side."
                    fb_priority = 7

        elif self.state == "TWIST":
            self.displacement_tracker.update(keypoints)

            if smooth_twist >= self.center_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if is_good_form:
                        feedback_list.append("Great Twist!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great Russian twist! Excellent oblique rotation."
                        fb_priority = 7
                    else:
                        feedback_list.append("Rotate further next time")
                        fb_code = "TORSO_ROTATION_INSUFFICIENT"
                        fb_detail = "Rotate your torso through a full range of motion."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full rotation required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Twist your torso fully from side to side."
                    fb_priority = 5

                self.state = "CENTER"

                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if is_good_form:
                        feedback_list.append("Great Twist!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great Russian twist! Excellent oblique rotation."
                        fb_priority = 7
                    else:
                        feedback_list.append("Rotate further next time")
                        fb_code = "TORSO_ROTATION_INSUFFICIENT"
                        fb_detail = "Rotate your torso through a full range of motion."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full rotation required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Twist your torso fully from side to side."
                    fb_priority = 5

                self.state = "CENTER"
            else:
                if is_good_form:
                    feedback_list.append("Return Center")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Return torso back through center position."
                    fb_priority = 7

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(
            self.state,
            primary_angle=smooth_twist,
            feedback=feedback_list,
            valid=True,
            feedback_code=fb_code,
            feedback_detail=fb_detail,
            feedback_priority=fb_priority,
        )
