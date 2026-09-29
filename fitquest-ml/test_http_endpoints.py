import sys
import json
import base64
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "http://127.0.0.1:8100"

def test_endpoints():
    print(f"Connecting to live ML service at {BASE_URL}...")

    # Wait for server to become ready
    ready = False
    for attempt in range(10):
        try:
            req = urllib.request.Request(f"{BASE_URL}/health")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.5)

    if not ready:
        print("[FAIL] Server did not become ready in time!")
        sys.exit(1)

    print("[PASS] ML Service is UP and responding to HTTP requests!")

    # 1. Health check
    req = urllib.request.Request(f"{BASE_URL}/health")
    with urllib.request.urlopen(req) as resp:
        health = json.loads(resp.read().decode("utf-8"))
        print(f"[PASS] GET /health: {health}")
        assert health["status"] == "ok"
        assert health["service"] == "FitQuest ML Engine"

    # 2. Start session
    session_id = "http_test_sess_42"
    start_payload = json.dumps({"session_id": session_id, "exercise_choice": "2"}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/live/start-session",
        data=start_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        start_res = json.loads(resp.read().decode("utf-8"))
        print(f"[PASS] POST /live/start-session: {start_res}")
        assert start_res["status"] == "success"
        assert start_res["exercise"] == "Squat"

    # 3. Process frame
    import ultralytics
    img_path = Path(ultralytics.__file__).parent / "assets" / "zidane.jpg"
    with open(img_path, "rb") as f:
        img_b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")

    process_payload = json.dumps({
        "session_id": session_id,
        "exercise_choice": "2",
        "frame_data": img_b64,
        "include_annotated_image": True
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/live/process-frame",
        data=process_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        frame_res = json.loads(resp.read().decode("utf-8"))
        print(f"[PASS] POST /live/process-frame status: {frame_res['status']}")
        print(f"       Exercise: {frame_res['exercise']}")
        print(f"       Rep Count: {frame_res['rep_count']}")
        print(f"       Primary Angle: {frame_res['primary_angle']}")
        print(f"       Feedback: {frame_res['feedback']}")
        print(f"       Annotated Frame returned: {bool(frame_res.get('annotated_frame'))}")
        assert frame_res["status"] == "success"
        assert frame_res["exercise"] == "Squat"

    # 4. Stop session
    stop_payload = json.dumps({"session_id": session_id}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/live/stop-session",
        data=stop_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        stop_res = json.loads(resp.read().decode("utf-8"))
        print(f"[PASS] POST /live/stop-session: {stop_res['status']}, exercise: {stop_res.get('exercise')}")
        assert stop_res["status"] == "success"
        assert stop_res["exercise"] == "Squat"
        assert "movement_intelligence" in stop_res

    # 5. Compatibility routes: /workouts/live/*
    print("\n--- Testing Compatibility Routes (/workouts/live/*) ---")
    c_session_id = "http_compat_sess_88"
    c_start_payload = json.dumps({"session_id": c_session_id, "exercise_choice": "1"}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/workouts/live/start-session",
        data=c_start_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        c_start_res = json.loads(resp.read().decode("utf-8"))
        print(f"[PASS] POST /workouts/live/start-session: {c_start_res}")
        assert c_start_res["status"] == "success"
        assert c_start_res["exercise"] == "Bicep Curl"

    c_process_payload = json.dumps({
        "session_id": c_session_id,
        "exercise_choice": "1",
        "frame_data": img_b64,
        "include_annotated_image": True
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/workouts/live/process-frame",
        data=c_process_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        c_frame_res = json.loads(resp.read().decode("utf-8"))
        print(f"[PASS] POST /workouts/live/process-frame: status={c_frame_res['status']}, angle={c_frame_res.get('primary_angle')}")
        assert c_frame_res["status"] == "success"
        assert c_frame_res["exercise"] == "Bicep Curl"
        assert c_frame_res.get("primary_angle") is not None

    c_stop_payload = json.dumps({"session_id": c_session_id}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/workouts/live/stop-session",
        data=c_stop_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        c_stop_res = json.loads(resp.read().decode("utf-8"))
        print(f"[PASS] POST /workouts/live/stop-session: {c_stop_res['status']}, exercise: {c_stop_res.get('exercise')}")
        assert c_stop_res["status"] == "success"
        assert c_stop_res["exercise"] == "Bicep Curl"
        assert "movement_intelligence" in c_stop_res

    print("\n[SUCCESS] All HTTP endpoints verified over live network socket (port 8100)!")

if __name__ == "__main__":
    test_endpoints()
