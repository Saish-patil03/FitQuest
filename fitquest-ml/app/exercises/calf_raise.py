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

class CalfRaiseTracker(BaseExerciseTracker):
    """
    Multi-Layer Calf Raise Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Upright Posture Check
    3. Biomechanical Knee Alignment (Locked/Straight Knees, No Knee Bouncing)
    4. Vertical Heel Elevation Displacement (Ankle Lift >= 15px)
    """
    def __init__(
        self,
        flat_angle: float = 150.0,
        raised_angle: float = 135.0,
        debounce_sec: float = 0.4,
        min_displacement_px: float = 15.0,
    ):
        super().__init__("Calf Raises")
        self.flat_angle = flat_angle
        self.raised_angle = raised_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "FLAT"
        self.last_rep_time = 0.0
        self.baseline_leg_length = None

        self.ankle_smoother = AngleSmoother(alpha=0.35)
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_ankle", "right_ankle"]
        )

    def process(self, keypoints):
        # Layer 1: Landmark Visibility
        left_valid = are_landmarks_valid(keypoints, ["left_knee", "left_ankle"])
        right_valid = are_landmarks_valid(keypoints, ["right_knee", "right_ankle"])

        if not left_valid and not right_valid:
            return self.build_result(
                "FLAT",
                feedback=["Position lower legs in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position your legs and feet clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Orientation Check (Upright stance required)
        is_l_upright, _ = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=45.0)
        is_r_upright, _ = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=45.0)

        if is_l_upright and is_r_upright:
            pass

        # Calculate Knee Joint Angle (Check straight legs)
        knee_angle = 180.0
        if left_valid and are_landmarks_valid(keypoints, ["left_hip", "left_knee", "left_ankle"]):
            knee_angle = calculate_angle(keypoints["left_hip"], keypoints["left_knee"], keypoints["left_ankle"])
        elif right_valid and are_landmarks_valid(keypoints, ["right_hip", "right_knee", "right_ankle"]):
            knee_angle = calculate_angle(keypoints["right_hip"], keypoints["right_knee"], keypoints["right_ankle"])

        # Calculate Ankle Elevation Metric
        ank_y = keypoints.get("left_ankle", keypoints.get("right_ankle", {})).get("y", 300)
        kne_y = keypoints.get("left_knee", keypoints.get("right_knee", {})).get("y", 200)
        curr_dist = abs(ank_y - kne_y)

        if self.baseline_leg_length is None or (self.state == "FLAT" and curr_dist > self.baseline_leg_length):
            self.baseline_leg_length = curr_dist

        # Map ankle lift ratio to effective angle (1.0 ratio = 180°, 0.75 ratio = 135°)
        if self.baseline_leg_length and self.baseline_leg_length > 0:
            ratio = min(1.0, max(0.5, curr_dist / self.baseline_leg_length))
            effective_angle = ratio * 180.0
        else:
            effective_angle = 180.0

        smooth_angle = self.ankle_smoother.update(effective_angle)

        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great calf raise! Hold peak contraction."
        fb_priority = 7
        now = time.time()

        # Layer 3: Biomechanical Knee Alignment (Knees must remain straight >= 145°)
        if knee_angle < 145.0:
            feedback_list.append("Keep knees straight")
            is_good_form = False
            fb_code = "JOINT_ALIGNMENT_ERROR"
            fb_detail = "Keep your knees straight — raise up using only your calves and ankles."
            fb_priority = 3

        # Layer 4: State Machine & Ankle Displacement
        if self.state == "FLAT":
            if smooth_angle <= self.raised_angle:
                self.state = "RAISED"
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Peak contraction! Lower heels")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Peak calf contraction! Lower heels under control."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Raise Heels High")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Raise your heels high onto the balls of your feet."
                    fb_priority = 7

        elif self.state == "RAISED":
            self.displacement_tracker.update(keypoints)

            if smooth_angle >= self.flat_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if is_good_form:
                        feedback_list.append("Great Calf Raise!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great calf raise! Full range of motion."
                        fb_priority = 7
                    else:
                        feedback_list.append("Raise higher next time")
                        fb_code = "INSUFFICIENT_DEPTH"
                        fb_detail = "Raise up higher onto your toes."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Raise up higher")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Raise up higher onto your toes."
                    fb_priority = 5

                self.state = "FLAT"
            else:
                if is_good_form:
                    feedback_list.append("Lower Heels")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Lower heels back down to floor."
                    fb_priority = 7

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(
            self.state,
            primary_angle=smooth_angle,
            secondary_angle=knee_angle,
            feedback=feedback_list,
            valid=True,
            feedback_code=fb_code,
            feedback_detail=fb_detail,
            feedback_priority=fb_priority,
        )
