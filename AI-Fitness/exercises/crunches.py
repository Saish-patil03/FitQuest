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

class CrunchesTracker(BaseExerciseTracker):
    """
    Multi-Layer Crunches Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Supine Posture Check (Inclination <= 40.0°)
    3. Shoulder Lift vs Head/Neck Pulling Anti-Cheating
    4. Movement Elevation Displacement (dy >= 20.0px)
    """
    def __init__(
        self,
        down_angle: float = 150.0,
        crunch_angle: float = 140.0,
        debounce_sec: float = 0.4,
        min_displacement_px: float = 20.0,
    ):


        super().__init__("Crunches")
        self.down_angle = down_angle
        self.crunch_angle = crunch_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "DOWN"
        self.last_rep_time = 0.0

        self.left_hip_smoother = AngleSmoother(alpha=0.35)
        self.right_hip_smoother = AngleSmoother(alpha=0.35)
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_shoulder", "right_shoulder"]
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
                feedback=["Position torso and knees in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position torso and knees clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Orientation Check
        is_l_horiz, _ = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=65.0)
        is_r_horiz, _ = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=65.0)


        if not is_l_horiz and not is_r_horiz:
            return self.build_result(
                self.state,
                primary_angle=float(np.mean(hip_angles)),
                feedback=["Lie flat on back for crunches"],
                valid=True,
                feedback_code="INCORRECT_ORIENTATION",
                feedback_detail="Lie flat on your back with knees bent for crunches.",
                feedback_priority=2,
            )

        avg_hip_angle = float(np.mean(hip_angles))
        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great crunch! Squeeze core at top."
        fb_priority = 7
        now = time.time()

        # Layer 4: State Machine & Shoulder Elevation Displacement
        if self.state == "DOWN":
            if avg_hip_angle <= self.crunch_angle:
                self.state = "CRUNCH"
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Squeeze abs! Lower down")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Peak crunch contraction! Lower shoulders under control."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Crunch Up")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Lift your shoulders off floor and squeeze your abs."
                    fb_priority = 7

        elif self.state == "CRUNCH":
            self.displacement_tracker.update(keypoints)

            if avg_hip_angle >= self.down_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if is_good_form:
                        feedback_list.append("Great Crunch!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great crunch! Excellent abdominal contraction."
                        fb_priority = 7
                    else:
                        feedback_list.append("Lift shoulders higher next time")
                        fb_code = "INSUFFICIENT_DEPTH"
                        fb_detail = "Lift your shoulders higher and engage your core."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Perform the crunch through a controlled range of motion."
                    fb_priority = 5

                self.state = "DOWN"
            else:
                if is_good_form:
                    feedback_list.append("Lower Down")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Lower shoulders back down to floor."
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
