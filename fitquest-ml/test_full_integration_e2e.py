import sys
import json
import base64
import time
import urllib.request
import urllib.error
from pathlib import Path

BACKEND_BASE = "http://127.0.0.1:8000/api/v1"
ML_BASE = "http://127.0.0.1:8100"

def run_integration_test():
    print("==================================================================")
    print("      FITQUEST DUAL-SERVICE LOCAL INTEGRATION VERIFICATION        ")
    print("==================================================================")

    # 1. Health Checks
    print("\n--- 1. Health Checks ---")
    with urllib.request.urlopen("http://127.0.0.1:8000/health") as resp:
        b_health = json.loads(resp.read().decode())
        print(f"[PASS] Backend health: {b_health}")
        assert b_health["status"] == "ok"

    with urllib.request.urlopen("http://127.0.0.1:8100/health") as resp:
        m_health = json.loads(resp.read().decode())
        print(f"[PASS] ML Service health: {m_health}")
        assert m_health["status"] == "ok"

    # 2. CORS Checks
    print("\n--- 2. CORS Preflight & Origin Header Verification ---")
    origin = "http://127.0.0.1:8000"
    cors_req = urllib.request.Request(
        f"{ML_BASE}/workouts/live/start-session",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        },
        method="OPTIONS"
    )
    with urllib.request.urlopen(cors_req) as resp:
        allow_origin = resp.headers.get("Access-Control-Allow-Origin")
        print(f"[PASS] ML Service CORS Allow-Origin for {origin}: {allow_origin}")
        assert allow_origin in [origin, "*"], f"CORS origin mismatch: {allow_origin}"

    # 3. Backend Normal APIs: User Login & Setup
    print("\n--- 3. Backend User Authentication & Setup (Port 8000) ---")
    email = "integration_runner@example.com"
    password = "TestPassword123!"
    auth_token = None
    try:
        req = urllib.request.Request(
            f"{BACKEND_BASE}/auth/login",
            data=json.dumps({"email": email, "password": password}).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            auth_token = json.loads(resp.read().decode())["access_token"]
            print(f"[PASS] Logged in user: {email}")
    except urllib.error.HTTPError:
        req = urllib.request.Request(
            f"{BACKEND_BASE}/auth/register",
            data=json.dumps({
                "name": "Integration Athlete",
                "email": email,
                "password": password,
                "fitness_goal": "Hypertrophy",
                "experience_level": "Intermediate"
            }).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            auth_token = json.loads(resp.read().decode())["access_token"]
            print(f"[PASS] Registered user: {email}")

    auth_headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

    # Verify /exercises on Backend
    req = urllib.request.Request(f"{BACKEND_BASE}/exercises")
    with urllib.request.urlopen(req) as resp:
        exercises = json.loads(resp.read().decode())
        print(f"[PASS] Backend /exercises returned {len(exercises)} exercises")
        assert len(exercises) == 20

    # 4. Live CV Session on ML Service (Port 8100)
    print("\n--- 4. Live CV Flow Dispatched to ML Service (Port 8100) ---")
    session_id = f"integration_live_sess_{int(time.time())}"
    
    # 4a. Start Session
    start_req = urllib.request.Request(
        f"{ML_BASE}/workouts/live/start-session",
        data=json.dumps({"session_id": session_id, "exercise_choice": "1"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(start_req) as resp:
        start_res = json.loads(resp.read().decode())
        print(f"[PASS] ML /workouts/live/start-session: {start_res}")
        assert start_res["status"] == "success"
        assert start_res["exercise"] == "Bicep Curl"

    # 4b. Send Frames to ML Service
    import ultralytics
    img_path = Path(ultralytics.__file__).parent / "assets" / "zidane.jpg"
    with open(img_path, "rb") as f:
        img_b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()

    for f_idx in range(1, 4):
        frame_req = urllib.request.Request(
            f"{ML_BASE}/workouts/live/process-frame",
            data=json.dumps({
                "session_id": session_id,
                "exercise_choice": "1",
                "frame_data": img_b64,
                "include_annotated_image": True
            }).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(frame_req) as resp:
            frame_res = json.loads(resp.read().decode())
            print(f"[PASS] Frame {f_idx} processed by ML service: angle={frame_res.get('primary_angle')}, rep_count={frame_res.get('rep_count')}")
            assert frame_res["status"] == "success"

    # 4c. Stop Session on ML Service
    stop_req = urllib.request.Request(
        f"{ML_BASE}/workouts/live/stop-session",
        data=json.dumps({"session_id": session_id}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(stop_req) as resp:
        stop_res = json.loads(resp.read().decode())
        print(f"[PASS] ML /workouts/live/stop-session: status={stop_res['status']}, duration={stop_res['duration_sec']}s")
        assert stop_res["status"] == "success"
        movement_intel = stop_res.get("movement_intelligence")
        assert movement_intel is not None

    # 5. Ingest Workout Session on Backend (Port 8000)
    print("\n--- 5. Workout Ingestion & AI Coaching Hand-off to Backend (Port 8000) ---")
    ingest_payload = {
        "session_data": {
            "exercise_id": 1,
            "repetitions": 10,
            "duration_sec": 45,
            "form_score": 92.0
        },
        "form_scores_history": [90, 92, 94],
        "feedback_events": ["Elbow aligned", "Controlled eccentric"],
        "movement_intelligence": movement_intel
    }
    ingest_req = urllib.request.Request(
        f"{BACKEND_BASE}/workouts",
        data=json.dumps(ingest_payload).encode(),
        headers=auth_headers
    )
    with urllib.request.urlopen(ingest_req) as resp:
        workout_record = json.loads(resp.read().decode())
        print(f"[PASS] Backend /workouts recorded Session ID: {workout_record.get('id')}")
        assert workout_record.get("id") is not None

    # 6. Verify User Workouts History on Backend
    print("\n--- 6. Verify User Workout History on Backend (Port 8000) ---")
    me_req = urllib.request.Request(f"{BACKEND_BASE}/auth/me", headers=auth_headers)
    with urllib.request.urlopen(me_req) as resp:
        user_id = json.loads(resp.read().decode())["id"]

    history_req = urllib.request.Request(f"{BACKEND_BASE}/workouts/user/{user_id}", headers=auth_headers)
    with urllib.request.urlopen(history_req) as resp:
        user_workouts = json.loads(resp.read().decode())
        print(f"[PASS] Backend user {user_id} history has {len(user_workouts)} sessions")
        assert len(user_workouts) >= 1

    print("\n==================================================================")
    print("      ALL MULTI-SERVICE INTEGRATION TESTS PASSED 100%!           ")
    print("==================================================================")

if __name__ == "__main__":
    run_integration_test()
