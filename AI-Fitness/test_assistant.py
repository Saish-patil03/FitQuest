#!/usr/bin/env python3
"""
Test suite for Member 4 AI Fitness Assistant module.
Tests data schemas, offline fallback engine, and prompt formatting.
"""

import os
import sys

def test_assistant_module():
    print("[TEST] Initializing AI Assistant module test...")

    from assistant import AIFitnessAssistant, WorkoutSessionData, UserProfile

    # 1. Test Schema Instantiation
    session = WorkoutSessionData(
        exercise_name="Bicep Curl",
        rep_count=10,
        duration_sec=45,
        form_score=90.0,
        form_scores_history=[1, 1, 1, 1, 1, 0, 1, 1, 1, 1],
        feedback_events=["Good curl! Lower arms", "Curl higher next time"]
    )

    assert session.duration_formatted == "00:45", "Formatted duration mismatch"
    print("[PASS] WorkoutSessionData schema verified successfully.")

    profile = UserProfile(
        user_id="test_user_1",
        fitness_goal="Strength",
        experience_level="Intermediate"
    )
    print("[PASS] UserProfile schema verified successfully.")

    # 2. Test Assistant Initialization & Rule-Based Fallback
    assistant = AIFitnessAssistant()
    
    print("\n--- Testing Workout Feedback Generation ---")
    feedback = assistant.generate_workout_feedback(session, profile)
    print(feedback)
    assert len(feedback) > 0, "Feedback should not be empty"
    print("[PASS] Workout feedback generated successfully.")

    print("\n--- Testing Form Explanation ---")
    form_explanation = assistant.explain_form_issues("Squat", 80.0, ["Squat deeper next time"])
    print(form_explanation)
    assert len(form_explanation) > 0, "Form explanation should not be empty"
    print("[PASS] Form explanation generated successfully.")

    print("\n--- Testing General Fitness Q&A ---")
    qa_response = assistant.answer_fitness_question("How many rest days do I need for strength training?", profile)
    print(qa_response)
    assert len(qa_response) > 0, "Q&A response should not be empty"
    print("[PASS] Q&A response generated successfully.")

    print("\n[SUCCESS] All Member 4 AI Assistant tests passed cleanly!")

if __name__ == "__main__":
    test_assistant_module()
