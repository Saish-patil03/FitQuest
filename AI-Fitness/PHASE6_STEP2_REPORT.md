# Phase 6 Step 2 — Live Webcam & Backend CV Bridge Integration Report

**Project**: FitQuest / AI-Fitness (SIH 2026)  
**Component**: Live Webcam Feed, Backend CV Bridge, Real-Time YOLO Pose Telemetry HUD & AI Ingestion Pipeline  

---

## 1. System Architecture & Flow

```text
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           BROWSER FRONTEND                             │
  │                                                                        │
  │  HTML5 Webcam Feed (navigator.mediaDevices.getUserMedia)               │
  │                           │                                            │
  │  Canvas Base64 Frame Capture (~8-10 FPS)                               │
  └───────────────────────────┬────────────────────────────────────────────┘
                              │
                    HTTP POST / WebSocket Stream
                              │
                              ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                            FASTAPI BACKEND                             │
  │                                                                        │
  │  backend/api/workouts.py                                               │
  │  - POST /api/v1/workouts/live/process-frame                            │
  │  - POST /api/v1/workouts/live/stop-session                             │
  │  - WebSocket /api/v1/workouts/live-ws/{exercise_choice}                │
  │                           │                                            │
  │  backend/services/cv_service.py (CVLiveService)                        │
  └───────────────────────────┬────────────────────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                    MEMBER 3 COMPUTER VISION ENGINE                     │
  │                                                                        │
  │  - PoseDetector (YOLOv8 Pose Keypoints)                                │
  │  - ExerciseController (20 ExerciseTrackers via ExerciseRegistry)       │
  │  - Biomechanics & Joint Angle Calculation                              │
  └───────────────────────────┬────────────────────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                        REAL-TIME HUD TELEMETRY                         │
  │                                                                        │
  │  { rep_count, form_score, state, feedback, annotated_frame }           │
  └───────────────────────────┬────────────────────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 WORKOUT COMPLETION & MEMBER 4 AI COACH                 │
  │                                                                        │
  │  POST /api/v1/workouts                                                 │
  │  - SQLite Database Persistence (WorkoutSession & FormLogs)             │
  │  - Member 4 AIFitnessAssistant (Gemini / Biomechanics Fallback)        │
  │  - Workout Results & AI Coaching Summary Screen                        │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Files Created & Modified

### Files Created:
- [`backend/services/cv_service.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/backend/services/cv_service.py): Bridge service (`CVLiveService`) connecting browser webcam frame streams with Member 3's `PoseDetector` and `ExerciseController`.
- [`test_phase6_step2.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/test_phase6_step2.py): Comprehensive test suite verifying live frame processing, exercise selection validation, session termination, WebSocket endpoint, ingestion pipeline, and AI coaching.
- [`PHASE6_STEP2_REPORT.md`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/PHASE6_STEP2_REPORT.md): This phase completion report.

### Files Modified:
- [`backend/api/workouts.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/backend/api/workouts.py): Added `POST /api/v1/workouts/live/process-frame`, `POST /api/v1/workouts/live/stop-session`, and `WebSocket /api/v1/workouts/live-ws/{exercise_choice}` endpoints.
- [`frontend/index.html`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/frontend/index.html): Added HTML5 `<video id="webcamFeed">`, `<img id="overlayImage">`, and hidden `<canvas id="frameCanvas">` elements.
- [`frontend/style.css`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/frontend/style.css): Styled webcam video feed and YOLO Pose skeleton overlay image.
- [`frontend/workout.js`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/frontend/workout.js): Added webcam `getUserMedia` permissions, canvas frame grabber loop (~10 FPS), live HUD telemetry updates (`rep_count`, `form_score`, `feedback`, `annotated_frame`), session termination, and payload ingestion to `POST /api/v1/workouts`.
- [`requirements.txt`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/requirements.txt): Added `websockets>=11.0`.

---

## 3. Real-Time Telemetry Data Format

### Frame Processing Endpoint
**`POST /api/v1/workouts/live/process-frame`**

#### Request Payload:
```json
{
  "session_id": "session_1700000000000",
  "exercise_choice": "1",
  "frame_data": "data:image/jpeg;base64,...",
  "include_annotated_image": true
}
```

#### Response Telemetry:
```json
{
  "status": "success",
  "exercise": "Bicep Curl",
  "rep_count": 5,
  "state": "UP",
  "primary_angle": 42.5,
  "secondary_angle": 168.1,
  "form_score": 95.0,
  "feedback": ["Good Form"],
  "valid": true,
  "annotated_frame": "data:image/jpeg;base64,..."
}
```

---

## 4. Session Lifecycle Management

1. **Start Workout**:
   - User selects exercise (1-20 or by name).
   - Browser requests camera permission via `navigator.mediaDevices.getUserMedia()`.
   - `CVLiveService` initializes a dedicated `ExerciseController` for the session.
2. **During Workout**:
   - Hidden canvas captures video frames at ~10 FPS.
   - Base64 frames are sent to backend CV bridge.
   - Member 3 `PoseDetector` detects keypoints and updates `ExerciseTracker`.
   - Frontend HUD updates Rep Counter, Form Score, Live Feedback, and renders YOLO Pose skeleton overlay image.
3. **End Workout**:
   - Camera media tracks are stopped.
   - Frame grabber loop is cleared.
   - Live CV session is closed (`stop-session`).
   - Final session stats (`rep_count`, `duration_sec`, `form_score`, `feedback_events`) are submitted to `POST /api/v1/workouts`.
   - Member 4 `AIFitnessAssistant` generates personalized AI coaching feedback.
   - Workout Result screen displays complete statistics and AI Coach insights!

---

## 5. Error Handling

- **Camera Permission Denied**: Displays user-friendly warning alert without crashing the frontend.
- **Invalid Exercise Selection**: Backend rejects invalid exercise keys (e.g. `"999"`) with clean HTTP `400 Bad Request`.
- **Keypoint Detection Loss**: Returns `status: "warning"` with feedback `"Position yourself in view"`.
- **WebSocket / Server Disconnect**: App handles disconnection gracefully and preserves accumulated local session state.

---

## 6. Testing Results

Executed full multi-suite automated test pipeline across all 10 test modules (`python test_backend.py && python test_db.py && python test_api.py && python test_frontend_chat.py && python test_phase6_step1.py && python test_phase6_step2.py && python test_assistant.py && python test_all_exercises.py && python test_exercise.py && python test_integration.py`):

- **All 10 test suites passed 100% with zero regressions.**

---

## 7. Known Limitations & Next Steps

- **Lighting & Camera Quality**: Optimal YOLO Pose keypoint tracking requires standard indoor lighting and clear visibility of upper/full body joints depending on the selected exercise.
