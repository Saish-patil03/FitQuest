# FitQuest --- AI Fitness & Pose Analytics Platform

> **Your camera counts. Your journey motivates.**

FitQuest is a browser-first AI fitness platform that uses computer
vision, pose estimation, workout analytics, and an AI fitness assistant
to help users perform exercises, count repetitions, receive form
feedback, and maintain workout consistency.

The project was designed with students and beginners in mind and
combines a web-based workout experience with a Python computer-vision
backend, persistent workout data, and AI-powered coaching.

------------------------------------------------------------------------

## 1. Project Overview

FitQuest turns a normal webcam into an interactive fitness assistant.

The basic workflow is:

**User → Web Frontend → Webcam → Computer Vision → Exercise Tracker →
Workout Telemetry → Backend/API → Database → AI Coach → Results &
Feedback**

During a workout, the system can:

-   Access the user's webcam through the browser.
-   Process pose/keypoint information.
-   Detect and track exercise movements.
-   Count repetitions.
-   Evaluate basic exercise form.
-   Generate feedback events.
-   Track workout duration and performance.
-   Store completed workout sessions.
-   Generate AI coaching feedback.
-   Provide an AI fitness chatbot for fitness-related questions.

------------------------------------------------------------------------

# 2. Technology Stack

## Frontend

### HTML5

Used to build the browser interface and workout screens.

The frontend contains the structure for:

-   Home/dashboard
-   Exercise selection
-   Workout setup
-   Live workout
-   Workout results
-   AI fitness chat

### CSS3

Used for the visual design and responsive layout of the application.

### JavaScript

Used for frontend application logic, including:

-   Screen/navigation handling
-   Webcam access
-   Sending frames to the backend
-   Receiving live workout data
-   Updating rep count
-   Updating form score
-   Displaying feedback
-   Workout timers
-   Sending completed workout telemetry
-   AI chatbot communication

Important frontend files include:

-   `frontend/index.html`
-   `frontend/style.css`
-   `frontend/app.js`
-   `frontend/workout.js`

------------------------------------------------------------------------

# 3. Backend Technology

## Python

Python is the main backend and computer-vision language.

It is used for:

-   Computer vision
-   Exercise tracking
-   Backend APIs
-   Workout telemetry
-   Database operations
-   AI assistant integration
-   Validation and application logic

## FastAPI

FastAPI provides the REST API and live workout communication layer.

The backend exposes APIs for:

-   Users
-   Exercises
-   Workouts
-   Live webcam processing
-   AI questions
-   Health/status checks

Example API areas:

``` text
/api/v1/users
/api/v1/exercises
/api/v1/workouts
/api/v1/ai/qa
/api/v1/workouts/live/process-frame
/api/v1/workouts/live/stop-session
```

A WebSocket endpoint is also used for live workout communication:

``` text
/api/v1/workouts/live-ws/{exercise_choice}
```

------------------------------------------------------------------------

# 4. Computer Vision / Pose Analytics

## MediaPipe Pose

MediaPipe Pose is used as the pose-estimation foundation.

The system uses human body landmarks/keypoints to understand body
movement.

The pose pipeline conceptually works as:

``` text
Camera Frame
     ↓
Pose Detection
     ↓
Body Keypoints
     ↓
Joint/Body Angles
     ↓
Exercise Logic
     ↓
Rep Counting + Form Feedback
```

## Pose Detector

The project's pose detection layer receives video/image frames and
extracts pose information used by exercise trackers.

The main pose-related implementation is connected to:

-   `pose.py`
-   exercise tracking modules
-   utility functions

------------------------------------------------------------------------

# 5. Exercise Tracking System

FitQuest uses an exercise registry and individual exercise trackers.

The tracker architecture allows different exercises to use their own
movement rules while sharing common tracking infrastructure.

The project contains an `exercises/` package containing
exercise-specific implementations and a registry.

The exercise system is responsible for:

-   Detecting movement phases
-   Tracking repetitions
-   Checking relevant body angles
-   Producing form feedback
-   Maintaining exercise state

Examples of exercise implementations include exercises such as:

-   Bicep curl
-   Squat
-   Other registered exercises in the project

The system was designed so additional exercises can be added without
rewriting the entire computer-vision pipeline.

------------------------------------------------------------------------

# 6. Utility Layer

The `utils/` package contains reusable computer-vision and tracking
utilities.

Important responsibilities include:

### `angles.py`

Used for calculating body/joint angles from pose landmarks.

### `keypoints.py`

Contains helper functionality for working with pose keypoints.

### `counter.py`

Provides shared repetition-counting functionality and exercise tracker
infrastructure.

The base tracker also collects feedback events so that workout telemetry
can later be passed to the AI coaching layer.

------------------------------------------------------------------------

# 7. AI Fitness Assistant

FitQuest includes an AI fitness assistant that analyzes workout
telemetry and generates coaching feedback.

The assistant layer contains components such as:

``` text
assistant/
├── assistant.py
├── prompts.py
├── schema.py
└── __init__.py
```

### `assistant.py`

Contains the core AI assistant logic.

### `prompts.py`

Contains prompt definitions used to guide AI-generated fitness feedback.

### `schema.py`

Defines structured data models used by the assistant.

The AI assistant can work with information such as:

-   Exercise performed
-   Repetitions
-   Workout duration
-   Form score
-   Feedback events
-   Workout observations

The system was also designed with an offline fallback so that workout
processing can remain functional when an external AI service is
unavailable.

------------------------------------------------------------------------

# 8. Gemini / Generative AI Integration

The project supports Gemini/Google Generative AI integration for
AI-powered coaching and chatbot functionality.

The AI layer is used for:

-   Workout coaching
-   Workout summaries
-   Fitness questions
-   Personalized feedback

API credentials are stored through environment variables and are
intentionally excluded from version control.

The repository contains `.env.example` as a template for required
environment variables.

Never commit the real `.env` file or API keys to a public repository.

------------------------------------------------------------------------

# 9. Database

## SQLAlchemy

SQLAlchemy is used as the ORM/database abstraction layer.

It allows Python application code to interact with database tables
through models.

## SQLite

SQLite was used during the local development/database implementation.

The project also includes migration-related work for moving from SQLite
toward PostgreSQL.

The database stores information such as:

### Users

``` text
id
name
email
fitness_goal
experience_level
created_at
```

### Exercises

``` text
id
name
description
muscle_group
difficulty
```

### Workout Sessions

``` text
id
user_id
exercise_id
repetitions
duration_sec
form_score
started_at
completed_at
```

### Form Logs

``` text
id
workout_session_id
form_score
feedback
created_at
```

### AI Coaching Logs

Used for storing AI-generated coaching information associated with
workout sessions.

------------------------------------------------------------------------

# 10. Pydantic

Pydantic / Pydantic v2 is used for:

-   API request validation
-   API response schemas
-   Structured data validation
-   Configuration management

This helps ensure that data entering and leaving the backend follows the
expected structure.

------------------------------------------------------------------------

# 11. Backend Architecture

The backend was structured into separate responsibilities instead of
putting everything into one Python file.

A simplified architecture is:

``` text
backend/
├── main.py
├── config.py
├── database.py
├── models/
├── schemas/
├── api/
└── services/
```

## `backend/main.py`

Creates and configures the FastAPI application.

Responsibilities include:

-   Creating the FastAPI app
-   CORS configuration
-   Health endpoint
-   API router registration

## `backend/config.py`

Contains application configuration and environment-variable handling.

It supports settings such as:

-   Database URL
-   Gemini API key
-   Google API key

## `backend/database.py`

Handles database setup.

Responsibilities include:

-   SQLAlchemy engine
-   Session management
-   Base model
-   Database dependency
-   SQLite configuration

------------------------------------------------------------------------

# 12. Database Models

The `backend/models/` directory contains ORM models representing
database entities.

Important model areas include:

``` text
user.py
workout.py
coaching.py
```

These models represent persistent application data.

------------------------------------------------------------------------

# 13. API Layer

The `backend/api/` directory separates API endpoints by functionality.

## Users API

Provides endpoints for:

``` text
POST /api/v1/users
GET  /api/v1/users
GET  /api/v1/users/{user_id}
```

These endpoints manage user profiles.

## Exercises API

Provides exercise catalogue endpoints:

``` text
GET /api/v1/exercises
GET /api/v1/exercises/{exercise_id}
```

The exercise catalogue is connected to the project's exercise registry.

## Workouts API

The workout API accepts completed workout telemetry and stores it in the
database.

It handles information such as:

-   User ID
-   Exercise ID
-   Repetitions
-   Duration
-   Form score
-   Feedback events

The endpoint can also trigger AI coaching and save the generated result.

## AI API

The AI chatbot endpoint is:

``` text
POST /api/v1/ai/qa
```

The frontend sends a user's fitness question to this endpoint and
receives the AI response.

------------------------------------------------------------------------

# 14. Live Webcam Architecture

One of the major implementation stages was connecting the browser webcam
to the Python computer-vision engine.

The flow is:

``` text
Browser Webcam
      ↓
HTML Video Element
      ↓
Canvas / Frame Capture
      ↓
Frontend Workout Logic
      ↓
FastAPI CV Bridge
      ↓
Pose Detector
      ↓
Exercise Controller
      ↓
Rep + Form Analysis
      ↓
Live Result
      ↓
Frontend HUD
```

The bridge service is implemented in:

``` text
backend/services/cv_service.py
```

This service connects browser video frames with the existing
computer-vision exercise engine.

------------------------------------------------------------------------

# 15. Live Workout Interface

The live workout interface provides an interactive HUD containing
information such as:

-   Rep counter
-   Form score
-   Session duration
-   Form feedback

The browser also contains:

``` html
<video id="webcamFeed">
<img id="overlayImage">
<canvas id="frameCanvas">
```

These elements support the webcam and live workout visualization
pipeline.

------------------------------------------------------------------------

# 16. AI Fitness Chatbot

FitQuest contains a dedicated AI Coach chatbot.

The chatbot frontend is implemented using:

``` text
frontend/index.html
frontend/style.css
frontend/app.js
```

The frontend communicates with:

``` text
POST /api/v1/ai/qa
```

The chatbot supports:

-   User fitness questions
-   AI responses
-   Typing/loading indication
-   Markdown-style response formatting
-   Backend API communication

------------------------------------------------------------------------

# 17. Workout Session Flow

A typical workout follows this sequence:

``` text
1. User opens FitQuest
        ↓
2. Selects an exercise
        ↓
3. Configures workout
        ↓
4. Browser requests webcam access
        ↓
5. Live frames are captured
        ↓
6. Frames are sent to CV backend
        ↓
7. Pose landmarks are detected
        ↓
8. Exercise tracker analyzes movement
        ↓
9. Repetitions are counted
        ↓
10. Form is evaluated
        ↓
11. Feedback is generated
        ↓
12. Workout ends
        ↓
13. Telemetry is sent to backend
        ↓
14. Workout is stored in database
        ↓
15. AI coaching is generated
        ↓
16. User receives workout results
```

------------------------------------------------------------------------

# 18. Major Development Phases

## Phase 3 --- CV Engine & AI Assistant Integration

The computer-vision engine and AI fitness assistant were integrated.

The integration:

-   Preserved the existing exercise tracking system.
-   Added feedback-event collection.
-   Created workout-session telemetry.
-   Connected completed sessions to the AI assistant.
-   Added AI coaching feedback to workout results.

A dedicated integration test was added to verify the connection.

------------------------------------------------------------------------

## Phase 4 --- Backend & Persistence Architecture

A FastAPI backend architecture was created.

Major work included:

-   FastAPI application
-   CORS configuration
-   Database configuration
-   SQLAlchemy setup
-   Database models
-   Pydantic schemas
-   REST APIs
-   Exercise seeding
-   Workout ingestion
-   AI coaching persistence

------------------------------------------------------------------------

## Phase 5 --- AI Coach Chatbot

The AI chatbot frontend was created and connected to the backend.

Major work included:

-   Chat UI
-   Responsive styling
-   JavaScript API communication
-   Typing indicator
-   Markdown formatting
-   Backend AI endpoint
-   Frontend chatbot testing

------------------------------------------------------------------------

## Phase 6 Step 1 --- Workout Experience

The complete workout UI flow was implemented.

Screens included:

``` text
Home
  ↓
Exercise Selection
  ↓
Workout Setup
  ↓
Live Workout
  ↓
Workout Results
```

The results screen sends workout telemetry to the backend.

------------------------------------------------------------------------

## Phase 6 Step 2 --- Live Webcam & CV Bridge

The browser webcam was connected to the Python computer-vision system.

Major work included:

-   Webcam video element
-   Frame capture canvas
-   CV bridge service
-   Live frame endpoint
-   Live session stop endpoint
-   WebSocket support
-   Frontend workout integration

------------------------------------------------------------------------

# 19. Important Project Files

A simplified project structure is:

``` text
AI-Fitness/
│
├── assistant/
│   ├── assistant.py
│   ├── prompts.py
│   ├── schema.py
│   └── __init__.py
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── api/
│   ├── models/
│   ├── schemas/
│   └── services/
│
├── data/
│
├── exercises/
│   ├── registry.py
│   ├── bicep_curl.py
│   ├── squat.py
│   └── ...
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── workout.js
│
├── models/
│
├── utils/
│   ├── angles.py
│   ├── keypoints.py
│   └── counter.py
│
├── pose.py
├── exercise.py
├── main.py
├── modal_app.py
├── migrate_sqlite_to_postgres.py
│
├── PHASE4_ARCHITECTURE.md
├── phase4_implementation_plan.md
├── PHASE5_CHATBOT_REPORT.md
├── PHASE6_STEP1_REPORT.md
├── PHASE6_STEP2_REPORT.md
│
├── .env.example
├── .gitignore
└── README.md
```

The exact contents can evolve as the project is extended.

------------------------------------------------------------------------

# 20. Environment Variables

Sensitive configuration is stored locally in `.env`.

Typical configuration includes values for:

``` text
DATABASE_URL
GEMINI_API_KEY
GOOGLE_API_KEY
```

The real `.env` file must not be committed to GitHub.

Instead, use:

``` text
.env.example
```

to document the required environment variables without exposing secrets.

------------------------------------------------------------------------

# 21. Git & Repository Structure

The project is maintained using Git and GitHub.

The repository uses branches for development and integration.

The main development branch used during the final architecture work was:

``` text
migration/multi-service-architecture
```

The project was also merged into the `main` branch.

The repository contains the main FitQuest application along with the
ML-related project directory.

------------------------------------------------------------------------

# 22. Deployment

The web frontend is deployed using Vercel.

The backend and ML services were separated into deployable services
during the migration to the multi-service architecture.

The deployment architecture therefore separates responsibilities
between:

``` text
Frontend
   ↓
Backend API
   ↓
ML / Computer Vision Service
   ↓
Database
   ↓
AI Services
```

This separation makes the system easier to deploy and maintain compared
with keeping every component inside one application process.

------------------------------------------------------------------------

# 23. Security & Repository Hygiene

Before making the repository public, the following local/development
files should remain excluded from Git:

``` text
.env
.venv/
__pycache__/
*.pyc
*.db
*.sqlite
*.log
.DS_Store
```

The `.gitignore` file is responsible for preventing these files from
being added accidentally.

API keys, passwords, database credentials, and other secrets should
never be placed directly inside source code.

------------------------------------------------------------------------

# 24. Testing

Testing was performed during the implementation phases to verify:

-   Exercise tracking
-   AI assistant integration
-   Backend integration
-   Workout ingestion
-   Frontend chatbot
-   Live workout functionality
-   Overall integration behavior

Tests were also used to ensure that changes to the new architecture did
not break the existing computer-vision engine.

------------------------------------------------------------------------

# 25. Key Design Principles

FitQuest was developed around several principles:

### Modular Architecture

Computer vision, AI, backend, database, and frontend responsibilities
are separated.

### Reusable Exercise System

Exercise trackers are organized so that new exercises can be added
systematically.

### Real-Time Interaction

The live workout system processes webcam information and provides
feedback during exercise.

### AI-Assisted Coaching

Workout telemetry is converted into useful coaching information through
the AI assistant.

### Browser-First Experience

Users can interact with the workout system through a web browser and
webcam.

### Persistent Data

Completed workouts and related feedback can be stored for later use.

------------------------------------------------------------------------

# 26. What FitQuest Demonstrates

The project combines several software and AI concepts in one working
system:

-   Full-stack web development
-   REST API development
-   WebSocket communication
-   Computer vision
-   Human pose estimation
-   Exercise-state tracking
-   Real-time webcam processing
-   Database design
-   ORM-based persistence
-   Data validation
-   Generative AI
-   AI chatbot development
-   Cloud deployment
-   Git/GitHub version control
-   Multi-service architecture

------------------------------------------------------------------------

# 27. Quick Mental Model

If you need to understand the entire project quickly, remember these
five layers:

``` text
┌──────────────────────────────┐
│          FRONTEND            │
│ HTML + CSS + JavaScript      │
│ UI + Webcam + Workout HUD    │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│        BACKEND / API         │
│ FastAPI + Pydantic           │
│ REST + WebSocket             │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│       COMPUTER VISION        │
│ Pose Detection + Exercise    │
│ Tracking + Rep Counting      │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│          DATABASE            │
│ SQLAlchemy + SQLite/Postgres │
│ Users + Workouts + Logs      │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│          AI LAYER            │
│ Gemini + AI Fitness Coach    │
│ Coaching + Chatbot           │
└──────────────────────────────┘
```

------------------------------------------------------------------------

# 28. Final Summary

FitQuest is an AI-powered browser fitness platform that connects a
webcam-based computer-vision engine with a structured backend,
persistent workout database, and generative AI coaching system.

The most important relationship between the components is:

**Frontend captures the workout → Backend transports/processes the data
→ Computer vision understands movement → Exercise trackers count and
evaluate repetitions → Database stores workout information → AI
assistant converts workout telemetry into coaching feedback.**

This architecture allows FitQuest to function as more than a simple
exercise counter: it provides a complete pipeline from live user
interaction to workout analytics and AI-assisted coaching.

------------------------------------------------------------------------

## Repository Safety Note

This repository may contain configuration templates and documentation,
but production secrets must always remain outside version control.

Before sharing the repository publicly, verify that no API keys,
passwords, private credentials, personal data, or local database files
have been committed.
