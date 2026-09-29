KEYPOINT_MAP = {
    "nose": 0,
    "left_eye": 1, "right_eye": 2,
    "left_ear": 3, "right_ear": 4,
    "left_shoulder": 5, "right_shoulder": 6,
    "left_elbow": 7, "right_elbow": 8,
    "left_wrist": 9, "right_wrist": 10,
    "left_hip": 11, "right_hip": 12,
    "left_knee": 13, "right_knee": 14,
    "left_ankle": 15, "right_ankle": 16,
}

def extract_keypoints(person_kpts, conf_threshold=0.25):
    """
    Extracts landmark dictionary from person_kpts numpy array.
    """
    keypoints = {}
    for kp_name, kp_idx in KEYPOINT_MAP.items():
        if kp_idx < len(person_kpts):
            x, y, conf = person_kpts[kp_idx]
            keypoints[kp_name] = {
                "x": float(x),
                "y": float(y),
                "conf": float(conf),
                "valid": bool(conf >= conf_threshold)
            }
    return keypoints

def are_landmarks_valid(keypoints, landmark_names):
    """
    Returns True if all specified landmark_names exist and are marked valid.
    """
    return all(keypoints.get(lm, {}).get("valid", False) for lm in landmark_names)
