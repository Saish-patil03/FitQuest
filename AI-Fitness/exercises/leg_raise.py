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

class LegRaisesTracker(BaseExerciseTracker):
    """
    Multi-Layer Leg Raises Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Supine Posture Check
    3. Biomechanical Knee Extension Alignment (Straight legs Hip-Knee-Ankle >= 140.0°, no knee tucking)
    4. Physical Ankle Elevation Displacement (dy >= 40.0px)
    """
    def __init__(
        self,
        down_angle: float = 145.0,
        raised_angle: float = 110.0,
        debounce_sec: float = 0.4,
        min_displacement_px: float = 40.0,
    ):
        super().__init__("Leg Raises")
        self.down_angle = down_angle
        self.raised_angle = raised_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "DOWN"
        self.last_rep_time = 0.0

        self.left_hip_smoother = AngleSmoother(alpha=0.35)
        self.right_hip_smoother = AngleSmoother(alpha=0.35)
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_ankle", "right_ankle"]
        )

    def process(self, keypoints):
        # Layer 1: Landmark Visibility
        left_valid = are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_ankle"])
        right_valid = are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_ankle"])

        hip_angles = []
        if left_valid:
            hip_angles.append(self.left_hip_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_ankle"])))
        if right_valid:
            hip_angles.append(self.right_hip_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_ankle"])))

        if not hip_angles:
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"]):
                hip_angles.append(self.left_hip_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])))
            elif are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"]):
                hip_angles.append(self.right_hip_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"])))

        if not hip_angles:
            return self.build_result(
                "DOWN",
                feedback=["Position legs in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position legs and hips clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Orientation Check
        is_l_horiz, _ = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=40.0)
        is_r_horiz, _ = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=40.0)

        if not is_l_horiz and not is_r_horiz:
            return self.build_result(
                self.state,
                primary_angle=float(np.mean(hip_angles)),
                feedback=["Lie flat on back for leg raises"],
                valid=True,
                feedback_code="INCORRECT_ORIENTATION",
                feedback_detail="Lie flat on your back for leg raises.",
                feedback_priority=2,
            )

        avg_hip_angle = float(np.mean(hip_angles))
        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great leg raise! Controlled lower."
        fb_priority = 7
        now = time.time()

        # Layer 3: Biomechanical Knee Extension Check (Straight legs required)
        p_hip = get_landmark_point(keypoints, "left_hip") or get_landmark_point(keypoints, "right_hip")
        p_kne = get_landmark_point(keypoints, "left_knee") or get_landmark_point(keypoints, "right_knee")
        p_ank = get_landmark_point(keypoints, "left_ankle") or get_landmark_point(keypoints, "right_ankle")

        if p_hip and p_kne and p_ank and self.state == "RAISED":
            knee_angle = calculate_angle(p_hip, p_kne, p_ank)
            if knee_angle < 135.0:  # Knee bending cheat
                feedback_list.append("Keep legs straight")
                is_good_form = False
                fb_code = "INSUFFICIENT_EXTENSION"
                fb_detail = "Keep your legs straight throughout the movement — don't bend knees."
                fb_priority = 3

        # Layer 4: State Machine & Ankle Displacement
        if self.state == "DOWN":
            if avg_hip_angle <= self.raised_angle:
                self.state = "RAISED"
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Legs raised! Lower under control")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Legs raised! Lower under control back towards floor."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Raise Legs")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Raise straight legs vertically toward ceiling."
                    fb_priority = 7

        elif self.state == "RAISED":
            self.displacement_tracker.update(keypoints)

            if avg_hip_angle >= self.down_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if is_good_form:
                        feedback_list.append("Great Leg Raise!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great leg raise! Full lower abdominal engagement."
                        fb_priority = 7
                    else:
                        feedback_list.append("Raise legs higher next time")
                        fb_code = "INSUFFICIENT_DEPTH"
                        fb_detail = "Raise your legs higher toward vertical."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Use a full controlled leg raise."
                    fb_priority = 5

                self.state = "DOWN"
            else:
                if is_good_form:
                    feedback_list.append("Lower Legs")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Lower legs under control back down."
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
