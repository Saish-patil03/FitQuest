import math
import time
from typing import Dict, Any, List, Tuple, Optional
from utils.angles import calculate_angle, get_body_inclination

# Standardized Feedback Codes & Priority Hierarchy (Lower number = Higher Priority)
FEEDBACK_CODES = {
    "LANDMARKS_MISSING": {
        "priority": 1,
        "default_message": "Position your body and key joints clearly in camera view."
    },
    "BODY_NOT_HORIZONTAL": {
        "priority": 2,
        "default_message": "Keep your body horizontal from shoulders to hips."
    },
    "INCORRECT_ORIENTATION": {
        "priority": 2,
        "default_message": "Adjust your body orientation to match the exercise posture."
    },
    "BACK_NOT_STRAIGHT": {
        "priority": 3,
        "default_message": "Keep your back straight — avoid sagging or arching your hips."
    },
    "ELBOW_MISALIGNED": {
        "priority": 3,
        "default_message": "Keep your upper arm still — avoid moving your elbow forward."
    },
    "KNEE_MISALIGNED": {
        "priority": 3,
        "default_message": "Keep your knees aligned with your toes."
    },
    "HIP_TOO_HIGH": {
        "priority": 3,
        "default_message": "Lower your hips — keep your body level."
    },
    "HIP_TOO_LOW": {
        "priority": 3,
        "default_message": "Raise your hips — avoid sagging your core."
    },
    "JOINT_ALIGNMENT_ERROR": {
        "priority": 3,
        "default_message": "Maintain proper joint alignment throughout the movement."
    },
    "HEAD_ONLY_MOVEMENT": {
        "priority": 3,
        "default_message": "Sit up using your core — don't pull or nod with your head."
    },
    "HIP_POSITION_ERROR": {
        "priority": 3,
        "default_message": "Keep your hips in a level, aligned position."
    },
    "TORSO_ROTATION_INSUFFICIENT": {
        "priority": 3,
        "default_message": "Rotate your torso and shoulders — don't move only your hands."
    },
    "OPPOSITE_LIMB_MISMATCH": {
        "priority": 3,
        "default_message": "Bring your opposite elbow all the way to your opposite knee."
    },
    "PLANK_HOLD_BROKEN": {
        "priority": 2,
        "default_message": "Maintain a strong horizontal plank posture."
    },
    "UPPER_ARM_MOVING": {
        "priority": 3,
        "default_message": "Keep your upper arm stationary during the movement."
    },
    "TORSO_LEANING": {
        "priority": 3,
        "default_message": "Keep your torso still — avoid using body momentum."
    },
    "ALTERNATION_ERROR": {
        "priority": 3,
        "default_message": "Alternate your limbs correctly — left, then right."
    },
    "ARM_NOT_HIGH_ENOUGH": {
        "priority": 4,
        "default_message": "Raise your arms higher to shoulder or overhead height."
    },
    "LEGS_NOT_SEPARATED": {
        "priority": 4,
        "default_message": "Spread your feet wider during the jump."
    },
    "JUMPING_JACK_INCOMPLETE": {
        "priority": 4,
        "default_message": "Open both your arms and legs fully before returning."
    },
    "KNEE_NOT_HIGH_ENOUGH": {
        "priority": 4,
        "default_message": "Drive your knee higher toward your hip."
    },
    "INSUFFICIENT_DEPTH": {
        "priority": 4,
        "default_message": "Move deeper into the repetition."
    },


    "INSUFFICIENT_EXTENSION": {
        "priority": 4,
        "default_message": "Extend fully at the start and end of each rep."
    },
    "INSUFFICIENT_MOVEMENT": {
        "priority": 5,
        "default_message": "Move through a full range of motion."
    },
    "GOOD_FORM": {
        "priority": 7,
        "default_message": "Great form! Maintain this controlled movement."
    }
}

class FeedbackStabilizer:
    """
    Stabilizes live feedback strings to prevent rapid per-frame UI flickering.
    Overrides immediately if a higher-priority error occurs (lower numeric priority value).
    Otherwise holds active message for at least min_hold_sec (default 0.4s).
    """
    def __init__(self, min_hold_sec: float = 0.4):
        self.min_hold_sec = min_hold_sec
        self.active_code = "GOOD_FORM"
        self.active_message = FEEDBACK_CODES["GOOD_FORM"]["default_message"]
        self.active_priority = FEEDBACK_CODES["GOOD_FORM"]["priority"]
        self.last_update_time = 0.0

    def update(self, code: str, custom_message: Optional[str] = None) -> Tuple[str, str, int]:
        now = time.time()
        meta = FEEDBACK_CODES.get(code, FEEDBACK_CODES["GOOD_FORM"])
        new_priority = meta["priority"]
        new_msg = custom_message or meta["default_message"]

        # High priority override (lower numeric value) OR time hold window elapsed
        if new_priority < self.active_priority or (now - self.last_update_time) >= self.min_hold_sec:
            self.active_code = code
            self.active_message = new_msg
            self.active_priority = new_priority
            self.last_update_time = now

        return self.active_code, self.active_message, self.active_priority

def validate_landmarks(keypoints: Dict[str, Any], required_landmarks: List[str], min_conf: float = 0.25) -> bool:
    """
    Validates that all required landmarks exist in keypoints dict and have conf >= min_conf.
    """
    for lm in required_landmarks:
        kp = keypoints.get(lm)
        if not kp or not kp.get("valid", False) or kp.get("conf", 0.0) < min_conf:
            return False
    return True

def get_landmark_point(keypoints: Dict[str, Any], lm_name: str) -> Optional[Tuple[float, float]]:
    """
    Returns (x, y) tuple for landmark if valid, else None.
    """
    kp = keypoints.get(lm_name)
    if kp and kp.get("valid", False):
        return (kp["x"], kp["y"])
    return None

def calculate_distance(point_a: Tuple[float, float], point_b: Tuple[float, float]) -> float:
    """
    Calculates 2D Euclidean distance between two points.
    """
    return math.hypot(point_b[0] - point_a[0], point_b[1] - point_a[1])

def check_body_orientation(
    keypoints: Dict[str, Any],
    start_lm: str,
    end_lm: str,
    max_horizontal_deg: float = 45.0
) -> Tuple[bool, float]:
    """
    Calculates body inclination relative to horizontal plane for segment start_lm -> end_lm.
    Returns (is_horizontal, inclination_deg).
    For push-up / plank, inclination <= max_horizontal_deg indicates horizontal posture.
    """
    p_start = get_landmark_point(keypoints, start_lm)
    p_end = get_landmark_point(keypoints, end_lm)
    if not p_start or not p_end:
        return False, 90.0

    inclination = get_body_inclination(p_start, p_end)
    is_horizontal = (inclination <= max_horizontal_deg)
    return is_horizontal, inclination

def check_joint_alignment(
    keypoints: Dict[str, Any],
    lm1: str,
    lm2: str,
    lm3: str,
    min_angle: float = 135.0
) -> Tuple[bool, float]:
    """
    Calculates angle at vertex lm2 formed by lm1-lm2-lm3.
    Returns (is_aligned, angle_deg).
    """
    p1 = get_landmark_point(keypoints, lm1)
    p2 = get_landmark_point(keypoints, lm2)
    p3 = get_landmark_point(keypoints, lm3)
    if not p1 or not p2 or not p3:
        return False, 0.0

    angle = calculate_angle(p1, p2, p3)
    is_aligned = (angle >= min_angle)
    return is_aligned, angle

def check_relative_elevation(
    keypoints: Dict[str, Any],
    lower_lm: str,
    upper_lm: str,
    tolerance_px: float = 15.0
) -> bool:
    """
    Checks if lower_lm is vertically lower than (or equal to) upper_lm in image Y coordinates (y_lower >= y_upper).
    In image space, y=0 is top, y=H is bottom.
    """
    p_lower = get_landmark_point(keypoints, lower_lm)
    p_upper = get_landmark_point(keypoints, upper_lm)
    if not p_lower or not p_upper:
        return False
    return p_lower[1] >= (p_upper[1] - tolerance_px)

class MovementDisplacementTracker:
    """
    Tracks keypoint displacement across rep state cycles to verify physical movement.
    Normalizes spatial displacement by body scale to prevent camera distance shifts (moving closer/farther)
    from causing false movement readings.
    """
    def __init__(self, target_landmarks: List[str]):
        self.target_landmarks = target_landmarks
        self.start_positions: Dict[str, Tuple[float, float]] = {}
        self.max_displacements: Dict[str, float] = {}
        self.initial_body_scale: float = 100.0

    def reset(self):
        self.start_positions.clear()
        self.max_displacements.clear()
        self.initial_body_scale = 100.0

    def _get_body_scale(self, keypoints: Dict[str, Any]) -> float:
        """
        Calculates reference 2D body scale in pixels (shoulder width or torso height).
        """
        p_sh_l = get_landmark_point(keypoints, "left_shoulder")
        p_sh_r = get_landmark_point(keypoints, "right_shoulder")
        if p_sh_l and p_sh_r:
            sh_dist = calculate_distance(p_sh_l, p_sh_r)
            if sh_dist > 10.0:
                return sh_dist

        p_hip_l = get_landmark_point(keypoints, "left_hip")
        if p_sh_l and p_hip_l:
            torso_dist = calculate_distance(p_sh_l, p_hip_l)
            if torso_dist > 10.0:
                return torso_dist

        return 100.0

    def capture_start(self, keypoints: Dict[str, Any]):
        self.reset()
        self.initial_body_scale = self._get_body_scale(keypoints)
        for lm in self.target_landmarks:
            pt = get_landmark_point(keypoints, lm)
            if pt:
                self.start_positions[lm] = pt

    def update(self, keypoints: Dict[str, Any]):
        curr_body_scale = self._get_body_scale(keypoints)
        scale_ratio = self.initial_body_scale / max(10.0, curr_body_scale)

        for lm, start_pt in self.start_positions.items():
            curr_pt = get_landmark_point(keypoints, lm)
            if curr_pt:
                # Adjust current coordinate for camera z-axis zoom/depth scale shift
                dx = abs((curr_pt[0] - start_pt[0]) * scale_ratio)
                dy = abs((curr_pt[1] - start_pt[1]) * scale_ratio)
                total_disp = math.hypot(dx, dy)
                if lm not in self.max_displacements or total_disp > self.max_displacements[lm]:
                    self.max_displacements[lm] = total_disp

    def get_max_displacement(self) -> float:
        if not self.max_displacements:
            return 0.0
        return max(self.max_displacements.values())

