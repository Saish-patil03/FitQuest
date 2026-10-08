import time
from typing import Optional, List, Dict, Any, Tuple

class TemporalStateValidator:
    """
    Prevents single-frame noise spikes, temporary keypoint jitter, and camera distance shifts
    (e.g., user moving toward or away from the camera) from triggering false state transitions or false reps.
    """
    def __init__(self, initial_state: str = "START", min_confirm_frames: int = 2, min_hold_sec: float = 0.12):
        self.current_state = initial_state
        self.pending_state = None
        self.pending_frame_count = 0
        self.min_confirm_frames = min_confirm_frames
        self.min_hold_sec = min_hold_sec
        self.state_enter_time = time.time()
        self.rep_start_time = None
        self.last_rep_time = 0.0

    def reset(self, initial_state: str = "START"):
        self.current_state = initial_state
        self.pending_state = None
        self.pending_frame_count = 0
        self.state_enter_time = time.time()
        self.rep_start_time = None
        self.last_rep_time = 0.0

    def update(self, proposed_state: str, is_valid_frame: bool = True) -> Tuple[str, bool]:
        """
        Evaluates proposed state against temporal multi-frame confirmation.
        Returns:
            (confirmed_state: str, state_changed_this_frame: bool)
        """
        now = time.time()
        if not is_valid_frame or proposed_state is None:
            self.pending_state = None
            self.pending_frame_count = 0
            return self.current_state, False

        if proposed_state == self.current_state:
            self.pending_state = None
            self.pending_frame_count = 0
            return self.current_state, False

        if proposed_state != self.pending_state:
            self.pending_state = proposed_state
            self.pending_frame_count = 1
        else:
            self.pending_frame_count += 1

        # Confirm state transition if consecutive frame threshold is met
        if self.pending_frame_count >= self.min_confirm_frames:
            self.current_state = self.pending_state
            self.pending_state = None
            self.pending_frame_count = 0
            self.state_enter_time = now

            if self.rep_start_time is None:
                self.rep_start_time = now

            return self.current_state, True

        return self.current_state, False

    def can_commit_rep(self, min_rep_duration_sec: float = 0.45, debounce_sec: float = 0.4) -> bool:
        """
        Validates that a rep cycle fulfilled the minimum temporal physical movement duration.
        """
        now = time.time()
        effective_min_duration = min(min_rep_duration_sec, debounce_sec)
        if (now - self.last_rep_time) < debounce_sec:
            return False

        if self.rep_start_time is not None:
            duration = now - self.rep_start_time
            if duration < effective_min_duration:
                return False

        self.last_rep_time = now
        self.rep_start_time = None
        return True



class BaseExerciseTracker:
    """
    Base interface for all exercise trackers in the AI Fitness system.
    Integrates TemporalStateValidator for multi-frame hysteresis & rep protection.
    """
    def __init__(self, name):
        self.name = name
        self.rep_count = 0
        self.form_scores = []  # Stores 1 for good form, 0 for poor form
        self.feedback_events = []  # Stores unique feedback messages across the session
        self.state_validator = TemporalStateValidator(initial_state="START")

    def validate_state_transition(
        self,
        proposed_state: str,
        is_valid_frame: bool = True,
        min_confirm_frames: int = 2,
        min_hold_sec: float = 0.12
    ) -> Tuple[str, bool]:
        """
        Confirms proposed state across consecutive valid frames before committing state transition.
        """
        self.state_validator.min_confirm_frames = min_confirm_frames
        self.state_validator.min_hold_sec = min_hold_sec
        return self.state_validator.update(proposed_state, is_valid_frame)

    def validate_rep_completion(self, min_rep_duration_sec: float = 0.45, debounce_sec: float = 0.4) -> bool:
        """
        Validates that rep movement cycle duration exceeds minimum physical threshold.
        """
        return self.state_validator.can_commit_rep(min_rep_duration_sec, debounce_sec)

    def process(self, keypoints):
        """
        Input: keypoints dict
        Output: Standard dictionary with exercise, rep_count, state, primary_angle, secondary_angle, form_score, feedback, valid
        """
        raise NotImplementedError


    def get_form_score(self):
        if not self.form_scores or self.rep_count == 0:
            return 0.0
        return round((sum(self.form_scores) / len(self.form_scores)) * 100.0, 1)

    def build_result(
        self,
        state: str,
        primary_angle: float = None,
        secondary_angle: float = None,
        feedback: list = None,
        valid: bool = True,
        feedback_code: str = None,
        feedback_detail: str = None,
        feedback_priority: int = None,
    ):
        fb = feedback if feedback is not None else ["GOOD FORM"]
        ignore_list = ["GOOD FORM", "Position arms in view", "Position legs in view", "Position body in view"]
        for msg in fb:
            if msg not in ignore_list and msg not in self.feedback_events:
                self.feedback_events.append(msg)

        # Infer structured feedback metadata if not explicitly provided
        if not feedback_code:
            if not valid:
                feedback_code = "LANDMARKS_MISSING"
                feedback_detail = fb[0] if fb else "Position yourself clearly in view"
                feedback_priority = 1
            elif any("GOOD FORM" in m or "Great" in m or "Good" in m for m in fb):
                feedback_code = "GOOD_FORM"
                feedback_detail = fb[0] if fb else "Great form! Maintain controlled movement."
                feedback_priority = 7
            elif any("Horizontal" in m or "posture" in m for m in fb):
                feedback_code = "BODY_NOT_HORIZONTAL"
                feedback_detail = fb[0]
                feedback_priority = 2
            elif any("back" in m or "straight" in m for m in fb):
                feedback_code = "BACK_NOT_STRAIGHT"
                feedback_detail = fb[0]
                feedback_priority = 3
            elif any("elbow" in m or "arm still" in m for m in fb):
                feedback_code = "ELBOW_MISALIGNED"
                feedback_detail = fb[0]
                feedback_priority = 3
            elif any("head" in m or "nod" in m or "neck" in m for m in fb):
                feedback_code = "HEAD_ONLY_MOVEMENT"
                feedback_detail = fb[0]
                feedback_priority = 3
            elif any("rotate" in m or "twist" in m for m in fb):
                feedback_code = "TORSO_ROTATION_INSUFFICIENT"
                feedback_detail = fb[0]
                feedback_priority = 3
            elif any("opposite" in m or "elbow to knee" in m for m in fb):
                feedback_code = "OPPOSITE_LIMB_MISMATCH"
                feedback_detail = fb[0]
                feedback_priority = 3
            elif any("torso" in m or "leaning" in m or "swinging" in m for m in fb):
                feedback_code = "TORSO_LEANING"
                feedback_detail = fb[0]
                feedback_priority = 3

            elif any("upper arm" in m or "stationary" in m for m in fb):
                feedback_code = "UPPER_ARM_MOVING"
                feedback_detail = fb[0]
                feedback_priority = 3
            elif any("alternate" in m or "alternating" in m for m in fb):
                feedback_code = "ALTERNATION_ERROR"
                feedback_detail = fb[0]
                feedback_priority = 3
            elif any("knee higher" in m or "knee to hip" in m or "knee toward chest" in m for m in fb):
                feedback_code = "KNEE_NOT_HIGH_ENOUGH"
                feedback_detail = fb[0]
                feedback_priority = 4
            elif any("feet wider" in m or "legs apart" in m or "spread" in m for m in fb):
                feedback_code = "LEGS_NOT_SEPARATED"
                feedback_detail = fb[0]
                feedback_priority = 4
            elif any("open both" in m or "incomplete" in m for m in fb):
                feedback_code = "JUMPING_JACK_INCOMPLETE"
                feedback_detail = fb[0]
                feedback_priority = 4
            elif any("higher" in m or "overhead" in m for m in fb):
                feedback_code = "ARM_NOT_HIGH_ENOUGH"
                feedback_detail = fb[0]
                feedback_priority = 4

            elif any("lower" in m or "depth" in m or "deeper" in m for m in fb):
                feedback_code = "INSUFFICIENT_DEPTH"
                feedback_detail = fb[0]
                feedback_priority = 4
            elif any("extend" in m for m in fb):
                feedback_code = "INSUFFICIENT_EXTENSION"
                feedback_detail = fb[0]
                feedback_priority = 4

            elif any("movement" in m or "range" in m for m in fb):
                feedback_code = "INSUFFICIENT_MOVEMENT"
                feedback_detail = fb[0]
                feedback_priority = 5
            else:
                feedback_code = "JOINT_ALIGNMENT_ERROR"
                feedback_detail = fb[0] if fb else "Form issue detected"
                feedback_priority = 3

        if not feedback_detail and fb:
            feedback_detail = fb[0]
        if feedback_priority is None:
            feedback_priority = 3

        return {
            "exercise": self.name,
            "rep_count": self.rep_count,
            "state": state,
            "primary_angle": round(primary_angle, 1) if primary_angle is not None else None,
            "secondary_angle": round(secondary_angle, 1) if secondary_angle is not None else None,
            "form_score": self.get_form_score(),
            "feedback": fb,
            "feedback_code": feedback_code,
            "feedback_detail": feedback_detail,
            "feedback_priority": feedback_priority,
            "valid": valid
        }
