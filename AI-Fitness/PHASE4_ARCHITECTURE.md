# FitQuest / AI-Fitness — Phase 4 Architecture Specification

**Project**: FitQuest / AI-Fitness (SIH 2026)  
**Scope**: Member 3 (CV Engine), Member 4 (AI Assistant), Member 5 (Backend API & Database), Member 6 (Frontend UI)

---

## A. Current Architecture (Phases 1 - 3 Foundation)

The current system is composed of two fully functional and integrated core modules:

1. **Member 3 — Computer Vision & Pose Tracking Engine**:
   - **Frameworks**: Python, OpenCV (`cv2`), Ultralytics YOLOv8 Pose (`models/pose_model.pt`).
   - **Keypoint Extraction**: COCO 17-landmark keypoint extraction with confidence thresholds (`utils/keypoints.py`).
   - **Biomechanical Math**: 2D joint angle calculation, body inclination relative to horizontal, and Exponential Moving Average (EMA) angle smoothing (`utils/angles.py`).
   - **Exercise Trackers**: 20 modular trackers (`exercises/`) inheriting from `BaseExerciseTracker` (`utils/counter.py`), mapped dynamically via `ExerciseRegistry` (`exercises/registry.py`).
   - **Session Controller**: `ExerciseController` (`exercise.py`) managing session start/end timestamps, real-time tracking, rep counting, form scoring percentage, and feedback event logging.

2. **Member 4 — AI Fitness Assistant**:
   - **Data Schemas**: `WorkoutSessionData` & `UserProfile` (`assistant/schema.py`).
   - **Prompts Engine**: Structured prompt templates for performance summaries, form breakdowns, and Q&A (`assistant/prompts.py`).
   - **Assistant Core**: `AIFitnessAssistant` (`assistant/assistant.py`) supporting Google Gemini API (`gemini-1.5-flash` / `gemini-2.0-flash`) with an offline rule-based biomechanics fallback engine.

3. **Phase 3 Integration Layer**:
   - `ExerciseController.create_session_data()` extracts CV session metrics into a `WorkoutSessionData` object.
   - `ExerciseController.finish_session()` passes session metrics to `AIFitnessAssistant` and appends `AI COACHING` feedback to the `WORKOUT SUMMARY`.
   - Fault-tolerant wrapper prevents app crashes if offline or if API key is missing.

---

## B. Phase 4 Target Architecture

The target architecture evolves AI-Fitness into a modern, decoupled multi-tier system:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MEMBER 6 — FRONTEND CLIENT                            │
│           (Web Dashboard / React / Mobile App / Camera Video Feed)           │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ HTTP REST APIs / WebSockets
┌─────────────────────────────────────▼───────────────────────────────────────┐
│                       MEMBER 5 — BACKEND API SERVICE                        │
│                (FastAPI / Pydantic / Route Controllers)                    │
└──────────────┬──────────────────────┬──────────────────────┬────────────────┘
               │                      │                      │
               │                      │                      │
┌──────────────▼─────────────┐ ┌──────▼─────────────┐ ┌──────▼────────────────┐
│ MEMBER 3 — CV ENGINE       │ │ MEMBER 4 — AI      │ │ DATABASE PERSISTENCE   │
│ (YOLO Pose / OpenCV /      │ │ ASSISTANT          │ │ (SQLAlchemy ORM /      │
│  20 Trackers / Telemetry)  │ │ (Gemini & Fallback)│ │  SQLite / PostgreSQL)  │
└────────────────────────────┘ └────────────────────┘ └───────────────────────┘
```

---

## C. Member 5 Responsibilities (Backend API & Database Engineer)

1. **FastAPI Application Framework**:
   - Setup FastAPI application server with CORS middleware, request logging, and OpenAPI docs (`/docs`).
2. **Database ORM & Migrations**:
   - Configure SQLAlchemy database connections (SQLite for dev / PostgreSQL for prod).
   - Design DB models (`UserModel`, `WorkoutSessionModel`, `FormLogModel`, `AICoachingLogModel`).
3. **API Route Handlers**:
   - Implement RESTful endpoints for User Management, Exercise Catalog, Workout Session Ingestion, and AI Coaching history.
4. **Business Logic & Service Layer**:
   - Bridge incoming HTTP payloads with Member 4's `AIFitnessAssistant` and handle persistence operations.
5. **Authentication Readiness**:
   - Structure API routes to support JWT authentication or user token headers.

---

## D. Member 6 Responsibilities (Frontend & UI Application Engineer)

1. **User Interface & Dashboard**:
   - Build responsive Web/Mobile interfaces for live exercise selection, workout stream view, and post-workout analytics.
2. **Real-time Video Feed & Overlay**:
   - Display webcam stream with real-time pose skeleton rendering, rep counter HUD, joint angle metrics, and live form feedback.
3. **Post-Workout Insights Screen**:
   - Render traditional CV workout summaries alongside formatted AI Coaching recommendations (Performance Overview, Biomechanics Rating, Actionable Cues, Next Steps).
4. **Workout History & Progress Tracking**:
   - Display historical workout charts, average form score trends, total reps per exercise, and user profile management.
5. **Backend HTTP Integration**:
   - Fetch exercise catalogs, send completed session data to Member 5 APIs via `fetch`/`axios`, and render backend responses seamlessly.

---

## E. API Responsibilities

- **Validation**: Enforce request payload schemas using Pydantic.
- **Orchestration**: Receive completed workout data $\rightarrow$ Store workout session in DB $\rightarrow$ Invoke `AIFitnessAssistant` $\rightarrow$ Store AI coaching response $\rightarrow$ Return combined JSON payload to Frontend.
- **Decoupling**: Ensure frontend applications do not depend directly on local file systems or OpenCV window rendering.

---

## F. Database Responsibilities

- **Data Integrity**: Store historical workout data, user profiles, and form feedback permanently.
- **Relational Structure**:
  - `users` (1) $\longleftrightarrow$ ($\infty$) `workout_sessions`
  - `workout_sessions` (1) $\longleftrightarrow$ ($\infty$) `form_logs`
  - `workout_sessions` (1) $\longleftrightarrow$ (1) `ai_coaching_logs`
- **Analytics Ready**: Enable fast querying for weekly workout stats, average form scores, and user progress.

---

## G. Data Models Required

### 1. Pydantic Schemas (API Data Validation)
- `UserProfileCreate` / `UserProfileResponse`:
  - `user_id`: str
  - `fitness_goal`: str ("Strength", "Hypertrophy", "Endurance", "Weight Loss")
  - `experience_level`: str ("Beginner", "Intermediate", "Advanced")
- `WorkoutSessionCreate` (Matches `WorkoutSessionData` schema):
  - `user_id`: str
  - `exercise_name`: str
  - `rep_count`: int
  - `duration_sec`: int
  - `form_score`: float
  - `form_scores_history`: List[int]
  - `feedback_events`: List[str]
- `WorkoutSessionResponse`:
  - `session_id`: int / str
  - `created_at`: datetime
  - `cv_metrics`: WorkoutSessionCreate
  - `ai_coaching`: str

### 2. SQLAlchemy ORM Models (Database Tables)
- **`UserModel`**: `id`, `username`, `email`, `fitness_goal`, `experience_level`, `created_at`
- **`ExerciseModel`**: `id`, `key`, `name`, `description`, `muscle_group`
- **`WorkoutSessionModel`**: `id`, `user_id`, `exercise_name`, `rep_count`, `duration_sec`, `form_score`, `created_at`
- **`FormLogModel`**: `id`, `session_id`, `rep_index`, `form_pass` (bool), `feedback_cue` (str)
- **`AICoachingLogModel`**: `id`, `session_id`, `ai_feedback_text`, `provider_used` ("gemini" / "rule_based"), `created_at`

---

## H. API Endpoints Required

| Method | Endpoint Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/users` | Register/create user profile |
| `GET` | `/api/v1/users/{user_id}` | Fetch user profile & settings |
| `GET` | `/api/v1/exercises` | List all 20 supported exercises |
| `POST` | `/api/v1/workouts` | Ingest completed CV workout session + generate & persist AI coaching |
| `GET` | `/api/v1/workouts/{session_id}` | Fetch single workout details & AI coaching |
| `GET` | `/api/v1/workouts/user/{user_id}` | Fetch full workout history for a user |
| `POST` | `/api/v1/ai/coaching` | Generate standalone AI coaching for workout payload |
| `POST` | `/api/v1/ai/qa` | General fitness Q&A endpoint |

---

## I. Complete Data Flow

```text
1. [Frontend M6] User selects exercise ("Squat") & starts camera stream.
2. [CV Engine M3] PoseDetector extracts keypoints, tracks reps, scores form, logs feedback events.
3. [CV Engine M3] Session ends -> ExerciseController generates WorkoutSessionData.
4. [Backend API M5] POST /api/v1/workouts receives WorkoutSessionData payload.
5. [Database M5] Session record created in `workout_sessions` table.
6. [AI Assistant M4] AIFitnessAssistant generates coaching feedback (Gemini or Fallback).
7. [Database M5] AI response stored in `ai_coaching_logs` table.
8. [Frontend M6] Receives JSON response & renders Workout Summary + AI Coaching Insights.
```

---

## J. Proposed Backend Folder Structure

```text
AI-Fitness/
├── models/                  # Existing YOLO weights
├── utils/                   # Existing CV utils
├── exercises/               # Existing 20 exercise trackers
├── assistant/               # Existing AI Assistant module
├── pose.py                  # Existing CV PoseDetector
├── exercise.py              # Existing ExerciseController
├── main.py                  # Existing CLI runner
│
├── backend/                 [PROPOSED FOR MEMBER 5]
│   ├── __init__.py
│   ├── main.py              # FastAPI app startup & router mounts
│   ├── config.py            # Environment configuration & settings
│   ├── database.py          # SQLAlchemy engine & session factory
│   ├── models/              # DB Models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── workout.py
│   │   └── coaching.py
│   ├── schemas/             # Pydantic Schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── workout.py
│   │   └── coaching.py
│   ├── api/                 # Endpoint Routers
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── exercises.py
│   │   ├── workouts.py
│   │   └── ai.py
│   └── services/            # Business Logic
│       ├── __init__.py
│       ├── workout_service.py
│       └── ai_service.py
│
└── frontend/                [PROPOSED FOR MEMBER 6]
    ├── package.json
    ├── src/                 # React/Vite/Flutter source code
    └── ...
```

---

## K. Integration Strategy

- **Zero Touch Principle**: Existing CV files (`pose.py`, `exercise.py`, `exercises/`, `utils/`) and AI files (`assistant/`) remain 100% untouched.
- **Backend Import Layer**: `backend/services/workout_service.py` imports `WorkoutSessionData` and `AIFitnessAssistant` directly as internal Python packages.
- **Standalone Execution**: The existing CLI (`python main.py`) remains completely functional for offline local webcam testing without running the backend server.

---

## L. Testing Strategy

1. **Regression Testing**:
   - Run `python test_all_exercises.py` (CV trackers).
   - Run `python test_exercise.py` (`ExerciseController`).
   - Run `python test_assistant.py` (`AIFitnessAssistant`).
   - Run `python test_integration.py` (CV + AI pipeline).
2. **Backend API Testing**:
   - Create `backend/tests/test_api.py` using `fastapi.testclient.TestClient`.
   - Test user creation, exercise catalog retrieval, workout posting, DB persistence, and AI endpoint outputs using an in-memory SQLite database (`sqlite:///:memory:`).

---

## M. Explicit List of Existing Files That MUST NOT Be Broken

The following files constitute the baseline working foundation and must be preserved without breaking changes:

1. [`pose.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/pose.py)
2. [`exercise.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/exercise.py)
3. [`exercises/registry.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/exercises/registry.py)
4. [`exercises/*.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/exercises) (all 20 exercise tracker modules)
5. [`utils/angles.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/utils/angles.py)
6. [`utils/counter.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/utils/counter.py)
7. [`utils/keypoints.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/utils/keypoints.py)
8. [`assistant/schema.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/assistant/schema.py)
9. [`assistant/prompts.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/assistant/prompts.py)
10. [`assistant/assistant.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/assistant/assistant.py)
11. [`assistant/__init__.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/assistant/__init__.py)
12. [`main.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/main.py)
13. [`test_all_exercises.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/test_all_exercises.py)
14. [`test_exercise.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/test_exercise.py)
15. [`test_assistant.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/test_assistant.py)
16. [`test_integration.py`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/test_integration.py)
17. [`requirements.txt`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/requirements.txt)
18. [`README.md`](file:///Users/nihartambe/Desktop/AI-Fitness/AI-Fitness/README.md)
