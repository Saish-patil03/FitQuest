import os
import sys
import time
from pathlib import Path
import cv2
import numpy as np
import torch
from ultralytics import YOLO

# Configure PyTorch CPU thread usage conservatively for small container environments
torch.set_num_threads(1)

# Resolve paths robustly relative to fitquest-ml service root
SERVICE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODELS_DIR = str(SERVICE_ROOT / "models")
DEFAULT_MODEL_PATH = str(SERVICE_ROOT / "models" / "pose_model.pt")
FALLBACK_MODEL_PATH = str(SERVICE_ROOT / "models" / "yolov8n-pose.pt")

class PoseDetector:
    """
    YOLO Pose detector with real-time HUD rendering, joint tracking,
    and modular exercise repetition counting.
    Decoupled standalone service edition with memory optimizations.
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

    def __init__(self, model_path=None, conf_threshold=0.25):
        self.conf_threshold = conf_threshold

        # Robust path resolution independent of current working directory
        if model_path is None or model_path == "models/pose_model.pt":
            self.model_path = DEFAULT_MODEL_PATH
        elif not os.path.isabs(model_path):
            self.model_path = str(SERVICE_ROOT / model_path)
        else:
            self.model_path = model_path

        models_dir = os.path.dirname(self.model_path)
        if not os.path.exists(models_dir):
            os.makedirs(models_dir, exist_ok=True)

        print(f"[INFO] Initializing YOLO Pose model from: {self.model_path}")
        if not os.path.exists(self.model_path):
            if os.path.exists(FALLBACK_MODEL_PATH):
                print(f"[INFO] Using fallback model at {FALLBACK_MODEL_PATH}...")
                self.model = YOLO(FALLBACK_MODEL_PATH)
                self.model.save(self.model_path)
                print(f"[INFO] Saved weights to {self.model_path}")
            else:
                print(f"[INFO] Pretrained weights not found locally. Loading yolov8n-pose.pt...")
                self.model = YOLO("yolov8n-pose.pt")
                self.model.save(self.model_path)
                print(f"[INFO] Saved pretrained weights to {self.model_path}")
        else:
            self.model = YOLO(self.model_path)

        print("[INFO] YOLO Pose model loaded successfully.")

    def process_frame(
        self,
        frame,
        tracker=None,
        draw_debug_hud=False,
        clean_overlay=True,
        include_annotated_image=True
    ):
        with torch.inference_mode():
            results = self.model(frame, verbose=False, max_det=1)

        annotated_frame = None
        if include_annotated_image:
            if clean_overlay:
                # Clean, subtle skeleton: omit bounding boxes, class labels, and confidence numbers
                try:
                    annotated_frame = results[0].plot(boxes=False, labels=False, conf=False, kpt_radius=3, line_width=2)
                except Exception:
                    annotated_frame = results[0].plot()
            else:
                annotated_frame = results[0].plot()

        keypoints = {}
        body_detected = False

        if len(results) > 0 and results[0].keypoints is not None and len(results[0].keypoints.data) > 0:
            person_kpts = results[0].keypoints.data[0].cpu().numpy()

            for kp_name, kp_idx in self.KEYPOINT_MAP.items():
                if kp_idx < len(person_kpts):
                    x, y, conf = person_kpts[kp_idx]
                    keypoints[kp_name] = {
                        "x": float(x),
                        "y": float(y),
                        "conf": float(conf),
                        "valid": bool(conf >= self.conf_threshold)
                    }

            # Body is detected if any key upper body / torso landmarks are visible
            core_landmarks = ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_hip", "right_hip"]
            valid_core_count = sum(1 for lm in core_landmarks if keypoints.get(lm, {}).get("valid", False))
            body_detected = (valid_core_count >= 1)
            del person_kpts

        del results

        tracker_info = None
        if tracker is not None:
            tracker_info = tracker.process(keypoints)
            if draw_debug_hud and annotated_frame is not None:
                self.draw_hud(annotated_frame, tracker_info, body_detected)

        return annotated_frame, keypoints, tracker_info

    def draw_hud(self, frame, tracker_info, body_detected):
        if tracker_info is None:
            return

        h, w, _ = frame.shape

        # Balanced responsive card sizing: 220-270px width (approx 34-36% of 640px frame)
        padding = max(12, int(w * 0.02))
        card_w = min(270, max(220, int(w * 0.36)))

        # Extract values
        ex_name = str(tracker_info.get("exercise", "")).upper()
        reps = tracker_info.get("rep_count", 0)
        state = str(tracker_info.get("state", "N/A")).upper()
        angle = tracker_info.get("primary_angle")
        angle_str = f"{angle:.1f}°" if isinstance(angle, (int, float)) else "N/A"

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

        # Line 3: Joint Angle
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
    detector = PoseDetector(model_path=DEFAULT_MODEL_PATH, conf_threshold=0.25)
    detector.start_stream()
