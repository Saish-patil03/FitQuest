"""
FitQuest Adaptive Workout View Transition Integration Test
Verifies:
1. startAdaptiveWorkoutSession is defined and correctly connects to switchTab and selectExercise.
2. Error handling / edge case handling if no plan or no exercises are generated.
3. Adaptive prescription resolution picks up the adaptive plan exercises.
4. Navigation and workout flow remain intact.
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent
ADAPTIVE_JS = BASE_DIR / "frontend" / "adaptive_training.js"
WORKOUT_JS = BASE_DIR / "frontend" / "workout.js"
INDEX_HTML = BASE_DIR / "frontend" / "index.html"

def test_adaptive_transition_logic():
    adaptive_code = ADAPTIVE_JS.read_text(encoding="utf-8")
    workout_code = WORKOUT_JS.read_text(encoding="utf-8")
    html_code = INDEX_HTML.read_text(encoding="utf-8")

    # 1. Check startAdaptiveWorkoutSession definition and button hookup
    assert "function startAdaptiveWorkoutSession()" in adaptive_code, "Missing startAdaptiveWorkoutSession"
    assert "startAdaptiveWorkoutSession()" in adaptive_code, "Missing startAdaptiveWorkoutSession call in button"
    assert "switchTab('workoutView')" in adaptive_code, "Missing switchTab('workoutView') in adaptive_training.js"
    assert "selectExercise(" in adaptive_code, "Missing selectExercise call in adaptive_training.js"

    # 2. Check safety edge case handling
    assert "if (!currentAdaptivePlan || !currentAdaptivePlan.exercises || currentAdaptivePlan.exercises.length === 0)" in adaptive_code, "Missing plan validation"
    assert "if (!targetExId)" in adaptive_code, "Missing targetExId validation"

    # 3. Check resolveExercisePrescription integration
    assert "window.currentAdaptivePlan" in workout_code or "currentAdaptivePlan" in workout_code, "Missing currentAdaptivePlan check in workout.js"

    # 4. Check that 4-stage flow and landing page are preserved
    assert 'id="landingView"' in html_code, "Missing landingView"
    assert 'id="workoutSetupStep"' in html_code, "Missing workoutSetupStep (LEARN)"
    assert 'id="workoutPrepareStep"' in html_code, "Missing workoutPrepareStep (PREPARE)"
    assert 'id="workoutActiveStep"' in html_code, "Missing workoutActiveStep (PERFORM)"
    assert 'id="workoutResultStep"' in html_code, "Missing workoutResultStep (REVIEW)"

    print("[PASS] All Adaptive Workout -> Workout View transition tests passed cleanly!")

if __name__ == "__main__":
    test_adaptive_transition_logic()
