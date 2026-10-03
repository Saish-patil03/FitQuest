# pyrefly: ignore [missing-import]
import cv2
import os
import time
import numpy as np
from ultralytics import YOLO

try:
    from utils.angles import AngleSmoother
except Exception:
    class AngleSmoother:
        def __init__(self, alpha: float = 0.45, deadband_deg: float = 0.8, max_step_deg: float = 90.0, window_size: int = 3):
            self.alpha = alpha
            self.deadband_deg = deadband_deg
            self.max_step_deg = max_step_deg
            self.window_size = window_size
            self.window = []
            self.smoothed_value = None
        def update(self, val):
            if val is None or not isinstance(val, (int, float)) or np.isnan(val):
                return self.smoothed_value
            v = float(val)
            self.window.append(v)
            if len(self.window) > self.window_size:
                self.window.pop(0)
            median_val = sorted(self.window)[len(self.window) // 2]
            if self.smoothed_value is None:
                self.smoothed_value = median_val
                return round(self.smoothed_value, 2)
            diff = median_val - self.smoothed_value
            if abs(diff) < self.deadband_deg:
                return round(self.smoothed_value, 2)
            if abs(diff) > self.max_step_deg:
                clamped_diff = np.sign(diff) * self.max_step_deg
                target = self.smoothed_value + clamped_diff
            else:
                target = median_val
            self.smoothed_value = (self.alpha * target) + ((1.0 - self.alpha) * self.smoothed_value)
            return round(self.smoothed_value, 2)

class KeypointSmoother:
    """
    Temporal Keypoint Filter (Exponential Moving Average + Inertial Occlusion Buffer):
    Stabilizes joint coordinates across consecutive frames, eliminating high-frequency jitter
    and erratic joint snapping while keeping latency imperceptible (<0.02ms).
    """
    def __init__(self, alpha: float = 0.45, min_confidence: float = 0.35, hold_frames: int = 3):
        self.alpha = alpha
        self.min_confidence = min_confidence
        self.hold_frames = hold_frames
        self.history = {}

    def smooth(self, raw_keypoints: dict) -> dict:
        smoothed = {}
        for name, pt in raw_keypoints.items():
            raw_x = float(pt["x"])
            raw_y = float(pt["y"])
            conf = float(pt.get("conf", 1.0))

            prev = self.history.get(name)
            if prev is None:
                is_valid = bool(conf >= self.min_confidence)
                smoothed[name] = {
                    "x": round(raw_x, 2),
                    "y": round(raw_y, 2),
                    "conf": conf,
                    "valid": is_valid
                }
                if is_valid:
                    self.history[name] = {"x": raw_x, "y": raw_y, "miss_count": 0, "conf": conf}
            else:
                if conf >= self.min_confidence:
                    # Adaptive Alpha: high confidence gives standard responsive alpha;
                    # lower confidence gives stronger damping to suppress jumpiness
                    cur_alpha = self.alpha if conf >= 0.50 else (self.alpha * 0.6)
                    smooth_x = cur_alpha * raw_x + (1.0 - cur_alpha) * prev["x"]
                    smooth_y = cur_alpha * raw_y + (1.0 - cur_alpha) * prev["y"]

                    self.history[name] = {
                        "x": smooth_x,
                        "y": smooth_y,
                        "miss_count": 0,
                        "conf": conf
                    }
                    smoothed[name] = {
                        "x": round(smooth_x, 2),
                        "y": round(smooth_y, 2),
                        "conf": conf,
                        "valid": True
                    }
                else:
                    # Temporary occlusion / frame dip: maintain previous valid position with decayed confidence
                    prev["miss_count"] += 1
                    if prev["miss_count"] <= self.hold_frames:
                        smoothed[name] = {
                            "x": round(prev["x"], 2),
                            "y": round(prev["y"], 2),
                            "conf": round(conf * 0.7, 2),
                            "valid": True
                        }
                    else:
                        smoothed[name] = {
                            "x": round(raw_x, 2),
                            "y": round(raw_y, 2),
                            "conf": conf,
                            "valid": False
                        }
        return smoothed

    def reset(self):
        self.history.clear()

class PoseDetector:
    """
    YOLO Pose detector with real-time HUD rendering, joint tracking,
    temporal EMA keypoint smoothing, and modular exercise repetition counting.
    """
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

    def __init__(self, model_path="models/pose_model.pt", conf_threshold=0.35):
        self.conf_threshold = conf_threshold
        self.model_path = model_path
        self.keypoint_smoother = KeypointSmoother(alpha=0.45, min_confidence=conf_threshold, hold_frames=3)
        self.hud_angle_smoother = AngleSmoother(alpha=0.45, deadband_deg=0.8, max_step_deg=90.0)
        
        if not os.path.exists("models"):
            os.makedirs("models")

        # Enable OpenCV hardware instruction optimization
        cv2.setUseOptimized(True)

        # Detect hardware execution device (CUDA GPU, Apple MPS, or CPU)
        try:
            import torch
            if torch.cuda.is_available():
                self.device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        except Exception:
            self.device = "cpu"

        print(f"[INFO] Initializing YOLO Pose Nano model on device '{self.device}'...")
        if not os.path.exists(model_path):
            print(f"[INFO] Pretrained weights not found at {model_path}. Loading yolov8n-pose.pt...")
            self.model = YOLO("yolov8n-pose.pt")
            self.model.save(model_path)
            print(f"[INFO] Saved pretrained weights to {model_path}")
        else:
            self.model = YOLO(model_path)

        try:
            self.model.to(self.device)
            if self.device == "cpu":
                import torch
                torch.set_num_threads(2)
        except Exception:
            pass

        print(f"[INFO] YOLO Pose model loaded successfully on {self.device}.")

    def process_frame(self, frame, tracker=None, draw_debug_hud=False, clean_overlay=True):
        # Optimized 320p inference with torch.inference_mode: 3x faster on serverless CPU
        try:
            import torch
            with torch.inference_mode():
                results = self.model(frame, imgsz=320, device=self.device, verbose=False)
        except Exception:
            results = self.model(frame, imgsz=320, device=self.device, verbose=False)

        raw_keypoints = {}
        body_detected = False

        if len(results) > 0 and results[0].keypoints is not None and len(results[0].keypoints.data) > 0:
            person_kpts = results[0].keypoints.data[0].cpu().numpy()

            for kp_name, kp_idx in self.KEYPOINT_MAP.items():
                if kp_idx < len(person_kpts):
                    x, y, conf = person_kpts[kp_idx]
                    raw_keypoints[kp_name] = {
                        "x": float(x),
                        "y": float(y),
                        "conf": float(conf),
                        "valid": bool(conf >= self.conf_threshold)
                    }

        # Apply Temporal Keypoint Smoothing (EMA) across consecutive frames
        keypoints = self.keypoint_smoother.smooth(raw_keypoints) if raw_keypoints else {}

        # Body is detected if key upper body / torso landmarks are stable
        core_landmarks = ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_hip", "right_hip"]
        valid_core_count = sum(1 for lm in core_landmarks if keypoints.get(lm, {}).get("valid", False))
        body_detected = (valid_core_count >= 1)

        if clean_overlay:
            # Clean, subtle skeleton: omit bounding boxes, class labels, and confidence numbers
            try:
                annotated_frame = results[0].plot(boxes=False, labels=False, conf=False, kpt_radius=3, line_width=2)
            except Exception:
                annotated_frame = results[0].plot()
        else:
            annotated_frame = results[0].plot()

        tracker_info = None
        if tracker is not None:
            tracker_info = tracker.process(keypoints)
            if draw_debug_hud:
                self.draw_hud(annotated_frame, tracker_info, body_detected, keypoints)

        return annotated_frame, keypoints, tracker_info

    def draw_hud(self, frame, tracker_info, body_detected, keypoints=None):
        if tracker_info is None:
            return

        h, w, _ = frame.shape

        # Balanced responsive card sizing: 220-270px width (approx 34-36% of 640px frame)
        padding = max(12, int(w * 0.02))
        card_w = min(270, max(220, int(w * 0.36)))

        # Extract & smooth primary angle
        ex_name = str(tracker_info.get("exercise", "")).upper()
        reps = tracker_info.get("rep_count", 0)
        state = str(tracker_info.get("state", "N/A")).upper()
        raw_angle = tracker_info.get("primary_angle")
        smoothed_angle = self.hud_angle_smoother.update(raw_angle) if raw_angle is not None else None
        angle_str = f"{smoothed_angle:.1f}°" if isinstance(smoothed_angle, (int, float)) else "N/A"

        valid = tracker_info.get("valid", True)
        feedback_code = tracker_info.get("feedback_code", "GOOD_FORM")
        feedback_detail = tracker_info.get("feedback_detail") or (
            tracker_info.get("feedback", [""])[0] if tracker_info.get("feedback") else ""
        )

        # Status text & color
        if not valid or feedback_code == "LANDMARKS_MISSING":
            status_text = "STATUS: BODY NOT DETECTED"
            status_color = (0, 0, 255)      # Red
        elif feedback_code == "GOOD_FORM":
            status_text = "STATUS: GOOD FORM"
            status_color = (0, 255, 128)    # Green
        else:
            status_text = "STATUS: FORM ISSUE"
            status_color = (0, 165, 255)    # Orange

        # 1-2 compact lines of word-wrapped feedback text
        words = feedback_detail.split()
        lines = []
        curr_line = ""
        max_text_w = card_w - 24
        font_scale_fb = 0.42

        for word in words:
            test_line = f"{curr_line} {word}".strip()
            (tw, _), _ = cv2.getTextSize(test_line, cv2.FONT_HERSHEY_SIMPLEX, font_scale_fb, 1)
            if tw <= max_text_w:
                curr_line = test_line
            else:
                if curr_line:
                    lines.append(curr_line)
                curr_line = word
        if curr_line:
            lines.append(curr_line)
        lines = lines[:2]

        card_h = min(160, 92 + len(lines) * 18)

        card_x1 = padding
        card_y1 = padding
        card_x2 = card_x1 + card_w
        card_y2 = card_y1 + card_h

        # Translucent dark slate card with cyan border
        overlay = frame.copy()
        cv2.rectangle(overlay, (card_x1, card_y1), (card_x2, card_y2), (15, 23, 42), -1)
        cv2.rectangle(overlay, (card_x1, card_y1), (card_x2, card_y2), (0, 242, 254), 1)
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

        curr_y = card_y1 + 22

        # Line 1: Exercise Title
        cv2.putText(frame, ex_name, (card_x1 + 12, curr_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 242, 254), 1, cv2.LINE_AA)
        curr_y += 24

        # Line 2: REPS & STATE
        cv2.putText(frame, f"REPS: {reps}", (card_x1 + 12, curr_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 128), 2, cv2.LINE_AA)

        state_color = (0, 242, 254) if state in ["UP", "STANDING", "EXTENDED", "CLOSED", "HOLDING"] else (255, 165, 0)
        (reps_w, _), _ = cv2.getTextSize(f"REPS: {reps}", cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        state_x = max(card_x1 + 110, card_x1 + 20 + reps_w)
        cv2.putText(frame, f"STATE: {state}", (state_x, curr_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, state_color, 1, cv2.LINE_AA)
        curr_y += 20

        # Line 3: Stabilized Joint Angle
        cv2.putText(frame, f"Angle: {angle_str}", (card_x1 + 12, curr_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1, cv2.LINE_AA)
        curr_y += 20

        # Line 4: Status Badge
        cv2.putText(frame, status_text, (card_x1 + 12, curr_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, status_color, 1, cv2.LINE_AA)
        curr_y += 20

        # Line 5-6: Actionable Feedback Detail
        for line in lines:
            if curr_y <= card_y2 - 6:
                cv2.putText(frame, line, (card_x1 + 12, curr_y),
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale_fb, (255, 255, 255), 1, cv2.LINE_AA)
                curr_y += 18

        # --- Visual On-Joint Angle Indicator Overlay (e.g. 90° indicator) ---
        if keypoints and smoothed_angle is not None and isinstance(smoothed_angle, (int, float)):
            target_joint = None
            if "SQUAT" in ex_name or "LUNGE" in ex_name:
                for k in ["left_knee", "right_knee"]:
                    if keypoints.get(k, {}).get("valid"):
                        target_joint = keypoints[k]
                        break
            else:
                for k in ["left_elbow", "right_elbow", "left_shoulder", "right_shoulder"]:
                    if keypoints.get(k, {}).get("valid"):
                        target_joint = keypoints[k]
                        break

            if target_joint and target_joint.get("x") is not None:
                jx = int(target_joint["x"])
                jy = int(target_joint["y"])

                # Draw angle indicator callout pill near the joint
                is_near_90 = abs(smoothed_angle - 90.0) <= 6.0
                pill_color = (0, 255, 128) if is_near_90 else (0, 242, 254)
                badge_text = f"{smoothed_angle:.0f}°"
                if is_near_90:
                    badge_text = f"90° TARGET"

                (tw, th), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                bx1 = max(4, jx + 12)
                by1 = max(4, jy - 22)
                bx2 = min(w - 4, bx1 + tw + 14)
                by2 = min(h - 4, by1 + th + 10)

                # Translucent pill background
                pill_overlay = frame.copy()
                cv2.rectangle(pill_overlay, (bx1, by1), (bx2, by2), (15, 23, 42), -1)
                cv2.rectangle(pill_overlay, (bx1, by1), (bx2, by2), pill_color, 1)
                cv2.addWeighted(pill_overlay, 0.75, frame, 0.25, 0, frame)

                # Neon badge text
                cv2.putText(frame, badge_text, (bx1 + 7, by2 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, pill_color, 1, cv2.LINE_AA)
                cv2.circle(frame, (jx, jy), 4, pill_color, -1, cv2.LINE_AA)




    def start_stream(self, camera_index=0, window_name="AI Fitness Engine"):
        cap = cv2.VideoCapture(camera_index)

        if not cap.isOpened():
            print(f"[ERROR] Could not open video device at index {camera_index}")
            return

        print("[INFO] Camera stream started.")
        print("[INFO] Press 'q' to quit.")

        prev_time = time.time()

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    print("[WARNING] Failed to grab frame. Exiting.")
                    break

                annotated_frame, keypoints, tracker_info = self.process_frame(frame)

                curr_time = time.time()
                fps = 1.0 / (curr_time - prev_time + 1e-6)
                prev_time = curr_time
                cv2.putText(annotated_frame, f"FPS: {int(fps)}", (frame.shape[1] - 110, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

                cv2.imshow(window_name, annotated_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("[INFO] User pressed 'q'. Stopping stream.")
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("[INFO] Camera stream stopped cleanly.")

if __name__ == "__main__":
    detector = PoseDetector(model_path="models/pose_model.pt", conf_threshold=0.25)
    detector.start_stream()
