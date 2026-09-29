import time
import numpy as np
from utils import (
    calculate_angle,
    AngleSmoother,
    BaseExerciseTracker,
    are_landmarks_valid,
    get_landmark_point,
)

class BicepCurlTracker(BaseExerciseTracker):
    """
    Bicep Curl Tracker:
    Measures Shoulder -> Elbow -> Wrist angle.
    States: EXTENDED (>145 deg) <-> CURLED (<65 deg)
    """
    def __init__(self, extended_angle=145.0, curled_angle=65.0, debounce_sec=0.4):
        super().__init__("Bicep Curl")
        self.extended_angle = extended_angle
        self.curled_angle = curled_angle
        self.debounce_sec = debounce_sec

        self.state = "EXTENDED"
        self.last_rep_time = 0.0

        self.left_elbow_smoother = AngleSmoother(alpha=0.35)
        self.right_elbow_smoother = AngleSmoother(alpha=0.35)
        self.min_angle_in_rep = 180.0

    def process(self, keypoints):
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
            return self.build_result(
                "EXTENDED",
                feedback=["Position arms in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position your arms and upper body clearly in camera view.",
                feedback_priority=1
            )

        avg_elbow_angle = float(np.mean(elbow_angles))
        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great curl! Controlled movement."
        fb_priority = 7
        now = time.time()

        # Check for upper arm / elbow sway alignment
        p_sh = get_landmark_point(keypoints, "left_shoulder") or get_landmark_point(keypoints, "right_shoulder")
        p_el = get_landmark_point(keypoints, "left_elbow") or get_landmark_point(keypoints, "right_elbow")
        if p_sh and p_el:
            # If elbow drifts too far horizontally relative to shoulder
            dx_elbow = abs(p_el[0] - p_sh[0])
            if dx_elbow > 80.0:  # Excessive elbow drift
                feedback_list.append("Keep upper arm still")
                is_good_form = False
                fb_code = "ELBOW_MISALIGNED"
                fb_detail = "Keep your upper arm still and your elbow close to your body."
                fb_priority = 3

        if self.state == "EXTENDED":
            if avg_elbow_angle <= self.curled_angle:
                self.state = "CURLED"
                self.min_angle_in_rep = avg_elbow_angle
                if is_good_form:
                    feedback_list.append("Good curl! Lower arms")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Good curl depth! Lower your arms under control."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Curl Up")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Curl your arm upward towards your shoulder."
                    fb_priority = 7

        elif self.state == "CURLED":
            if avg_elbow_angle < self.min_angle_in_rep:
                self.min_angle_in_rep = avg_elbow_angle

            if avg_elbow_angle >= self.extended_angle:
                if (now - self.last_rep_time) >= self.debounce_sec:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if self.min_angle_in_rep <= self.curled_angle:
                        feedback_list.append("Great Rep!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great rep! Full range of motion."
                        fb_priority = 7
                    else:
                        feedback_list.append("Curl higher next time")
                        is_good_form = False
                        fb_code = "INSUFFICIENT_DEPTH"
                        fb_detail = "Curl your arm further towards your shoulder."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)

                self.state = "EXTENDED"
                self.min_angle_in_rep = 180.0
            else:
                if is_good_form:
                    feedback_list.append("Lower Arms")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Extend your arms smoothly back down."
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
            feedback_priority=fb_priority
        )
