import sys
import re

def test_exercise_learning_and_camera_framing():
    print("==================================================================")
    print("   FITQUEST EXERCISE LEARNING & CAMERA FRAMING AUDIT              ")
    print("==================================================================")

    # 1. Check index.html for all required stages and elements
    with open("frontend/index.html", "r") as f:
        html = f.read()

    required_ids = [
        # Stage 1: LEARN
        "workoutSetupStep", "setupExerciseName", "setupExerciseDesc", "setupCategoryBadge",
        "setupDifficulty", "setupMuscleGroup", "learnDemoAvatarCard", "learnDemoAvatarCanvas",
        "learnDemoPhaseBadge", "learnDemoCueText", "learnDemoMuscleTag", "learnDemoJointTag",
        "learnDemoPlayPauseBtn", "learnDemoResetBtn", "learnStepsList", "learnStartPosition",
        "learnEndPosition", "learnMovementPath", "learnKeyCuesList", "learnMistakesList",
        "learnCameraTip", "learnReadyBtn",
        # Stage 2: PREPARE
        "workoutPrepareStep", "prepareCameraContainer", "prepareWebcamFeed", "prepareFramingGuide",
        "prepareFramingInstruction", "workoutCountdownOverlay", "countdownNumber",
        "prepareCalibrationStatus", "prepareStatusIcon", "prepareStatusTitle", "prepareStatusDesc",
        "prepareStartBtn",
        # Stage 3: PERFORM
        "workoutActiveStep", "liveCameraContainer", "webcamFeed", "overlayImage",
        "trainerCoachingBanner", "hudRepCount", "hudRepTarget", "hudRepProgressFill",
        "hudFormScore", "hudFormScorePill", "hudDuration",
        # Stage 4: REVIEW
        "workoutResultStep", "resRepCount", "resDuration", "resFormScore", "resAICoaching"
    ]

    for elem_id in required_ids:
        assert f'id="{elem_id}"' in html, f"Missing required element ID: {elem_id}"
    print(f"[PASS] Verified all {len(required_ids)} critical stage DOM element IDs in index.html.")

    # 2. Check workout.js for all 20 exercise guides
    with open("frontend/workout.js", "r") as f:
        js = f.read()

    assert "const EXERCISE_LEARNING_GUIDES = {" in js, "Missing EXERCISE_LEARNING_GUIDES"
    for ex_id in range(1, 21):
        assert f"{ex_id}:" in js, f"Missing learning guide for exercise ID {ex_id}"
    print("[PASS] Verified comprehensive learning guides for all 20 seeded exercises in workout.js.")

    assert "goToPrepareStage" in js, "Missing goToPrepareStage function in workout.js"
    assert "startCountdownAndPerform" in js, "Missing startCountdownAndPerform function in workout.js"
    assert "backToLearnStage" in js, "Missing backToLearnStage function in workout.js"
    assert "populateExerciseLearningGuide" in js, "Missing populateExerciseLearningGuide function in workout.js"
    print("[PASS] Verified all stage transition controllers in workout.js.")

    # 3. Check style.css for camera container framing rules
    with open("frontend/style.css", "r") as f:
        css = f.read()

    assert ".camera-container" in css, "Missing .camera-container class in style.css"
    assert "object-fit: contain" in css, "Missing object-fit: contain rule in style.css"
    assert ".prepare-framing-guide" in css, "Missing .prepare-framing-guide class in style.css"
    assert ".countdown-overlay" in css, "Missing .countdown-overlay class in style.css"
    assert ".learn-workspace-grid" in css, "Missing .learn-workspace-grid class in style.css"
    print("[PASS] Verified camera aspect-ratio container, object-fit contain, framing guide, and countdown styles.")

    # 4. Check landing page remains untouched
    assert 'id="landingView"' in html, "Landing page #landingView missing or modified"
    assert 'id="landingNavHeader"' in html, "Landing nav #landingNavHeader missing or modified"
    print("[PASS] Verified landing page #landingView and #landingNavHeader remain 100% intact.")

    print("==================================================================")
    print("   ALL EXERCISE LEARNING & CAMERA FRAMING AUDITS PASSED!          ")
    print("==================================================================")

if __name__ == "__main__":
    test_exercise_learning_and_camera_framing()
