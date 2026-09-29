import time
import numpy as np
from utils import (
    calculate_angle,
    AngleSmoother,
    BaseExerciseTracker,
    are_landmarks_valid,
    check_body_orientation,
    check_joint_alignment,
    MovementDisplacementTracker,
)

class SquatTracker(BaseExerciseTracker):
    """
    Multi-Layer Squat Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Upright Orientation (Inclination > 45.0°)
    3. Biomechanical Spine & Knee Alignment
    4. Physical Hip Vertical Displacement & Squat Depth
    """
    def __init__(
        self,
        standing_angle: float = 150.0,
        squat_angle: float = 110.0,
        debounce_sec: float = 0.4,
        min_displacement_px: float = 35.0,
    ):
        super().__init__("Squat")
        self.standing_angle = standing_angle
        self.squat_angle = squat_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "STANDING"
        self.last_rep_time = 0.0

        self.left_knee_smoother = AngleSmoother(alpha=0.35)
        self.right_knee_smoother = AngleSmoother(alpha=0.35)
        self.torso_smoother = AngleSmoother(alpha=0.35)

        self.min_knee_angle_in_rep = 180.0
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_hip", "right_hip", "left_knee", "right_knee"]
        )

    def process(self, keypoints):
        # ----------------------------------------------------
        # LAYER 1: Landmark / Pose Validity
        # ----------------------------------------------------
        left_valid = are_landmarks_valid(keypoints, ["left_hip", "left_knee", "left_ankle"])
        right_valid = are_landmarks_valid(keypoints, ["right_hip", "right_knee", "right_ankle"])

        knee_angles = []
        if left_valid:
            raw_l = calculate_angle(keypoints["left_hip"], keypoints["left_knee"], keypoints["left_ankle"])
            knee_angles.append(self.left_knee_smoother.update(raw_l))
        if right_valid:
            raw_r = calculate_angle(keypoints["right_hip"], keypoints["right_knee"], keypoints["right_ankle"])
            knee_angles.append(self.right_knee_smoother.update(raw_r))

        if not knee_angles:
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"]):
                knee_angles.append(self.left_knee_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])))
            elif are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"]):
                knee_angles.append(self.right_knee_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"])))

        if not knee_angles:
            return self.build_result(
                "STANDING",
                feedback=["Position legs in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position your legs and lower body clearly in camera view.",
                feedback_priority=1,
            )

        # ----------------------------------------------------
        # LAYER 2: Spatial Body Orientation Validity
        # ----------------------------------------------------
        is_left_upright, l_incline = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=45.0)
        is_right_upright, r_incline = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=45.0)

        # Standing posture requires torso inclination > 45° (i.e. NOT horizontal)
        if is_left_upright and is_right_upright and l_incline <= 35.0 and r_incline <= 35.0:
            return self.build_result(
                self.state,
                primary_angle=float(np.mean(knee_angles)),
                feedback=["Stand upright for squats"],
                valid=True,
                feedback_code="INCORRECT_ORIENTATION",
                feedback_detail="Stand upright facing or profile to camera for squats.",
                feedback_priority=2,
            )

        avg_knee_angle = float(np.mean(knee_angles))

        # ----------------------------------------------------
        # LAYER 3: Biomechanical Alignment Checks
        # ----------------------------------------------------
        is_back_straight = True
        torso_angle = None
        if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"]):
            is_back_straight, torso_angle = check_joint_alignment(keypoints, "left_shoulder", "left_hip", "left_knee", min_angle=135.0)
        elif are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"]):
            is_back_straight, torso_angle = check_joint_alignment(keypoints, "right_shoulder", "right_hip", "right_knee", min_angle=135.0)

        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great squat depth! Drive up through your heels."
        fb_priority = 7

        if not is_back_straight and torso_angle is not None and torso_angle < 135.0:
            feedback_list.append("Keep back straight")
            is_good_form = False
            fb_code = "BACK_NOT_STRAIGHT"
            fb_detail = "Keep your back straight and chest lifted during squats."
            fb_priority = 3

        # ----------------------------------------------------
        # LAYER 4: State Machine & Movement Displacement
        # ----------------------------------------------------
        now = time.time()

        if self.state == "STANDING":
            if avg_knee_angle <= self.squat_angle:
                self.state = "SQUAT"
                self.min_knee_angle_in_rep = avg_knee_angle
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Good squat depth! Stand up")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Good squat depth! Now drive up through your heels."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Squat Down")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Lower your hips down and back like sitting in a chair."
                    fb_priority = 7

        elif self.state == "SQUAT":
            self.displacement_tracker.update(keypoints)

            if avg_knee_angle < self.min_knee_angle_in_rep:
                self.min_knee_angle_in_rep = avg_knee_angle

            if avg_knee_angle >= self.standing_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.min_knee_angle_in_rep <= self.squat_angle:
                        feedback_list.append("Great Rep!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great repetition! Excellent squat depth and posture."
                        fb_priority = 7
                    else:
                        feedback_list.append("Squat deeper next time")
                        is_good_form = False
                        fb_code = "INSUFFICIENT_DEPTH"
                        fb_detail = "Squat deeper — lower your hips until thighs are parallel to floor."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Lower your hips through a full vertical range of motion."
                    fb_priority = 5

                self.state = "STANDING"
                self.min_knee_angle_in_rep = 180.0
            else:
                if is_good_form:
                    feedback_list.append("Stand Up!")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Stand back up smoothly to starting position."
                    fb_priority = 7

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(
            self.state,
            primary_angle=avg_knee_angle,
            secondary_angle=torso_angle,
            feedback=feedback_list,
            valid=True,
            feedback_code=fb_code,
            feedback_detail=fb_detail,
            feedback_priority=fb_priority,
        )
