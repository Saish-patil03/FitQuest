import math

def calculate_angle(point_a, point_b, point_c):
    """
    Calculates 2D angle (in degrees) at vertex point_b formed by segments (BA) and (BC).
    Each point can be a tuple/list (x, y) or dict {"x": x, "y": y}.

    Returns:
        float: Angle in degrees in range [0.0, 180.0].
    """
    if isinstance(point_a, dict):
        a = (point_a["x"], point_a["y"])
    else:
        a = (point_a[0], point_a[1])

    if isinstance(point_b, dict):
        b = (point_b["x"], point_b["y"])
    else:
        b = (point_b[0], point_b[1])

    if isinstance(point_c, dict):
        c = (point_c["x"], point_c["y"])
    else:
        c = (point_c[0], point_c[1])

    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])

    dot_product = ba[0] * bc[0] + ba[1] * bc[1]
    magnitude_ba = math.hypot(ba[0], ba[1])
    magnitude_bc = math.hypot(bc[0], bc[1])

    if magnitude_ba == 0 or magnitude_bc == 0:
        return 0.0

    cosine_angle = dot_product / (magnitude_ba * magnitude_bc)
    cosine_angle = max(-1.0, min(1.0, cosine_angle))

    angle_rad = math.acos(cosine_angle)
    angle_deg = math.degrees(angle_rad)

    return round(angle_deg, 2)


def get_body_inclination(point_a, point_b):
    """
    Calculates the inclination angle (in degrees) of line segment AB relative to horizontal plane.
    0 degrees = completely horizontal, 90 degrees = completely vertical.
    """
    if isinstance(point_a, dict):
        a = (point_a["x"], point_a["y"])
    else:
        a = (point_a[0], point_a[1])

    if isinstance(point_b, dict):
        b = (point_b["x"], point_b["y"])
    else:
        b = (point_b[0], point_b[1])

    dx = abs(b[0] - a[0])
    dy = abs(b[1] - a[1])

    if dx == 0:
        return 90.0

    angle_rad = math.atan2(dy, dx)
    return round(math.degrees(angle_rad), 2)


class AngleSmoother:
    """
    Multi-stage Angle Filter:
    Combines 3-frame Median Pre-filter + Deadband Noise Gate + Bounded EMA Smoothing.
    Dampens camera keypoint jitter and single-frame tracking spikes while preserving fast physical motion.
    """
    def __init__(self, alpha: float = 0.35, deadband_deg: float = 0.5, max_step_deg: float = 180.0, window_size: int = 3):
        self.alpha = alpha
        self.deadband_deg = deadband_deg
        self.max_step_deg = max_step_deg
        self.window_size = window_size
        
        self.window = []
        self.smoothed_value = None
        self.raw_value = None

    def update(self, new_value):
        """
        Updates smoothed angle cleanly. Returns float angle in degrees or None.
        Safely handles None, NaN, or non-numeric inputs.
        """
        if new_value is None or not isinstance(new_value, (int, float)) or math.isnan(new_value):
            return self.smoothed_value

        val = float(new_value)
        self.raw_value = val

        # 1. 3-frame rolling window pre-filter (eliminates isolated 1-frame spikes)
        self.window.append(val)
        if len(self.window) > self.window_size:
            self.window.pop(0)

        # Median of rolling window
        sorted_win = sorted(self.window)
        median_val = sorted_win[len(sorted_win) // 2]

        # 2. Initial state
        if self.smoothed_value is None:
            self.smoothed_value = median_val
            return round(self.smoothed_value, 2)

        # 3. Deadband Noise Gate: Ignore tiny fluctuations under deadband_deg
        diff = median_val - self.smoothed_value
        if abs(diff) < self.deadband_deg:
            return round(self.smoothed_value, 2)

        # 4. Outlier Bounded Step: Limit maximum angular change allowed per single frame
        if abs(diff) > self.max_step_deg:
            clamped_diff = math.copysign(self.max_step_deg, diff)
            target = self.smoothed_value + clamped_diff
        else:
            target = median_val

        # 5. EMA Update
        self.smoothed_value = (self.alpha * target) + ((1.0 - self.alpha) * self.smoothed_value)
        return round(self.smoothed_value, 2)

    def reset(self):
        """
        Resets all filter history cleanly between exercises or workout sessions.
        """
        self.window.clear()
        self.smoothed_value = None
        self.raw_value = None




