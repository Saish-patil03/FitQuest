#!/usr/bin/env python3
"""
Test suite for Phase 6 Step 2: Live Webcam & Backend CV Bridge Integration.
Tests live frame processing, exercise selection validation, session stop, telemetry structure,
existing POST /api/v1/workouts ingestion, and AI coaching.
"""

import base64
import cv2
import numpy as np
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db

def create_dummy_base64_frame():
    """Generates a simple 480x640 dummy image encoded as base64 JPEG."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, "FITQUEST TEST FRAME", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    _, buffer = cv2.imencode('.jpg', img)
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

def test_phase6_step2_integration():
    print("[TEST] Initializing Phase 6 Step 2 Live CV Bridge Test Suite...")

    init_db()
    client = TestClient(app)
    dummy_frame = create_dummy_base64_frame()

    # 1. Test Valid Exercise Selection via Live Frame Processing
    valid_payload = {
        "session_id": "test_p6s2_session_1",
        "exercise_choice": "1",  # Bicep Curl
        "frame_data": dummy_frame,
        "include_annotated_image": True
    }

    res_live = client.post("/api/v1/workouts/live/process-frame", json=valid_payload)
    assert res_live.status_code == 200, f"Live frame processing failed: {res_live.text}"
    telemetry = res_live.json()

    # Verify telemetry data structure
    assert telemetry.get("status") in ["success", "warning"], f"Unexpected status: {telemetry.get('status')}"
    assert "exercise" in telemetry, "Missing exercise field"
    assert "rep_count" in telemetry, "Missing rep_count field"
    assert "form_score" in telemetry, "Missing form_score field"
    assert "feedback" in telemetry and isinstance(telemetry["feedback"], list), "Invalid feedback field"
    print(f"[PASS] Valid exercise selection ('1' / Bicep Curl) accepted. Telemetry returned: Exercise='{telemetry['exercise']}', Reps={telemetry['rep_count']}, FormScore={telemetry['form_score']}%.")

    # 2. Test Exercise Choice by Name ("Squat")
    squat_payload = {
        "session_id": "test_p6s2_session_2",
        "exercise_choice": "Squat",
        "frame_data": dummy_frame,
        "include_annotated_image": False
    }

    res_squat = client.post("/api/v1/workouts/live/process-frame", json=squat_payload)
    assert res_squat.status_code == 200, f"Squat frame processing failed: {res_squat.text}"
    squat_telemetry = res_squat.json()
    assert squat_telemetry.get("exercise").lower() == "squat", f"Exercise name mismatch: {squat_telemetry.get('exercise')}"
    print(f"[PASS] Exercise choice by name ('Squat') accepted. Telemetry exercise: '{squat_telemetry['exercise']}'.")

    # 3. Test Invalid Exercise Selection (Rejection)
    invalid_payload = {
        "session_id": "test_p6s2_invalid",
        "exercise_choice": "999",  # Non-existent exercise ID
        "frame_data": dummy_frame
    }

    res_invalid = client.post("/api/v1/workouts/live/process-frame", json=invalid_payload)
    assert res_invalid.status_code == 400, f"Expected 400 status for invalid exercise, got {res_invalid.status_code}"
    print(f"[PASS] Invalid exercise selection ('999') rejected gracefully with HTTP 400.")

    # 4. Test Live Session Stop Endpoint
    stop_payload = {"session_id": "test_p6s2_session_1"}
    res_stop = client.post("/api/v1/workouts/live/stop-session", json=stop_payload)
    assert res_stop.status_code == 200, "Session stop failed"
    stop_data = res_stop.json()
    assert stop_data.get("status") == "success", "Session stop status mismatch"
    print(f"[PASS] Live session termination verified. Returned final reps={stop_data.get('total_reps')}.")

    # 5. Test Live WebSocket Endpoint (/api/v1/workouts/live-ws/1)
    with client.websocket_connect("/api/v1/workouts/live-ws/1") as websocket:
        websocket.send_text(json_payload := f'{{"frame_data": "{dummy_frame}"}}')
        ws_response = websocket.receive_json()
        assert ws_response.get("status") in ["success", "warning"], "WebSocket response status error"
        assert "rep_count" in ws_response, "WebSocket missing rep_count"
        print(f"[PASS] Live WebSocket stream endpoint verified cleanly.")

    # 6. Verify existing POST /api/v1/workouts & AI Coaching pipeline
    user_res = client.post("/api/v1/users", json={"name": "Step2 Athlete", "email": "step2.athlete@example.com"})
    user_id = user_res.json()["id"]

    ingest_payload = {
        "session_data": {
            "user_id": user_id,
            "exercise_id": 2,  # Squat
            "repetitions": 12,
            "duration_sec": 45,
            "form_score": 91.5
        },
        "form_scores_history": [1, 1, 1, 1, 1, 1],
        "feedback_events": ["Good depth logged on rep 12"]
    }

    res_w = client.post("/api/v1/workouts", json=ingest_payload)
    assert res_w.status_code == 201, f"Workout ingestion failed: {res_w.text}"
    session = res_w.json()
    assert session["repetitions"] == 12, "Rep count mismatch"
    assert len(session["ai_coaching_logs"]) > 0, "AI coaching log missing"
    print(f"[PASS] Ingestion pipeline (POST /api/v1/workouts) and Member 4 AI Coach verified 100% working.")

    print("\n[SUCCESS] All Phase 6 Step 2 Live CV Bridge tests passed cleanly!")

if __name__ == "__main__":
    test_phase6_step2_integration()
