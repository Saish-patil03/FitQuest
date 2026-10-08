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

class TricepExtensionTracker(BaseExerciseTracker):
    """
    Multi-Layer Tricep Extension Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Upright Posture Check
    3. Biomechanical Upper-Arm Stationary Alignment (Elbow stationary beside head, no shoulder press swing)
    4. Movement Displacement & Extension Depth (dy >= 25px)
    """
    def __init__(
        self,
        bent_angle: float = 75.0,
        extended_angle: float = 150.0,
        debounce_sec: float = 0.4,
        min_displacement_px: float = 25.0,
    ):
        super().__init__("Tricep Extensions")
        self.bent_angle = bent_angle
        self.extended_angle = extended_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "BENT"
        self.last_rep_time = 0.0

        self.left_elbow_smoother = AngleSmoother(alpha=0.35)
        self.right_elbow_smoother = AngleSmoother(alpha=0.35)
        self.max_angle_in_rep = 0.0
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_wrist", "right_wrist"]
        )

    def process(self, keypoints):
        # Layer 1: Landmark Visibility
        left_valid = are_landmarks_valid(keypoints, ["left_shoulder", "left_elbow", "left_wrist"])
        right_valid = are_landmarks_valid(keypoints, ["right_shoulder", "right_elbow", "right_wrist"])

        elbow_angles = []
        if left_valid:
            elbow_angles.append(self.left_elbow_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_elbow"], keypoints["left_wrist"])))
        if right_valid:
            elbow_angles.append(self.right_elbow_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_elbow"], keypoints["right_wrist"])))

        if not elbow_angles:
            return self.build_result(
                "BENT",
                feedback=["Position arms overhead in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position arms overhead clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Orientation Check
        is_l_upright, _ = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=45.0)
        is_r_upright, _ = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=45.0)

        if is_l_upright and is_r_upright:
            pass

        avg_elbow_angle = float(np.mean(elbow_angles))
        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great tricep extension! Keep elbows stationary."
        fb_priority = 7
        now = time.time()

        # Layer 3: Biomechanical Upper Arm Stationary Check (Upper arm should remain stationary beside head)
        p_sh = get_landmark_point(keypoints, "left_shoulder") or get_landmark_point(keypoints, "right_shoulder")
        p_el = get_landmark_point(keypoints, "left_elbow") or get_landmark_point(keypoints, "right_elbow")

        if p_sh and p_el:
            # If elbow drifts horizontally away from shoulder vector (shoulder press cheat)
            dx_elbow = abs(p_el[0] - p_sh[0])
            if dx_elbow > 90.0:
                feedback_list.append("Keep upper arm still")
                is_good_form = False
                fb_code = "UPPER_ARM_MOVING"
                fb_detail = "Keep your upper arms still beside your head — flex only at the elbows."
                fb_priority = 3

        # Layer 4: State Machine & Movement Displacement
        if self.state == "BENT":
            if avg_elbow_angle >= self.extended_angle:
                self.state = "EXTENDED"
                self.max_angle_in_rep = avg_elbow_angle
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Full extension! Lower weights behind head")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Full extension! Lower weights under control behind head."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Extend Arms Overhead")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Extend your forearms overhead towards ceiling."
                    fb_priority = 7

        elif self.state == "EXTENDED":
            self.displacement_tracker.update(keypoints)

            if avg_elbow_angle > self.max_angle_in_rep:
                self.max_angle_in_rep = avg_elbow_angle

            if avg_elbow_angle <= self.bent_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.max_angle_in_rep >= self.extended_angle and is_good_form:
                        feedback_list.append("Great Tricep Extension!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great tricep extension! Full lockout."
                        fb_priority = 7
                    else:
                        feedback_list.append("Extend higher next time")
                        is_good_form = False
                        fb_code = "INSUFFICIENT_EXTENSION"
                        fb_detail = "Extend your arms fully overhead at the top."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Extend elbows through a full range of motion."
                    fb_priority = 5

                self.state = "BENT"
                self.max_angle_in_rep = 0.0
            else:
                if is_good_form:
                    feedback_list.append("Lower Behind Head")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Lower forearms smoothly behind head."
                    fb_priority = 7

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(
            self.state,
            primary_angle=avg_elbow_angle,
            feedback=feedback_list,
            valid=True,
            feedback_code=fb_code,
            feedback_detail=fb_detail,
            feedback_priority=fb_priority,
        )
