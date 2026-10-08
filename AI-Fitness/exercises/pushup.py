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

class PushUpTracker(BaseExerciseTracker):
    """
    Multi-Layer Push-Up Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Validity
    2. Spatial Body Orientation (Torso Inclination <= max_inclination_deg)
    3. Biomechanical Alignment & Range of Motion
    4. Movement Displacement
    """
    def __init__(
        self,
        up_angle: float = 150.0,
        down_angle: float = 110.0,
        debounce_sec: float = 0.4,
        max_inclination_deg: float = 45.0,
        min_displacement_px: float = 5.0,
    ):
        super().__init__("Push-up")
        self.up_angle = up_angle
        self.down_angle = down_angle
        self.debounce_sec = debounce_sec
        self.max_inclination_deg = max_inclination_deg
        self.min_displacement_px = min_displacement_px

        self.state = "UP"
        self.last_rep_time = 0.0

        self.left_elbow_smoother = AngleSmoother(alpha=0.35)
        self.right_elbow_smoother = AngleSmoother(alpha=0.35)
        self.body_line_smoother = AngleSmoother(alpha=0.35)

        self.min_elbow_angle_in_rep = 180.0
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"]
        )

    def process(self, keypoints):
        # ----------------------------------------------------
        # LAYER 1: Landmark / Pose Validity
        # ----------------------------------------------------
        left_valid = are_landmarks_valid(keypoints, ["left_shoulder", "left_elbow", "left_wrist"])
        right_valid = are_landmarks_valid(keypoints, ["right_shoulder", "right_elbow", "right_wrist"])

        elbow_angles = []
        if left_valid:
            raw_l = calculate_angle(keypoints["left_shoulder"], keypoints["left_elbow"], keypoints["left_wrist"])
            elbow_angles.append(self.left_elbow_smoother.update(raw_l))
        if right_valid:
            raw_r = calculate_angle(keypoints["right_shoulder"], keypoints["right_elbow"], keypoints["right_wrist"])
            elbow_angles.append(self.right_elbow_smoother.update(raw_r))

        if not elbow_angles:
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_elbow", "left_hip"]):
                elbow_angles.append(self.left_elbow_smoother.update(calculate_angle(keypoints["left_hip"], keypoints["left_shoulder"], keypoints["left_elbow"])))
            elif are_landmarks_valid(keypoints, ["right_shoulder", "right_elbow", "right_hip"]):
                elbow_angles.append(self.right_elbow_smoother.update(calculate_angle(keypoints["right_hip"], keypoints["right_shoulder"], keypoints["right_elbow"])))

        if not elbow_angles:
            return self.build_result(
                "UP",
                feedback=["Position upper body and arms in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position your upper body and arms clearly in camera view.",
                feedback_priority=1,
            )

        # ----------------------------------------------------
        # LAYER 2: Spatial Body Orientation Validity
        # ----------------------------------------------------
        is_left_horiz, _ = check_body_orientation(keypoints, "left_shoulder", "left_hip", self.max_inclination_deg)
        is_right_horiz, _ = check_body_orientation(keypoints, "right_shoulder", "right_hip", self.max_inclination_deg)

        is_horizontal_posture = is_left_horiz or is_right_horiz
        if not is_left_horiz and not is_right_horiz:
            is_l_knee_horiz, _ = check_body_orientation(keypoints, "left_shoulder", "left_knee", self.max_inclination_deg)
            is_r_knee_horiz, _ = check_body_orientation(keypoints, "right_shoulder", "right_knee", self.max_inclination_deg)
            is_horizontal_posture = is_l_knee_horiz or is_r_knee_horiz

        # Frontal / Diagonal Perspective Fallback:
        # When viewed from front or 3/4 angle, perspective foreshortens the torso in 2D.
        # If wrists are below shoulders (hands on ground), treat as a valid horizontal posture.
        if not is_horizontal_posture:
            left_arm_down = left_valid and (keypoints["left_wrist"][1] >= keypoints["left_shoulder"][1] - 15)
            right_arm_down = right_valid and (keypoints["right_wrist"][1] >= keypoints["right_shoulder"][1] - 15)
            if left_arm_down or right_arm_down:
                is_horizontal_posture = True

        avg_elbow_angle = float(np.mean(elbow_angles))

        # ----------------------------------------------------
        # LAYER 3: Biomechanical Alignment Checks
        # ----------------------------------------------------
        body_angle = None
        if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"]):
            body_angle = self.body_line_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"]))
        elif are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"]):
            body_angle = self.body_line_smoother.update(calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"]))

        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great push-up! Push back up smoothly."
        fb_priority = 7

        if not is_horizontal_posture:
            feedback_list.append("Horizontal body posture required")
            is_good_form = False
            self.state = "UP"
            return self.build_result(
                self.state,
                primary_angle=avg_elbow_angle,
                secondary_angle=body_angle,
                feedback=feedback_list,
                valid=True,
                feedback_code="BODY_NOT_HORIZONTAL",
                feedback_detail="Keep your body horizontal from shoulders to hips.",
                feedback_priority=2,
            )

        if body_angle is not None and body_angle < 140.0:
            feedback_list.append("Keep back straight")
            is_good_form = False
            fb_code = "BACK_NOT_STRAIGHT"
            fb_detail = "Keep your back straight — avoid sagging or arching your hips."
            fb_priority = 3

        # ----------------------------------------------------
        # LAYER 4: State Machine & Temporal Movement Displacement
        # ----------------------------------------------------
        now = time.time()

        if self.state == "UP":
            if avg_elbow_angle <= self.down_angle:
                self.state = "DOWN"
                self.min_elbow_angle_in_rep = avg_elbow_angle
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Good depth! Push up")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Good chest depth! Now push up."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Push Down")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Lower your chest towards the floor."
                    fb_priority = 7

        elif self.state == "DOWN":
            self.displacement_tracker.update(keypoints)

            if avg_elbow_angle < self.min_elbow_angle_in_rep:
                self.min_elbow_angle_in_rep = avg_elbow_angle

            if avg_elbow_angle >= self.up_angle:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.min_elbow_angle_in_rep <= self.down_angle:
                        feedback_list.append("Great Rep!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great repetition! Controlled movement."
                        fb_priority = 7
                    else:
                        feedback_list.append("Go lower next time")
                        is_good_form = False
                        fb_code = "INSUFFICIENT_DEPTH"
                        fb_detail = "Lower your chest further for full depth."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Move through a full vertical range of motion."
                    fb_priority = 5

                self.state = "UP"
                self.min_elbow_angle_in_rep = 180.0
            else:
                if is_good_form:
                    feedback_list.append("Push Up!")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Push back up to starting position."
                    fb_priority = 7

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(
            self.state,
            primary_angle=avg_elbow_angle,
            secondary_angle=body_angle,
            feedback=feedback_list,
            valid=True,
            feedback_code=fb_code,
            feedback_detail=fb_detail,
            feedback_priority=fb_priority,
        )
