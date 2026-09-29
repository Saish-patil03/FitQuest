import base64
import time
import cv2
import numpy as np
from typing import Optional, Dict, Any, Tuple

from pose import PoseDetector
from exercise import ExerciseController, ExerciseRegistry
from assistant import WorkoutSessionData
from utils.angles import calculate_angle
from utils.keypoints import are_landmarks_valid
from backend.services.movement_intelligence import (
    MovementAnalyzer,
    SessionTelemetryBuffer,
    FrameTelemetrySample,
    EXERCISE_BENCHMARKS
)

class CVLiveService:
    """
    Bridge service connecting browser webcam frame streams with Member 3's CV Engine.
    Reuses PoseDetector & ExerciseController without modifying any tracking algorithms.
    Captures live frame and rep telemetry to compute Movement Fingerprints on session completion.
    """
    def __init__(self, model_path="models/pose_model.pt"):
        self.detector = None
        self.model_path = model_path
        self.active_sessions: Dict[str, ExerciseController] = {}
        self.session_buffers: Dict[str, SessionTelemetryBuffer] = {}

    def _ensure_detector(self):
        if self.detector is None:
            print("[INFO] Lazy-loading YOLO PoseDetector model for CV Live Service...")
            self.detector = PoseDetector(model_path=self.model_path, conf_threshold=0.25)

    def resolve_exercise_key(self, choice_key: str) -> Optional[str]:
        key = str(choice_key).strip()
        if key in ExerciseRegistry.EXERCISES:
            return key
        for k, (name, _) in ExerciseRegistry.EXERCISES.items():
            if name.lower() == key.lower():
                return k
        return None

    def start_session(self, session_id: str, exercise_choice: str = "1") -> ExerciseController:
        """
        Forces creation of a brand new, clean ExerciseController for session_id,
        purging any existing session state for that ID.
        """
        self._ensure_detector()
        resolved_key = self.resolve_exercise_key(exercise_choice)
        if not resolved_key:
            raise ValueError(f"Invalid exercise choice '{exercise_choice}'. Supported exercises: 1-20 or names like 'Squat'.")

        if session_id in self.active_sessions:
            print(f"[INFO] Purging existing session controller for session '{session_id}'")
            self.active_sessions.pop(session_id, None)
            self.session_buffers.pop(session_id, None)

        print(f"[INFO] Starting fresh CV live session '{session_id}' for exercise: {exercise_choice} (Key: {resolved_key})")
        controller = ExerciseController(resolved_key)
        self.active_sessions[session_id] = controller
        self.session_buffers[session_id] = SessionTelemetryBuffer(
            exercise_id=resolved_key,
            exercise_name=controller.tracker.name
        )
        return controller

    def get_or_create_session(self, session_id: str, exercise_choice: str = "1") -> ExerciseController:
        """
        Gets existing ExerciseController or creates a new one for session_id.
        Validates exercise_choice against ExerciseRegistry.
        Purges stale controllers if exercise choice changes for the session.
        """
        self._ensure_detector()
        
        # Validate exercise choice
        resolved_key = self.resolve_exercise_key(exercise_choice)
        if not resolved_key:
            raise ValueError(f"Invalid exercise choice '{exercise_choice}'. Supported exercises: 1-20 or names like 'Squat'.")

        if session_id in self.active_sessions:
            existing_controller = self.active_sessions[session_id]
            # If exercise changed for session, replace with fresh controller
            current_key = getattr(existing_controller, "exercise_key", getattr(existing_controller.tracker, "exercise_key", None))
            current_name = getattr(existing_controller.tracker, "name", "").lower()
            if current_key != resolved_key and current_name != exercise_choice.lower() and current_name != resolved_key.lower():
                print(f"[INFO] Re-initializing session '{session_id}' with fresh controller for exercise: {exercise_choice}")
                self.active_sessions.pop(session_id, None)
                self.session_buffers.pop(session_id, None)

        if session_id not in self.active_sessions:
            print(f"[INFO] Initializing new CV live session '{session_id}' for exercise: {exercise_choice} (Key: {resolved_key})")
            controller = ExerciseController(resolved_key)
            self.active_sessions[session_id] = controller
            self.session_buffers[session_id] = SessionTelemetryBuffer(
                exercise_id=resolved_key,
                exercise_name=controller.tracker.name
            )

        return self.active_sessions[session_id]

    def close_session(self, session_id: str) -> Optional[WorkoutSessionData]:
        """
        Terminates session, pops from active sessions, and returns final WorkoutSessionData summary.
        """
        summary, _ = self.close_session_with_movement(session_id)
        return summary

    def close_session_with_movement(self, session_id: str) -> Tuple[Optional[WorkoutSessionData], Optional[Dict[str, Any]]]:
        """
        Terminates session, computes final WorkoutSessionData and Movement Intelligence fingerprint.
        """
        if session_id in self.active_sessions:
            controller = self.active_sessions.pop(session_id, None)
            buffer = self.session_buffers.pop(session_id, None)
            if controller:
                controller.finish_session()
                session_data = controller.create_session_data()

                # Generate Movement Intelligence Analysis
                ex_key = getattr(controller, "exercise_key", "1")
                movement_analysis = MovementAnalyzer.analyze_session(
                    exercise_id=ex_key,
                    exercise_name=controller.tracker.name,
                    rep_count=session_data.rep_count,
                    duration_sec=session_data.duration_sec,
                    form_score=session_data.form_score,
                    telemetry_buffer=buffer
                )
                return session_data, movement_analysis

        return None, None

    def process_frame(
        self,
        controller: ExerciseController,
        frame_bytes: bytes,
        include_annotated_image: bool = True,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Decodes raw JPEG/PNG bytes, runs YOLO Pose inference & exercise tracker,
        captures telemetry sample, and returns live telemetry payload.
        """
        self._ensure_detector()

        # 1. Decode bytes into OpenCV BGR numpy array
        np_arr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return {
                "status": "error",
                "message": "Could not decode frame image bytes"
            }

        # 2. Process frame with Member 3 PoseDetector & active exercise tracker
        annotated_frame, keypoints, tracker_info = self.detector.process_frame(
            frame,
            tracker=controller.tracker
        )

        if tracker_info is None:
            return {
                "status": "warning",
                "message": "No keypoints detected",
                "exercise": controller.tracker.name,
                "rep_count": controller.tracker.rep_count,
                "form_score": controller.tracker.get_form_score(),
                "state": getattr(controller.tracker, "state", "UNKNOWN"),
                "feedback": ["Position yourself in view"],
                "feedback_code": "LANDMARKS_MISSING",
                "feedback_detail": "Position your body and key joints clearly in camera view.",
                "feedback_priority": 1,
                "valid": False,
                "annotated_frame": None
            }

        # 3. Capture Telemetry Snapshot in Session Buffer if active
        now_ts = time.time()
        left_angle = None
        right_angle = None
        torso_angle = None

        if keypoints:
            ex_key = getattr(controller, "exercise_key", "1")
            benchmark = EXERCISE_BENCHMARKS.get(str(ex_key), {})
            pairs = benchmark.get("joint_pairs", [])
            if len(pairs) == 2:
                left_pts, right_pts = pairs
                if are_landmarks_valid(keypoints, list(left_pts)):
                    left_angle = calculate_angle(keypoints[left_pts[0]], keypoints[left_pts[1]], keypoints[left_pts[2]])
                if are_landmarks_valid(keypoints, list(right_pts)):
                    right_angle = calculate_angle(keypoints[right_pts[0]], keypoints[right_pts[1]], keypoints[right_pts[2]])

            # Torso inclination / alignment
            if are_landmarks_valid(keypoints, ["left_shoulder", "left_hip", "left_knee"]):
                torso_angle = calculate_angle(keypoints["left_shoulder"], keypoints["left_hip"], keypoints["left_knee"])
            elif are_landmarks_valid(keypoints, ["right_shoulder", "right_hip", "right_knee"]):
                torso_angle = calculate_angle(keypoints["right_shoulder"], keypoints["right_hip"], keypoints["right_knee"])

        sample = FrameTelemetrySample(
            timestamp=now_ts,
            primary_angle=tracker_info.get("primary_angle"),
            secondary_angle=tracker_info.get("secondary_angle"),
            left_angle=left_angle,
            right_angle=right_angle,
            torso_angle=torso_angle,
            state=tracker_info.get("state", "START"),
            rep_count=tracker_info.get("rep_count", 0),
            valid=tracker_info.get("valid", True),
            feedback_code=tracker_info.get("feedback_code", "GOOD_FORM")
        )

        # Buffer telemetry by matching controller in active_sessions
        target_buf = None
        if session_id and session_id in self.session_buffers:
            target_buf = self.session_buffers[session_id]
        else:
            for s_id, s_ctrl in self.active_sessions.items():
                if s_ctrl is controller and s_id in self.session_buffers:
                    target_buf = self.session_buffers[s_id]
                    break

        if target_buf:
            target_buf.add_sample(sample)

        # 4. Optionally encode annotated frame with skeleton HUD overlay back to base64 JPEG
        annotated_b64 = None
        if include_annotated_image and annotated_frame is not None:
            _, buffer = cv2.imencode('.jpg', annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            annotated_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

        # 5. Return live telemetry payload
        return {
            "status": "success",
            "exercise": tracker_info["exercise"],
            "rep_count": tracker_info["rep_count"],
            "state": tracker_info["state"],
            "primary_angle": tracker_info["primary_angle"],
            "secondary_angle": tracker_info.get("secondary_angle"),
            "form_score": tracker_info["form_score"],
            "feedback": tracker_info["feedback"],
            "feedback_code": tracker_info.get("feedback_code", "GOOD_FORM"),
            "feedback_detail": tracker_info.get("feedback_detail", tracker_info["feedback"][0] if tracker_info.get("feedback") else "Good form"),
            "feedback_priority": tracker_info.get("feedback_priority", 7),
            "valid": tracker_info["valid"],
            "annotated_frame": annotated_b64
        }

    def process_base64_frame(
        self,
        controller: ExerciseController,
        base64_str: str,
        include_annotated_image: bool = True,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Decodes a base64 image data URL string and runs CV processing.
        """
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]

        frame_bytes = base64.b64decode(base64_str)
        return self.process_frame(controller, frame_bytes, include_annotated_image, session_id=session_id)

cv_live_service = CVLiveService()

