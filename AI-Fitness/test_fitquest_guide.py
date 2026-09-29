"""
Unit and API Integration Tests for FITQUEST GUIDE™
Tests the dedicated in-app help chatbot, scope enforcement, feature explanations, and navigation intents.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.guide_service import fitquest_guide_service

client = TestClient(app)

def test_guide_chat_endpoint_feature_query():
    """Test asking a standard platform feature query via API."""
    response = client.post("/api/v1/guide/chat", json={
        "message": "What does FitQuest provide?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "FitQuest" in data["reply"]
    assert "Workout" in data["reply"] or "Movement DNA" in data["reply"]

def test_guide_chat_movement_dna_query():
    """Test asking specifically about Movement DNA."""
    response = client.post("/api/v1/guide/chat", json={
        "message": "What is Movement DNA?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Movement DNA" in data["reply"]
    assert "Stability" in data["reply"] or "Symmetry" in data["reply"] or "biomechanical" in data["reply"]
    assert data["nav_suggestion"] == "movementDnaView"

def test_guide_chat_nutrition_query():
    """Test asking about Nutrition."""
    response = client.post("/api/v1/guide/chat", json={
        "message": "What is FitQuest Nutrition?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Nutrition" in data["reply"]
    assert "meal plan" in data["reply"].lower() or "calorie" in data["reply"].lower() or "macro" in data["reply"].lower()
    assert data["nav_suggestion"] == "nutritionView"

def test_guide_chat_readiness_query():
    """Test asking about Readiness Score."""
    response = client.post("/api/v1/guide/chat", json={
        "message": "What does my Readiness Score mean?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Readiness" in data["reply"]

def test_guide_chat_start_workout_query():
    """Test asking how to start a workout."""
    response = client.post("/api/v1/guide/chat", json={
        "message": "How do I start a workout?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Workout" in data["reply"]
    assert "Step A" in data["reply"] or "exercise" in data["reply"].lower()
    assert data["nav_suggestion"] == "workoutView"

def test_guide_chat_scope_redirect_to_ai_coach():
    """Test strict scope gate redirecting fitness coaching questions to AI Coach."""
    coaching_questions = [
        "How many squats should I do today?",
        "What should I eat to build muscle?",
        "Can you create a workout routine for my chest?",
        "My knee hurts when I squat, what should I do?"
    ]
    for q in coaching_questions:
        response = client.post("/api/v1/guide/chat", json={"message": q})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "AI Coach" in data["reply"]
        assert data["nav_suggestion"] == "aiCoachView"
        assert data["provider"] == "FitQuest Guide Scope Gate"

def test_guide_chat_scope_reject_out_of_domain():
    """Test strict scope gate rejecting general-purpose off-topic questions."""
    off_topic_questions = [
        "Tell me a joke.",
        "What is the capital of France?",
        "Who was the first president of the United States?",
        "Write Python code to sort a list."
    ]
    for q in off_topic_questions:
        response = client.post("/api/v1/guide/chat", json={"message": q})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "FitQuest Guide" in data["reply"]
        assert data["provider"] == "FitQuest Guide Scope Gate"

def test_guide_chat_context_awareness():
    """Test context-aware query when user is on a specific view."""
    # When on movementDnaView
    res1 = client.post("/api/v1/guide/chat", json={
        "message": "What am I looking at?",
        "current_view": "movementDnaView"
    })
    assert res1.status_code == 200
    assert "Movement DNA" in res1.json()["reply"]

    # When on nutritionView
    res2 = client.post("/api/v1/guide/chat", json={
        "message": "What does this mean?",
        "current_view": "nutritionView"
    })
    assert res2.status_code == 200
    assert "Nutrition" in res2.json()["reply"]

    # When on workoutView
    res3 = client.post("/api/v1/guide/chat", json={
        "message": "Explain this page",
        "current_view": "workoutView"
    })
    assert res3.status_code == 200
    assert "Workout" in res3.json()["reply"]

def test_guide_chat_navigation_intent():
    """Test direct navigation intents."""
    nav_tests = [
        ("Take me to Analytics", "progressView"),
        ("Open Movement DNA", "movementDnaView"),
        ("Go to Workout", "workoutView"),
        ("Show me history", "historyView"),
        ("Go to Nutrition", "nutritionView")
    ]
    for msg, expected_target in nav_tests:
        response = client.post("/api/v1/guide/chat", json={"message": msg})
        assert response.status_code == 200
        data = response.json()
        assert data["nav_action"] == expected_target

def test_guide_chat_alias_endpoint():
    """Test the alias endpoint /api/v1/fitquest-guide/chat."""
    response = client.post("/api/v1/fitquest-guide/chat", json={
        "message": "What is Movement Copilot?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Movement Copilot" in data["reply"]
