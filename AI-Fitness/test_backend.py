#!/usr/bin/env python3
"""
Test suite for Phase 4 Step 2 FastAPI Backend Foundation.
"""

import sys
from fastapi.testclient import TestClient
from backend.main import app

def test_backend_foundation():
    print("[TEST] Initializing FastAPI Backend Foundation test...")

    client = TestClient(app)

    # 1. Test Root Endpoint
    res_root = client.get("/")
    assert res_root.status_code == 200, f"Expected 200, got {res_root.status_code}"
    data_root = res_root.json()
    assert data_root.get("status") == "running", "Root status mismatch"
    assert data_root.get("service") == "AI Fitness Backend", "Service name mismatch"
    print("[PASS] GET / root endpoint verified.")

    # 2. Test Health Endpoint
    res_health = client.get("/health")
    assert res_health.status_code == 200, f"Expected 200, got {res_health.status_code}"
    assert res_health.json() == {"status": "ok", "service": "AI Fitness Backend"}, "Health response mismatch"
    print("[PASS] GET /health endpoint verified.")

    # 3. Test Users Router
    res_users = client.get("/api/v1/users")
    assert res_users.status_code == 200, f"Expected 200, got {res_users.status_code}"
    assert isinstance(res_users.json(), list), "Users API should return a list"
    print("[PASS] GET /api/v1/users endpoint verified.")

    # 4. Test Exercises Router
    res_exercises = client.get("/api/v1/exercises")
    assert res_exercises.status_code == 200, f"Expected 200, got {res_exercises.status_code}"
    assert isinstance(res_exercises.json(), list), "Exercises API should return a list"
    print("[PASS] GET /api/v1/exercises endpoint verified.")

    # 5. Test Workouts Router (404 for non-existent session)
    res_workouts = client.get("/api/v1/workouts/99999")
    assert res_workouts.status_code == 404, f"Expected 404, got {res_workouts.status_code}"
    print("[PASS] GET /api/v1/workouts/{id} endpoint verified.")

    # 6. Test AI Router (Standalone Q&A endpoint)
    res_ai = client.post("/api/v1/ai/qa", json={"question": "Form tip for squats?"})
    assert res_ai.status_code == 200, f"Expected 200, got {res_ai.status_code}"
    assert res_ai.json().get("status") == "success", "AI API status mismatch"
    print("[PASS] POST /api/v1/ai/qa endpoint verified.")

    print("\n[SUCCESS] All FastAPI Backend Foundation tests passed cleanly!")

if __name__ == "__main__":
    test_backend_foundation()
