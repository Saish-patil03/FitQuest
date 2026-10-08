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

class MountainClimbersTracker(BaseExerciseTracker):
    """
    Multi-Layer Mountain Climbers Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Horizontal Plank Orientation Check (Inclination <= 40.0°)
    3. Knee-to-Chest Drive & Alternating Leg Drive Anti-Cheating
    4. Movement Displacement & Sequence (PLANK -> DRIVE -> PLANK)
    """
    def __init__(
        self,
        plank_angle: float = 135.0,
        drive_angle: float = 90.0,
        debounce_sec: float = 0.3,
        min_displacement_px: float = 25.0,
    ):
        super().__init__("Mountain Climbers")
        self.plank_angle = plank_angle
        self.drive_angle = drive_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "PLANK"
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
                "PLANK",
                feedback=["Position body in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position body and key joints clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Horizontal Plank Orientation Check
        is_l_horiz, _ = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=40.0)
        is_r_horiz, _ = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=40.0)

        if not is_l_horiz and not is_r_horiz:
            return self.build_result(
                self.state,
                feedback=["Keep body horizontal for mountain climbers"],
                valid=True,
                feedback_code="BODY_NOT_HORIZONTAL",
                feedback_detail="Keep your body in a strong horizontal plank position.",
                feedback_priority=2,
            )

        l_hip_angle = calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])
        r_hip_angle = calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"])

        smooth_l = self.left_hip_smoother.update(l_hip_angle)
        smooth_r = self.right_hip_smoother.update(r_hip_angle)
        min_hip_angle = float(np.min([smooth_l, smooth_r]))

        active_leg = "LEFT" if smooth_l < smooth_r else "RIGHT"

        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great Mountain Climber! Explosive drive."
        fb_priority = 7
        now = time.time()

        # Layer 3: Hip Position & Leg Alternation Check
        sh_y = keypoints.get("left_shoulder", keypoints.get("right_shoulder", {})).get("y", 0)
        hip_y = keypoints.get("left_hip", keypoints.get("right_hip", {})).get("y", 0)

        if self.state == "DRIVE":
            # Hip piking check (hips raised > 45px above shoulder vector line)
            if hip_y < (sh_y - 45.0):
                feedback_list.append("Keep hips level")
                is_good_form = False
                fb_code = "HIP_POSITION_ERROR"
                fb_detail = "Keep your hips level — avoid piking or sagging."
                fb_priority = 3

            # Leg alternation check
            if self.last_active_leg == active_leg:
                feedback_list.append("Alternate legs")
                is_good_form = False
                fb_code = "ALTERNATION_ERROR"
                fb_detail = "Alternate your legs during each mountain climber."
                fb_priority = 3

        # Layer 4: State Machine & Movement Displacement
        if self.state == "PLANK":
            if min_hip_angle <= self.drive_angle:
                self.state = "DRIVE"
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Good knee drive!")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Knee driven toward chest! Extend leg back."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Drive Knee Forward")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Drive knee forward toward chest in plank."
                    fb_priority = 7

        elif self.state == "DRIVE":
            self.displacement_tracker.update(keypoints)

            if min_hip_angle >= self.plank_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now
                    self.last_active_leg = active_leg

                    if is_good_form:
                        feedback_list.append("Great Drive!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great mountain climber! Full leg extension."
                        fb_priority = 7
                    else:
                        feedback_list.append("Drive knee further next time")
                        fb_code = "KNEE_NOT_HIGH_ENOUGH"
                        fb_detail = "Drive your knee toward your chest."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Drive each knee through a full range of motion."
                    fb_priority = 5

                self.state = "PLANK"
            else:
                if is_good_form:
                    feedback_list.append("Extend Leg Back")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Extend leg back smoothly to plank position."
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
