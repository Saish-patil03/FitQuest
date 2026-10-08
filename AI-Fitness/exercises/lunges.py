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

class LungesTracker(BaseExerciseTracker):
    """
    Multi-Layer Lunges Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Upright Orientation
    3. Torso Alignment (Upright Spine, No Excessive Forward Leaning)
    4. Movement Displacement & Lunge Depth
    """
    def __init__(
        self,
        standing_angle: float = 155.0,
        lunge_angle: float = 105.0,
        debounce_sec: float = 0.4,
        min_displacement_px: float = 25.0,
    ):
        super().__init__("Lunges")
        self.standing_angle = standing_angle
        self.lunge_angle = lunge_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "STANDING"
        self.last_rep_time = 0.0

        self.left_knee_smoother = AngleSmoother(alpha=0.35)
        self.right_knee_smoother = AngleSmoother(alpha=0.35)
        self.min_knee_angle_in_rep = 180.0
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_hip", "right_hip", "left_knee", "right_knee"]
        )

    def process(self, keypoints):
        # Layer 1: Landmark Visibility
        left_valid = are_landmarks_valid(keypoints, ["left_hip", "left_knee", "left_ankle"])
        right_valid = are_landmarks_valid(keypoints, ["right_hip", "right_knee", "right_ankle"])

        knee_angles = []
        if left_valid:
            knee_angles.append(self.left_knee_smoother.update(calculate_angle(keypoints["left_hip"], keypoints["left_knee"], keypoints["left_ankle"])))
        if right_valid:
            knee_angles.append(self.right_knee_smoother.update(calculate_angle(keypoints["right_hip"], keypoints["right_knee"], keypoints["right_ankle"])))

        if not knee_angles:
            return self.build_result(
                "STANDING",
                feedback=["Position legs in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position your legs clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Orientation Check
        is_left_horiz, _ = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=45.0)
        is_right_horiz, _ = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=45.0)

        if is_left_horiz and is_right_horiz:
            return self.build_result(
                self.state,
                primary_angle=float(np.min(knee_angles)),
                feedback=["Stand upright for lunges"],
                valid=True,
                feedback_code="INCORRECT_ORIENTATION",
                feedback_detail="Stand upright to perform lunges.",
                feedback_priority=2,
            )

        min_knee_angle = float(np.min(knee_angles))
        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great lunge! Push up through your front heel."
        fb_priority = 7
        now = time.time()

        # Layer 3: Torso Alignment Check (Check forward torso lean)
        is_l_torso_horiz, torso_incline = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=65.0)
        if is_l_torso_horiz and torso_incline <= 35.0:
            feedback_list.append("Keep torso upright")
            is_good_form = False
            fb_code = "BACK_NOT_STRAIGHT"
            fb_detail = "Keep your torso upright — avoid leaning forward over your front knee."
            fb_priority = 3

        # Layer 4: State Machine & Movement Displacement
        if self.state == "STANDING":
            if min_knee_angle <= self.lunge_angle:
                self.state = "LUNGE"
                self.min_knee_angle_in_rep = min_knee_angle
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Good depth! Step back up")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Good lunge depth! Now step back up smoothly."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Step into Lunge")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Step forward into a controlled lunge."
                    fb_priority = 7

        elif self.state == "LUNGE":
            self.displacement_tracker.update(keypoints)

            if min_knee_angle < self.min_knee_angle_in_rep:
                self.min_knee_angle_in_rep = min_knee_angle

            if min_knee_angle >= self.standing_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.min_knee_angle_in_rep <= self.lunge_angle:
                        feedback_list.append("Great Lunge!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great lunge! Full range of motion."
                        fb_priority = 7
                    else:
                        feedback_list.append("Lunge lower next time")
                        is_good_form = False
                        fb_code = "INSUFFICIENT_DEPTH"
                        fb_detail = "Lunge deeper — drop your back knee towards the floor."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Step into a full lunge with clear vertical movement."
                    fb_priority = 5

                self.state = "STANDING"
                self.min_knee_angle_in_rep = 180.0
            else:
                if is_good_form:
                    feedback_list.append("Step back up")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Drive through your front heel back to standing posture."
                    fb_priority = 7

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(
            self.state,
            primary_angle=min_knee_angle,
            feedback=feedback_list,
            valid=True,
            feedback_code=fb_code,
            feedback_detail=fb_detail,
            feedback_priority=fb_priority,
        )
