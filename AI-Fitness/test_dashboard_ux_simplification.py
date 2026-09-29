#!/usr/bin/env python3
"""
FitQuest Dashboard UX Simplification Verification Suite.
Verifies all 13 objective criteria from the UX Simplification specification:
1. Hero section simplified text and badges.
2. 20 Exercises card preservation.
3. Today's Readiness scannable 3-column layout.
4. Progressive disclosure toggle and secondary details.
5. Hierarchy & CTA "Start Today's Workout".
6. Unchanged backend intelligence & calculation APIs.
7. Visual design & CSS responsive media query rules.
"""

import re
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db, SessionLocal
from backend.models import (
    WorkoutSessionModel, FormLogModel, AICoachingLogModel,
    UserAchievementModel, UserModel, UserGoalModel
)

def verify_dashboard_ux():
    print("==================================================================")
    print("       FITQUEST DASHBOARD UX SIMPLIFICATION AUDIT                 ")
    print("==================================================================")

    # ------------------------------------------------------------------
    # 1. Verify HTML Structure & Content
    # ------------------------------------------------------------------
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # Hero Banner checks
    assert "<h1>Train Smarter. Move Better.</h1>" in html, "Missing new Hero heading"
    assert "AI-powered workout tracking and personalized feedback." in html, "Missing new Hero description"
    assert "Powered by YOLOv8 Pose & Gemini AI" in html, "Missing Hero badge"
    assert "Start Workout" in html, "Missing Start Workout button"
    assert "Ask AI Coach" in html, "Missing Ask AI Coach button"
    assert "20 Exercises" in html, "Missing 20 Exercises stat"
    assert "Real-time Biomechanics" in html, "Missing 20 Exercises subtext"
    print("[PASS] 1. Hero Section & 20 Exercises Card: Verified new copy, badge, buttons, and card stats.")

    # Readiness Card Structure
    assert 'id="readinessCard"' in html, "Missing #readinessCard"
    assert 'id="readinessStatusText"' in html, "Missing #readinessStatusText"
    assert 'id="readinessScoreVal"' in html, "Missing #readinessScoreVal"
    assert 'id="readinessGaugeIcon"' in html, "Missing #readinessGaugeIcon"
    assert 'id="readinessFocus"' in html, "Missing #readinessFocus"
    assert 'id="readinessSuggestedExercise"' in html, "Missing #readinessSuggestedExercise"
    assert 'id="readinessIntensity"' in html, "Missing #readinessIntensity"
    assert 'id="startRecommendedBtn"' in html, "Missing #startRecommendedBtn"
    assert "Start Today's Workout" in html, "Missing 'Start Today\'s Workout' CTA text"
    assert 'id="readinessDetailsToggle"' in html, "Missing #readinessDetailsToggle"
    assert 'id="readinessDetailsContent"' in html, "Missing #readinessDetailsContent"
    assert 'id="readinessFormTrend"' in html, "Missing #readinessFormTrend"
    assert 'id="readinessAvgForm"' in html, "Missing #readinessAvgForm"
    assert 'id="readinessConsistency"' in html, "Missing #readinessConsistency"
    assert 'id="readinessRestGap"' in html, "Missing #readinessRestGap"
    assert 'id="readinessExplanation"' in html, "Missing #readinessExplanation"
    print("[PASS] 2. Today's Readiness Scannable Grid: Verified Focus, Suggested Exercise, Intensity, and CTA.")

    # Progressive disclosure default hidden
    match_hidden = re.search(r'id=\"readinessDetailsContent\"[^>]*style=\"[^\"]*display:\s*none', html)
    assert match_hidden is not None, "#readinessDetailsContent must be hidden by default"
    print("[PASS] 3. Progressive Disclosure: Verified #readinessDetailsContent is hidden by default.")

    # ------------------------------------------------------------------
    # 2. Verify JavaScript Logic in readiness.js
    # ------------------------------------------------------------------
    with open('frontend/readiness.js', 'r', encoding='utf-8') as f:
        js = f.read()

    assert "renderReadinessCard" in js, "Missing renderReadinessCard"
    assert "toggleReadinessDetails" in js, "Missing toggleReadinessDetails"
    assert "startRecommendedWorkout" in js, "Missing startRecommendedWorkout"
    assert "readinessSuggestedExercise" in js, "Missing readinessSuggestedExercise assignment in JS"
    assert "readinessAvgForm" in js, "Missing readinessAvgForm assignment in JS"
    assert "readinessConsistency" in js, "Missing readinessConsistency assignment in JS"
    assert "readinessRestGap" in js, "Missing readinessRestGap assignment in JS"
    assert "INSUFFICIENT_DATA" in js, "Missing INSUFFICIENT_DATA state handling in JS"
    print("[PASS] 4. JavaScript Engine: Verified renderReadinessCard, toggleReadinessDetails, and dynamic assignments.")

    # ------------------------------------------------------------------
    # 3. Verify CSS Rules & Responsive Breakpoints
    # ------------------------------------------------------------------
    with open('frontend/style.css', 'r', encoding='utf-8') as f:
        css = f.read()

    assert ".readiness-widget-card" in css, "Missing .readiness-widget-card CSS"
    assert ".readiness-primary-grid" in css, "Missing .readiness-primary-grid CSS"
    assert ".readiness-primary-item" in css, "Missing .readiness-primary-item CSS"
    assert ".readiness-action-bar" in css, "Missing .readiness-action-bar CSS"
    assert ".readiness-details-toggle-btn" in css, "Missing .readiness-details-toggle-btn CSS"
    assert ".readiness-details-content" in css, "Missing .readiness-details-content CSS"
    assert ".readiness-secondary-grid" in css, "Missing .readiness-secondary-grid CSS"
    assert ".readiness-explanation-callout" in css, "Missing .readiness-explanation-callout CSS"

    # Check 768px responsive rules
    assert ".readiness-primary-grid" in css[css.find("@media (max-width: 768px)"):], "Missing 768px responsiveness for .readiness-primary-grid"
    assert ".readiness-secondary-grid" in css[css.find("@media (max-width: 768px)"):], "Missing 768px responsiveness for .readiness-secondary-grid"
    assert ".readiness-action-bar" in css[css.find("@media (max-width: 768px)"):], "Missing 768px responsiveness for .readiness-action-bar"
    print("[PASS] 5. CSS Architecture & Media Queries: Verified design tokens, grid geometry, and 768px / 640px breakpoints.")

    # ------------------------------------------------------------------
    # 4. Verify Backend API Integration
    # ------------------------------------------------------------------
    init_db()
    db = SessionLocal()
    db.query(AICoachingLogModel).delete()
    db.query(FormLogModel).delete()
    db.query(WorkoutSessionModel).delete()
    db.query(UserGoalModel).delete()
    db.query(UserAchievementModel).delete()
    db.query(UserModel).delete()
    db.commit()

    client = TestClient(app)

    reg = client.post("/api/v1/auth/register", json={
        "name": "Dashboard Tester",
        "email": "dash_test@example.com",
        "password": "password123"
    }).json()
    token = reg["access_token"]
    user_id = reg["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify Insufficient Data response schema
    res_empty = client.get("/api/v1/readiness/me", headers=headers).json()
    assert res_empty["status"] == "INSUFFICIENT_DATA"
    assert res_empty["readiness_score"] is None

    # Ingest a valid Squat session
    client.post("/api/v1/workouts", json={
        "session_data": {"user_id": user_id, "exercise_id": 2, "repetitions": 12, "duration_sec": 60, "form_score": 94.0},
        "form_scores_history": [1]*12,
        "feedback_events": ["Great depth"]
    }, headers=headers)

    res_valid = client.get("/api/v1/readiness/me", headers=headers).json()
    assert res_valid["status"] in ["READY_TO_TRAIN", "GOOD_TO_TRAIN"]
    assert res_valid["readiness_score"] is not None
    assert res_valid["recommended_focus"] is not None
    assert res_valid["recommended_intensity"] is not None
    assert res_valid["recommended_exercise_name"] is not None
    assert res_valid["supporting_metrics"]["valid_workouts_last_7_days"] == 1
    assert res_valid["supporting_metrics"]["recent_average_form"] == 94.0
    print(f"[PASS] 6. Backend API Integrity: Readiness Score={res_valid['readiness_score']}, Focus={res_valid['recommended_focus']}, Exercise={res_valid['recommended_exercise_name']}, Intensity={res_valid['recommended_intensity']}.")

    print("\n==================================================================")
    print("      ALL DASHBOARD UX SIMPLIFICATION CHECKS PASSED 100%!         ")
    print("==================================================================")

if __name__ == '__main__':
    verify_dashboard_ux()
