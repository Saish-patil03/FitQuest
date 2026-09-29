import sys
import base64
from pathlib import Path
import cv2
from fastapi.testclient import TestClient

# Ensure app package is accessible
sys.path.insert(0, str(Path(__file__).resolve().parent / "app"))

from main import app
from cv_service import cv_live_service

def run_tests():
    client = TestClient(app)
    results = {}

    print("==================================================")
    print("STARTING FITQUEST ML SERVICE VERIFICATION SUITE")
    print("==================================================")

    # Test 1: GET /health
    print("\n--- Test 1: GET /health ---")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    health_data = resp.json()
    assert health_data["status"] == "ok"
    assert health_data["service"] == "FitQuest ML Engine"
    print(f"[PASS] Health response: {health_data}")
    results["health"] = "PASS"

    # Test 2: Start Session with valid exercise
    print("\n--- Test 2: POST /live/start-session (valid exercise: Bicep Curl / 1) ---")
    session_id = "test_session_001"
    resp = client.post("/live/start-session", json={
        "session_id": session_id,
        "exercise_choice": "1"
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    start_data = resp.json()
    assert start_data["status"] == "success"
    assert start_data["session_id"] == session_id
    assert start_data["exercise"] == "Bicep Curl"
    assert start_data["rep_count"] == 0
    assert "form_score" in start_data
    print(f"[PASS] Start session response: {start_data}")
    results["start_session"] = "PASS"

    # Test 3: Invalid exercise selection
    print("\n--- Test 3: POST /live/start-session (invalid exercise) ---")
    bad_resp = client.post("/live/start-session", json={
        "session_id": "bad_session",
        "exercise_choice": "999_invalid_exercise"
    })
    assert bad_resp.status_code == 400, f"Expected 400, got {bad_resp.status_code}: {bad_resp.text}"
    print(f"[PASS] Invalid exercise rejected correctly with 400: {bad_resp.json()}")
    results["invalid_exercise"] = "PASS"

    # Test 4: Real JPEG Frame Processing & YOLO Inference
    print("\n--- Test 4: POST /live/process-frame (real image: zidane.jpg) ---")
    # Load actual image from site-packages
    test_img_path = Path(sys.prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "ultralytics" / "assets" / "zidane.jpg"
    if not test_img_path.exists():
        # Fallback search
        import ultralytics
        test_img_path = Path(ultralytics.__file__).parent / "assets" / "zidane.jpg"

    assert test_img_path.exists(), f"Test image not found at {test_img_path}"
    with open(test_img_path, "rb") as f:
        img_bytes = f.read()

    b64_frame = "data:image/jpeg;base64," + base64.b64encode(img_bytes).decode("utf-8")

    process_payload = {
        "session_id": session_id,
        "exercise_choice": "1",
        "frame_data": b64_frame,
        "include_annotated_image": True
    }

    resp = client.post("/live/process-frame", json=process_payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    frame_data = resp.json()
    print(f"[PASS] Frame processing status: {frame_data.get('status')}")
    print(f"       Exercise: {frame_data.get('exercise')}")
    print(f"       Rep Count: {frame_data.get('rep_count')}")
    print(f"       State: {frame_data.get('state')}")
    print(f"       Primary Angle: {frame_data.get('primary_angle')}")
    print(f"       Form Score: {frame_data.get('form_score')}")
    print(f"       Feedback Code: {frame_data.get('feedback_code')}")
    print(f"       Feedback Detail: {frame_data.get('feedback_detail')}")
    print(f"       Feedback Priority: {frame_data.get('feedback_priority')}")
    print(f"       Valid: {frame_data.get('valid')}")
    print(f"       Annotated Frame returned: {bool(frame_data.get('annotated_frame'))}")

    assert frame_data["status"] == "success"
    assert frame_data["exercise"] == "Bicep Curl"
    assert "rep_count" in frame_data
    assert "state" in frame_data
    assert "feedback_code" in frame_data
    assert frame_data["annotated_frame"] is not None
    assert frame_data["annotated_frame"].startswith("data:image/jpeg;base64,")
    results["frame_processing"] = "PASS"
    results["yolo_inference"] = "PASS"
    results["telemetry"] = "PASS"
    results["annotated_frame"] = "PASS"

    # Test 5: Session State Persistence Across Frames & Rep Continuity
    print("\n--- Test 5: Session State Persistence Across Frames & Rep Continuity ---")
    # Simulate rep count progression to verify it does not reset
    ctrl = cv_live_service.active_sessions[session_id]
    ctrl.tracker.rep_count = 3
    
    # Feed 2 more sequential frames to verify session state is maintained
    for i in range(2, 4):
        resp_seq = client.post("/live/process-frame", json=process_payload)
        assert resp_seq.status_code == 200
        seq_data = resp_seq.json()
        assert seq_data["status"] == "success"
        assert seq_data["rep_count"] >= 3, f"Rep count unexpectedly reset! Expected >= 3, got {seq_data['rep_count']}"
        print(f"[PASS] Sequential Frame {i} processed in session {session_id} with rep_count={seq_data['rep_count']}")

    # Verify controller is still in active_sessions and buffer has samples
    assert session_id in cv_live_service.active_sessions
    assert session_id in cv_live_service.session_buffers
    sample_count = len(cv_live_service.session_buffers[session_id].samples)
    print(f"[PASS] Session buffer accumulated {sample_count} telemetry samples")
    assert sample_count >= 3
    results["session_persistence"] = "PASS"

    # Test 6: Stop Session
    print("\n--- Test 6: POST /live/stop-session ---")
    stop_resp = client.post("/live/stop-session", json={"session_id": session_id})
    assert stop_resp.status_code == 200, f"Expected 200, got {stop_resp.status_code}: {stop_resp.text}"
    stop_data = stop_resp.json()
    assert stop_data["status"] == "success"
    assert stop_data["exercise"] == "Bicep Curl"
    assert "total_reps" in stop_data
    assert "duration_sec" in stop_data
    assert "form_score" in stop_data
    assert "movement_intelligence" in stop_data
    print(f"[PASS] Stop session response: {stop_data}")
    results["stop_session"] = "PASS"

    # Test 7: Session Cleanup
    print("\n--- Test 7: Session Memory Cleanup ---")
    assert session_id not in cv_live_service.active_sessions, "Session not purged from active_sessions!"
    assert session_id not in cv_live_service.session_buffers, "Session not purged from session_buffers!"
    print(f"[PASS] Session '{session_id}' cleanly removed from active_sessions and session_buffers.")

    # Calling stop-session again should return 'No active session found'
    stop_again_resp = client.post("/live/stop-session", json={"session_id": session_id})
    assert stop_again_resp.status_code == 200
    stop_again_data = stop_again_resp.json()
    assert stop_again_data["status"] == "info"
    assert stop_again_data["message"] == "No active session found"
    print(f"[PASS] Repeat stop-session returns expected info message: {stop_again_data}")
    # Test 8: /workouts/live/* Compatibility Routes
    print("\n--- Test 8: /workouts/live/* Compatibility Routes Parity ---")
    compat_sess_id = "compat_session_99"
    # 8a: Start Session via /workouts/live/start-session
    c_start_resp = client.post("/workouts/live/start-session", json={
        "session_id": compat_sess_id,
        "exercise_choice": "1"
    })
    assert c_start_resp.status_code == 200, f"Expected 200, got {c_start_resp.status_code}: {c_start_resp.text}"
    c_start_data = c_start_resp.json()
    assert c_start_data["status"] == "success"
    assert c_start_data["exercise"] == "Bicep Curl"
    print(f"[PASS] /workouts/live/start-session: {c_start_data}")

    # 8b: Process Frame via /workouts/live/process-frame
    c_frame_resp = client.post("/workouts/live/process-frame", json={
        "session_id": compat_sess_id,
        "exercise_choice": "1",
        "frame_data": b64_frame,
        "include_annotated_image": True
    })
    assert c_frame_resp.status_code == 200, f"Expected 200, got {c_frame_resp.status_code}: {c_frame_resp.text}"
    c_frame_data = c_frame_resp.json()
    assert c_frame_data["status"] == "success"
    assert c_frame_data["exercise"] == "Bicep Curl"
    assert c_frame_data["primary_angle"] == 130.8
    assert c_frame_data["feedback_code"] == "ELBOW_MISALIGNED"
    assert c_frame_data["annotated_frame"] is not None
    print(f"[PASS] /workouts/live/process-frame: angle={c_frame_data['primary_angle']}, feedback={c_frame_data['feedback_code']}")

    # 8c: Stop Session via /workouts/live/stop-session
    c_stop_resp = client.post("/workouts/live/stop-session", json={"session_id": compat_sess_id})
    assert c_stop_resp.status_code == 200, f"Expected 200, got {c_stop_resp.status_code}: {c_stop_resp.text}"
    c_stop_data = c_stop_resp.json()
    assert c_stop_data["status"] == "success"
    assert c_stop_data["exercise"] == "Bicep Curl"
    assert "movement_intelligence" in c_stop_data
    print(f"[PASS] /workouts/live/stop-session: status={c_stop_data['status']}, exercise={c_stop_data['exercise']}")
    results["compatibility_routes"] = "PASS"

    print("\n==================================================")
    print("ALL ML SERVICE TESTS PASSED SUCCESSFULLY!")
    print("==================================================")
    return results

if __name__ == "__main__":
    run_tests()
