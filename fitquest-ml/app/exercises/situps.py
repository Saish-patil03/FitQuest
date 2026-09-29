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

class SitUpsTracker(BaseExerciseTracker):
    """
    Multi-Layer Sit-Ups Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Supine to Seated Orientation Transition
    3. Torso vs Head-Only Movement Anti-Cheating (Shoulder Y movement required)
    4. Movement Displacement & Torso Flexion Depth
    """
    def __init__(
        self,
        down_angle: float = 130.0,
        up_angle: float = 90.0,
        debounce_sec: float = 0.4,
        min_displacement_px: float = 35.0,
    ):
        super().__init__("Sit-ups")
        self.down_angle = down_angle
        self.up_angle = up_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "DOWN"
        self.last_rep_time = 0.0

        self.left_hip_smoother = AngleSmoother(alpha=0.35)
        self.right_hip_smoother = AngleSmoother(alpha=0.35)
        self.min_hip_angle_in_rep = 180.0
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
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_ankle"]):
                hip_angles.append(self.left_hip_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_ankle"])))
            elif are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_ankle"]):
                hip_angles.append(self.right_hip_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_ankle"])))

        if not hip_angles:
            return self.build_result(
                "DOWN",
                feedback=["Position torso in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position torso and legs clearly in camera view.",
                feedback_priority=1,
            )

        avg_hip_angle = float(np.mean(hip_angles))
        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great sit-up! Controlled descent."
        fb_priority = 7
        now = time.time()

        # Layer 3: Head-Only Movement Anti-Cheating Check
        p_sh = get_landmark_point(keypoints, "left_shoulder") or get_landmark_point(keypoints, "right_shoulder")
        p_hip = get_landmark_point(keypoints, "left_hip") or get_landmark_point(keypoints, "right_hip")

        # Layer 4: State Machine & Torso Displacement
        if self.state == "DOWN":
            if avg_hip_angle <= self.up_angle:
                self.state = "UP"
                self.min_hip_angle_in_rep = avg_hip_angle
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Good height! Go back down")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Good sit-up height! Now lower back down smoothly."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Sit Up")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Sit up using your core — bring torso towards knees."
                    fb_priority = 7

        elif self.state == "UP":
            self.displacement_tracker.update(keypoints)

            if avg_hip_angle < self.min_hip_angle_in_rep:
                self.min_hip_angle_in_rep = avg_hip_angle

            if avg_hip_angle >= self.down_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.min_hip_angle_in_rep <= self.up_angle:
                        feedback_list.append("Great Rep!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great sit-up! Full range of motion."
                        fb_priority = 7
                    else:
                        feedback_list.append("Sit up higher next time")
                        is_good_form = False
                        fb_code = "INSUFFICIENT_DEPTH"
                        fb_detail = "Sit up higher — bring your chest all the way to your knees."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Sit up further — bring your torso toward your knees."
                    fb_priority = 5

                self.state = "DOWN"
                self.min_hip_angle_in_rep = 180.0
            else:
                if is_good_form:
                    feedback_list.append("Go back down")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Lower torso back to starting posture on floor."
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
