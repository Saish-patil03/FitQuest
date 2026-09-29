import time
import numpy as np
from utils import (
    calculate_angle,
    calculate_distance,
    AngleSmoother,
    BaseExerciseTracker,
    are_landmarks_valid,
    get_landmark_point,
    check_body_orientation,
    MovementDisplacementTracker,
)

class BicycleCrunchTracker(BaseExerciseTracker):
    """
    Multi-Layer Bicycle Crunch Repetition Tracker & Form Evaluator.

    Enforces 4 Validation Layers:
    1. Landmark Visibility & Confidence
    2. Spatial Supine Posture Check
    3. Cross-Body Opposite Elbow-to-Knee Convergence Anti-Cheating (dist <= 80px)
    4. Pedal/Twist Movement Displacement (dx/dy >= 30px)
    """
    def __init__(
        self,
        crunch_angle: float = 90.0,
        debounce_sec: float = 0.3,
        min_displacement_px: float = 30.0,
    ):
        super().__init__("Bicycle Crunches")
        self.crunch_angle = crunch_angle
        self.debounce_sec = debounce_sec
        self.min_displacement_px = min_displacement_px

        self.state = "EXTENDED"
        self.last_rep_time = 0.0
        self.angle_smoother = AngleSmoother(alpha=0.35)
        self.displacement_tracker = MovementDisplacementTracker(
            ["left_knee", "right_knee", "left_elbow", "right_elbow"]
        )

    def process(self, keypoints):
        # Layer 1: Landmark Visibility
        left_valid = are_landmarks_valid(keypoints, ["left_elbow", "right_knee", "left_hip"])
        right_valid = are_landmarks_valid(keypoints, ["right_elbow", "left_knee", "right_hip"])

        crunch_angles = []
        if left_valid:
            crunch_angles.append(self.angle_smoother.update(calculate_angle(keypoints["left_elbow"], keypoints["left_hip"], keypoints["right_knee"])))
        if right_valid:
            crunch_angles.append(self.angle_smoother.update(calculate_angle(keypoints["right_elbow"], keypoints["right_hip"], keypoints["left_knee"])))

        if not crunch_angles:
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"]):
                crunch_angles.append(self.angle_smoother.update(calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])))

        if not crunch_angles:
            return self.build_result(
                "EXTENDED",
                feedback=["Position body in view"],
                valid=False,
                feedback_code="LANDMARKS_MISSING",
                feedback_detail="Position body, arms, and legs clearly in camera view.",
                feedback_priority=1,
            )

        # Layer 2: Spatial Orientation Check
        is_l_horiz, _ = check_body_orientation(keypoints, "left_shoulder", "left_hip", max_horizontal_deg=45.0)
        is_r_horiz, _ = check_body_orientation(keypoints, "right_shoulder", "right_hip", max_horizontal_deg=45.0)

        if not is_l_horiz and not is_r_horiz:
            return self.build_result(
                self.state,
                primary_angle=float(np.min(crunch_angles)),
                feedback=["Lie flat on back for bicycle crunches"],
                valid=True,
                feedback_code="INCORRECT_ORIENTATION",
                feedback_detail="Lie flat on your back for bicycle crunches.",
                feedback_priority=2,
            )

        min_crunch_angle = float(np.min(crunch_angles))
        feedback_list = []
        is_good_form = True
        fb_code = "GOOD_FORM"
        fb_detail = "Great bicycle crunch! Switch sides smoothly."
        fb_priority = 7
        now = time.time()

        # Layer 3: Cross-Body Opposite Elbow to Knee Convergence Check
        p_l_el = get_landmark_point(keypoints, "left_elbow")
        p_r_kn = get_landmark_point(keypoints, "right_knee")
        p_r_el = get_landmark_point(keypoints, "right_elbow")
        p_l_kn = get_landmark_point(keypoints, "left_knee")

        cross_dist = 999.0
        if p_l_el and p_r_kn:
            cross_dist = min(cross_dist, calculate_distance(p_l_el, p_r_kn))
        if p_r_el and p_l_kn:
            cross_dist = min(cross_dist, calculate_distance(p_r_el, p_l_kn))

        if cross_dist > 150.0 and self.state == "CRUNCHED":  # Elbow and opposite knee remain far apart
            feedback_list.append("Bring opposite elbow to knee")
            is_good_form = False
            fb_code = "OPPOSITE_LIMB_MISMATCH"
            fb_detail = "Bring your opposite elbow all the way to your opposite knee."
            fb_priority = 3

        # Layer 4: State Machine & Pedal Displacement
        if self.state == "EXTENDED":
            if min_crunch_angle <= self.crunch_angle:
                self.state = "CRUNCHED"
                self.displacement_tracker.capture_start(keypoints)
                if is_good_form:
                    feedback_list.append("Elbow to knee! Switch sides")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Elbow met opposite knee! Now switch sides."
                    fb_priority = 7
            else:
                if is_good_form:
                    feedback_list.append("Bring Elbow to Opposite Knee")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Rotate torso and bring opposite elbow to knee."
                    fb_priority = 7

        elif self.state == "CRUNCHED":
            self.displacement_tracker.update(keypoints)

            if min_crunch_angle >= self.crunch_angle + 25.0:
                max_displacement = self.displacement_tracker.get_max_displacement()
                has_sufficient_movement = (max_displacement >= self.min_displacement_px)

                if (now - self.last_rep_time) >= self.debounce_sec and has_sufficient_movement:
                    self.rep_count += 1
                    self.last_rep_time = now

                    if is_good_form:
                        feedback_list.append("Great Bicycle Crunch!")
                        fb_code = "GOOD_FORM"
                        fb_detail = "Great bicycle crunch! Excellent cross-body contraction."
                        fb_priority = 7
                    else:
                        feedback_list.append("Bring knee closer next time")
                        fb_code = "INSUFFICIENT_DEPTH"
                        fb_detail = "Rotate further and bring your knee closer to your elbow."
                        fb_priority = 4

                    self.form_scores.append(1 if is_good_form else 0)
                elif not has_sufficient_movement:
                    feedback_list.append("Full movement required")
                    is_good_form = False
                    fb_code = "INSUFFICIENT_MOVEMENT"
                    fb_detail = "Perform the full bicycle movement through a full range of motion."
                    fb_priority = 5

                self.state = "EXTENDED"
            else:
                if is_good_form:
                    feedback_list.append("Switch Sides")
                    fb_code = "GOOD_FORM"
                    fb_detail = "Extend leg out and switch to opposite side."
                    fb_priority = 7

        if is_good_form and not feedback_list:
            feedback_list.append("GOOD FORM")

        return self.build_result(
            self.state,
            primary_angle=min_crunch_angle,
            feedback=feedback_list,
            valid=True,
            feedback_code=fb_code,
            feedback_detail=fb_detail,
            feedback_priority=fb_priority,
        )
