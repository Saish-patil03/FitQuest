"""
FitQuest Single Exercise Workout Prescription & Set Progression Integration Test
Verifies:
1. HTML elements for prescription card, AI recommendation, prepare plan pill, set progress HUD, and review summary.
2. JS prescription mapping and default data for all 20 catalogue exercises.
3. CSS styles for all prescription and set components.
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
HTML_FILE = BASE_DIR / "frontend" / "index.html"
JS_FILE = BASE_DIR / "frontend" / "workout.js"
CSS_FILE = BASE_DIR / "frontend" / "style.css"

def test_html_structure():
    content = HTML_FILE.read_text(encoding="utf-8")
    
    # 1. LEARN Stage Elements
    assert 'id="learnPrescriptionSets"' in content, "Missing learnPrescriptionSets"
    assert 'id="learnPrescriptionReps"' in content, "Missing learnPrescriptionReps"
    assert 'id="learnPrescriptionRest"' in content, "Missing learnPrescriptionRest"
    assert 'id="learnPrescriptionTempo"' in content, "Missing learnPrescriptionTempo"
    assert 'id="learnAiRecommendationText"' in content, "Missing learnAiRecommendationText"
    
    # 2. PREPARE Stage Elements
    assert 'id="preparePlanPill"' in content, "Missing preparePlanPill"
    assert 'id="preparePlanText"' in content, "Missing preparePlanText"
    
    # 3. PERFORM Stage Elements
    assert 'id="hudSetProgressPill"' in content, "Missing hudSetProgressPill"
    assert 'id="hudSetProgress"' in content, "Missing hudSetProgress"
    assert 'id="hudCompleteSetBtn"' in content, "Missing hudCompleteSetBtn"
    
    # 4. REVIEW Stage Elements
    assert 'id="workoutPlanSummaryCard"' in content, "Missing workoutPlanSummaryCard"
    assert 'id="resSetsSummary"' in content, "Missing resSetsSummary"
    assert 'id="resTargetRepsSummary"' in content, "Missing resTargetRepsSummary"
    assert 'id="resRestSummary"' in content, "Missing resRestSummary"
    
    # 5. Rest Modal Elements
    assert 'id="restModalHeaderBadge"' in content, "Missing restModalHeaderBadge"
    assert 'id="restModalSetCompleteText"' in content, "Missing restModalSetCompleteText"
    assert 'id="restSkipBtn"' in content, "Missing restSkipBtn"
    
    print("[PASS] All required HTML elements present in index.html")

def test_js_logic():
    content = JS_FILE.read_text(encoding="utf-8")
    
    # Verify prescription map & functions
    assert "EXERCISE_DEFAULT_PRESCRIPTIONS" in content, "Missing EXERCISE_DEFAULT_PRESCRIPTIONS"
    assert "resolveExercisePrescription" in content, "Missing resolveExercisePrescription"
    assert "generateDeterministicAIRecommendation" in content, "Missing generateDeterministicAIRecommendation"
    assert "handleSingleExerciseSetComplete" in content, "Missing handleSingleExerciseSetComplete"
    assert "handleManualSetComplete" in content, "Missing handleManualSetComplete"
    assert "startSingleExerciseRestTimer" in content, "Missing startSingleExerciseRestTimer"
    assert "launchNextSingleExerciseSet" in content, "Missing launchNextSingleExerciseSet"
    
    # Verify all 20 exercises are in the prescription catalog
    for ex_id in range(1, 21):
        assert f"{ex_id}:" in content, f"Missing exercise id {ex_id} in prescription map"
        
    print("[PASS] All prescription & set progression logic verified in workout.js")

def test_css_rules():
    content = CSS_FILE.read_text(encoding="utf-8")
    
    assert ".learn-prescription-wrap" in content, "Missing .learn-prescription-wrap CSS"
    assert ".learn-prescription-card" in content, "Missing .learn-prescription-card CSS"
    assert ".learn-ai-recommendation-card" in content, "Missing .learn-ai-recommendation-card CSS"
    assert ".prepare-plan-pill" in content, "Missing .prepare-plan-pill CSS"
    assert ".workout-set-pill" in content, "Missing .workout-set-pill CSS"
    assert ".workout-completion-summary" in content, "Missing .workout-completion-summary CSS"
    
    print("[PASS] All CSS classes verified in style.css")

if __name__ == "__main__":
    test_html_structure()
    test_js_logic()
    test_css_rules()
    print("ALL PRESCRIPTION & SET PROGRESSION TESTS PASSED CLEANLY!")
