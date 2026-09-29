#!/usr/bin/env python3
"""
Integration test suite for Phase 3:
Connecting Member 3 Computer Vision engine with Member 4 AI Fitness Assistant.
"""

import time
from exercise import ExerciseController
from assistant import AIFitnessAssistant, WorkoutSessionData, UserProfile

def test_integration_flow():
    print("[TEST] Starting Phase 3 Integration Test Suite...")

    # 1. Initialize ExerciseController for Squat (Choice 2)
    controller = ExerciseController("2")
    assert controller.tracker.name == "Squat", f"Expected Squat, got {controller.tracker.name}"
    print("[PASS] ExerciseController initialized cleanly.")

    # 2. Simulate frames to generate rep counts, form scores, and feedback events
    # Simulate a good rep
    controller.tracker.rep_count = 5
    controller.tracker.form_scores = [1, 1, 1, 0, 1]  # 4 good, 1 bad = 80.0%
    controller.tracker.feedback_events = ["Squat deeper next time"]

    # Sleep slightly to ensure duration_sec > 0
    time.sleep(1.0)
    controller.end_time = time.time()

    # 3. Test WorkoutSessionData creation from ExerciseController
    session_data = controller.create_session_data()
    assert isinstance(session_data, WorkoutSessionData), "Expected WorkoutSessionData object"
    assert session_data.exercise_name == "Squat", f"Mapped name mismatch: {session_data.exercise_name}"
    assert session_data.rep_count == 5, f"Mapped reps mismatch: {session_data.rep_count}"
    assert session_data.duration_sec >= 1, f"Mapped duration mismatch: {session_data.duration_sec}"
    assert session_data.form_score == 80.0, f"Mapped form score mismatch: {session_data.form_score}"
    assert session_data.form_scores_history == [1, 1, 1, 0, 1], "Mapped history mismatch"
    assert session_data.feedback_events == ["Squat deeper next time"], "Mapped feedback events mismatch"
    print("[PASS] WorkoutSessionData extracted correctly from CV engine.")

    # 4. Test finish_session() without UserProfile (Default handling)
    summary_default = controller.finish_session()
    assert "WORKOUT SUMMARY" in summary_default, "CV Workout Summary missing from output"
    assert "AI COACHING" in summary_default, "AI Coaching section missing from output"
    assert "Squat" in summary_default, "Exercise name missing from summary"
    print("[PASS] finish_session() with default UserProfile executed successfully.")

    # 5. Test finish_session() with custom UserProfile
    profile = UserProfile(user_id="user_123", fitness_goal="Hypertrophy", experience_level="Advanced")
    summary_profile = controller.finish_session(user_profile=profile)
    assert "WORKOUT SUMMARY" in summary_profile
    assert "AI COACHING" in summary_profile
    print("[PASS] finish_session() with custom UserProfile executed successfully.")

    # 6. Test Fault Tolerance / API Failure Fallback
    class BrokenAssistant(AIFitnessAssistant):
        def generate_workout_feedback(self, session_data, user_profile=None):
            raise RuntimeError("Simulated API Error / Network Outage")

    summary_fault = controller.finish_session(assistant=BrokenAssistant())
    assert "WORKOUT SUMMARY" in summary_fault, "CV Workout Summary must survive API errors"
    assert "AI Coaching feedback unavailable" in summary_fault, "Fault handling message missing"
    print("[PASS] System handled API failure gracefully without crashing!")

    print("\n[SUCCESS] All Phase 3 Integration Tests Passed Cleanly!")

if __name__ == "__main__":
    test_integration_flow()
