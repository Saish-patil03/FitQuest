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

class SideLungeTracker(BaseExerciseTracker):
    """
    Multi-Layer Side Lunge Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Upright Orientation
    3. Biomechanical Leg Separation Alignment (One leg bent, non-working leg straight)
    4. Lateral Hip Movement Displacement
    """
    def __init__(
        self,
        standing_angle: float = 155.0,
        lunge_angle: float = 115.0,
        debounce_sec: float = 0.4,
        min_displacement_px: float = 30.0,
    ):
        super().__init__("Side Lunges")
        self.standing_angle = standing_angle
        self.lunge_angle = lunge_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "STANDING"
        self.last_rep_time = 0.0

        self.knee_smoother = AngleSmoother(alpha=0.35)
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_hip", "right_hip", "left_knee", "right_knee"]
        )

    def process(self, keypoints):
        # Layer 1: Landmark Visibility
        left_valid = are_landmarks_valid(keypoints, ["left_hip", "left_knee", "left_ankle"])
        right_valid = are_landmarks_valid(keypoints, ["right_hip", "right_knee", "right_ankle"])

        knee_angles = []
        l_angle = None
        r_angle = None

        if left_valid:
            l_angle = calculate_angle(keypoints["left_hip"], keypoints["left_knee"], keypoints["left_ankle"])
            knee_angles.append(self.knee_smoother.update(l_angle))
        if right_valid:
            r_angle = calculate_angle(keypoints["right_hip"], keypoints["right_knee"], keypoints["right_ankle"])
            knee_angles.append(self.knee_smoother.update(r_angle))

        if not knee_angles:
            return self.build_result(
                "STANDING",
                feedback=["Position legs in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position your legs and lower body clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Orientation Check
        is_left_horiz, _ = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=45.0)
        is_right_horiz, _ = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=45.0)

        if is_left_horiz and is_right_horiz:
            return self.build_result(
                self.state,
                primary_angle=float(np.min(knee_angles)),
                feedback=["Stand upright for side lunges"],
                valid=True,
                feedback_code="INCORRECT_ORIENTATION",
                feedback_detail="Stand upright for side lunges.",
                feedback_priority=2,
            )

        min_knee_angle = float(np.min(knee_angles))
        max_knee_angle = float(np.max(knee_angles)) if len(knee_angles) > 1 else min_knee_angle

        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great side lunge! Drive back to center."
        fb_priority = 7
        now = time.time()

        # Layer 3: Biomechanical Alignment (In side lunge, non-working leg must remain straight)
        if len(knee_angles) == 2 and self.state == "SIDE_LUNGE":
            if max_knee_angle < 145.0:  # Both legs bending simultaneously = normal squat cheat
                feedback_list.append("Keep non-working leg straight")
                is_good_form = False
                fb_code = "JOINT_ALIGNMENT_ERROR"
                fb_detail = "Keep non-working leg straight while stepping sideways into lunge."
                fb_priority = 3

        # Layer 4: State Machine & Lateral Displacement
        if self.state == "STANDING":
            if min_knee_angle <= self.lunge_angle:
                self.state = "SIDE_LUNGE"
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Good side lunge! Push back center")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Good side lunge! Push back to center posture."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Step Sideways into Lunge")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Step wide sideways and sit back into your hip."
                    fb_priority = 7

        elif self.state == "SIDE_LUNGE":
            self.displacement_tracker.update(keypoints)

            if min_knee_angle >= self.standing_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if is_good_form:
                        feedback_list.append("Great Side Lunge!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great side lunge! Excellent lateral mobility."
                        fb_priority = 7
                    else:
                        feedback_list.append("Sit deeper into lunge next time")
                        fb_code = "INSUFFICIENT_DEPTH"
                        fb_detail = "Step wider and sit deeper into side lunge."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Step wider sideways")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Step wider sideways into the lunge."
                    fb_priority = 5

                self.state = "STANDING"
            else:
                if is_good_form:
                    feedback_list.append("Return Center")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Push off lead leg back to starting center stance."
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
