# FitQuest / AI-Fitness — Phase 4 Implementation Plan
# MOVEMENT DNA™ + AI PERFORMANCE INTELLIGENCE

==================================================
A. EXISTING ARCHITECTURE
==================================================

FitQuest currently operates a modular 3-phase human movement intelligence engine:
1. Phase 1 (Biomechanical Extraction): `backend/services/movement_intelligence.py` buffers non-intrusive joint angle/velocity telemetry during CV workouts and computes 5 normalized dimensions: Range of Motion (ROM), Movement Stability, Tempo Control, Repetition Consistency, Bilateral Symmetry, plus Overall Movement Quality (0–100).
2. Phase 2 (Persistence & Longitudinal Evolution): `MovementFingerprintModel` in `backend/models/movement_fingerprint.py` stores session fingerprints. `MovementFingerprintService` (`backend/services/movement_fingerprint_service.py`) provides exercise-specific evolution comparisons, Δ%, and baseline tracking.
3. Phase 3 (Adaptive AI Training): `AdaptiveTrainingEngine` (`backend/services/adaptive_training.py`) categorizes biomechanical limiters into `STRONG`, `ADEQUATE`, `NEEDS ATTENTION`, `HIGH PRIORITY`, scoring the 20-exercise catalogue and generating tailored workout plans with eccentric tempos.
4. Workout Orchestration: `frontend/workout.js` manages single exercise, structured routines, and adaptive sessions with live YOLO webcam tracking.

==================================================
B. EXISTING REUSABLE DATA
==================================================

All required intelligence can be deterministically computed from existing tables and schemas:
- `movement_fingerprints` Table:
  - `user_id`, `workout_session_id`, `exercise_id`, `exercise_name`
  - `range_of_motion`, `movement_stability`, `tempo_control`, `repetition_consistency`, `bilateral_symmetry`, `overall_movement_quality`
  - `form_score`, `repetition_count`, `session_duration`, `created_at`
- `EXERCISE_BENCHMARKS` & `EXERCISE_METADATA`:
  - 20 exercises with joint kinematic benchmarks, bilateral flags, and affinity weights.
- Adaptive Training Engine:
  - Metric classification thresholds (`STRONG` >= 80, `ADEQUATE` >= 65, `NEEDS ATTENTION` >= 50, `HIGH PRIORITY` < 50).
  - Recommendation engine with explainability rationales.

==================================================
C. PROPOSED MOVEMENT DNA ARCHITECTURE
==================================================

```
                  ┌────────────────────────────────────────────────────────┐
                  │              MOVEMENT FINGERPRINTS HISTORY             │
                  │   (PostgreSQL / SQLite: movement_fingerprints table)   │
                  └───────────────────────────┬────────────────────────────┘
                                              │
                                              ▼
                  ┌────────────────────────────────────────────────────────┐
                  │               MOVEMENT DNA ENGINE (NEW)                │
                  │          backend/services/movement_dna.py              │
                  │  - Longitudinal Dimension Averaging (Baseline/Recent)  │
                  │  - Absolute Delta & Improvement Velocity               │
                  │  - Directional Trend Vector (Improving/Stable/Decline) │
                  │  - Strongest Dimension & Primary/Secondary Limiters    │
                  │  - Confidence Scoring (Low / Moderate / High)          │
                  │  - Explainable Deterministic AI Movement Report        │
                  │  - Next Step Action & Adaptive Plan Binding            │
                  └───────────────────────────┬────────────────────────────┘
                                              │
                                              ▼
                  ┌────────────────────────────────────────────────────────┐
                  │                MOVEMENT DNA API (NEW)                  │
                  │               backend/api/movement_dna.py              │
                  │            GET /api/v1/movement-intelligence/dna       │
                  │        (Strict JWT Auth & Multi-Tenant Isolation)      │
                  └───────────────────────────┬────────────────────────────┘
                                              │
                                              ▼
                  ┌────────────────────────────────────────────────────────┐
                  │             MOVEMENT DNA DASHBOARD & UI (NEW)          │
                  │  - Hero Card: DNA Score, Strongest, Limiter, Trend     │
                  │  - Native HTML5 Canvas: 5-Axis Movement DNA Radar      │
                  │  - 5 Dimension Cards (ROM, Stability, Tempo, etc.)     │
                  │  - AI Movement Limiter & "Why This Matters" Section    │
                  │  - Interactive Multi-Metric Evolution Timeline         │
                  │  - Deterministic AI Movement Report                    │
                  │  - Direct [ GENERATE ADAPTIVE WORKOUT ] Launch Action  │
                  │  - Post-Workout Experience Enhancement with DNA Delta  │
                  └────────────────────────────────────────────────────────┘
```

==================================================
D. EXACT FILES REQUIRING MODIFICATION
==================================================

1. `backend/main.py`: Import and mount `movement_dna_router` under prefix `/api/v1`.
2. `frontend/index.html`:
   - Add `<button class="nav-tab" data-view="movementDnaView">` with double-helix DNA icon.
   - Add `<section id="movementDnaView" class="view-panel">` markup.
   - Enhance `#workoutResultStep` to render post-workout Movement DNA change (Δ%), strongest improvement, and limiter summary.
   - Add `<script src="movement_dna.js"></script>`.
3. `frontend/style.css`:
   - Cyberpunk glassmorphism styling for `.dna-container`, `.dna-hero-card`, `.dna-radar-box`, `.dna-dimension-grid`, `.dna-dimension-card`, `.dna-report-card`, `.dna-timeline-card`, and responsive mobile layouts.
4. `frontend/workout.js`:
   - Hook `switchTab('movementDnaView')` to invoke `loadMovementDNA()`.
   - Update `endWorkoutSession()` to calculate and display session-level Movement DNA impact in the workout completion card.

==================================================
E. NEW FILES REQUIRED
==================================================

1. `backend/services/movement_dna.py`:
   - Core mathematical service implementing `MovementDNAService`: profile generation, baseline/recent metrics, velocity, trends, limiter ranking, confidence, explainable AI report, and adaptive training link.
2. `backend/api/movement_dna.py`:
   - Dedicated REST route `GET /api/v1/movement-intelligence/dna`.
3. `frontend/movement_dna.js`:
   - Client controller: `loadMovementDNA()`, `renderMovementDNADashboard()`, `renderMovementDNARadar()`, `renderMovementDNATimeline()`, and adaptive launch.
4. `test_movement_dna.py`:
   - Comprehensive test suite covering 20 required verification scenarios.

==================================================
F. API CHANGES REQUIRED
==================================================

Only ONE clean, consolidated REST endpoint is added:
- `GET /api/v1/movement-intelligence/dna`:
  - Auth: Required Bearer JWT (`get_current_user_id`).
  - Query Params: `exercise_id` (optional int for exercise-specific DNA, default=None for holistic profile).
  - Response:
    ```json
    {
      "overall_score": 82.4,
      "total_sessions_analyzed": 6,
      "confidence": "High",
      "confidence_reason": "Based on 6 recorded movement sessions.",
      "strongest_dimension": {
        "key": "range_of_motion",
        "label": "Range of Motion",
        "score": 91.2,
        "status": "STRONG"
      },
      "primary_limiter": {
        "key": "tempo_control",
        "label": "Tempo Control",
        "score": 62.5,
        "status": "NEEDS ATTENTION",
        "why_it_matters": "Your joint excursion is solid, but cadence fluctuations reduce eccentric tension.",
        "ai_response": "Prescribing elongated 3-1-2 eccentric descent tempos."
      },
      "secondary_limiter": {
        "key": "movement_stability",
        "label": "Movement Stability",
        "score": 68.0,
        "status": "ADEQUATE"
      },
      "trend": {
        "direction": "IMPROVING",
        "delta": 4.6,
        "pct_change": 5.9,
        "velocity_per_session": 0.92
      },
      "dimensions": {
        "range_of_motion": { "score": 91.2, "baseline": 85.0, "recent": 92.5, "delta": 7.5, "pct_change": 8.8, "status": "STRONG", "trend": "IMPROVING", "interpretation": "Consistently achieving full biomechanical joint excursion." },
        "movement_stability": { "score": 68.0, "baseline": 64.0, "recent": 69.5, "delta": 5.5, "pct_change": 8.6, "status": "ADEQUATE", "trend": "IMPROVING", "interpretation": "Torso sway and joint jitter are stabilizing." },
        "tempo_control": { "score": 62.5, "baseline": 65.0, "recent": 61.0, "delta": -4.0, "pct_change": -6.2, "status": "NEEDS ATTENTION", "trend": "DECLINING", "interpretation": "Eccentric deceleration needs controlled pacing." },
        "repetition_consistency": { "score": 79.4, "baseline": 74.0, "recent": 81.0, "delta": 7.0, "pct_change": 9.5, "status": "ADEQUATE", "trend": "IMPROVING", "interpretation": "Rep-to-rep kinematic cadence is becoming uniform." },
        "bilateral_symmetry": { "score": 86.0, "baseline": 82.0, "recent": 87.5, "delta": 5.5, "pct_change": 6.7, "status": "STRONG", "trend": "IMPROVING", "interpretation": "Left and right joint angles remain well balanced." }
      },
      "timeline": [
        { "session_id": 101, "date": "2026-08-25T10:00:00Z", "exercise": "Squat", "overall": 76.0, "rom": 85.0, "stability": 64.0, "tempo": 65.0, "consistency": 74.0, "symmetry": 82.0 }
      ],
      "ai_report": {
        "what_you_do_well": "Your Range of Motion and Bilateral Symmetry are performing at an elite baseline.",
        "what_is_limiting_you": "Tempo Control is your primary limiter with cadence fluctuations across sets.",
        "what_changed": "Stability and consistency have improved by +8.6% across recent workouts.",
        "what_fitquest_recommends": "Incorporate controlled eccentric pacing (3-second descent) to eliminate momentum.",
        "next_step": "Generate your personalized Adaptive AI workout calibrated to your Movement DNA."
      },
      "adaptive_action": {
        "endpoint": "/api/v1/adaptive-training/generate",
        "primary_focus": "tempo_control",
        "recommended_title": "Adaptive Session: Tempo Control Focus"
      }
    }
    ```

==================================================
G. DATABASE CHANGES REQUIRED
==================================================

- ZERO DATABASE SCHEMA CHANGES:
  - The `movement_fingerprints` table already stores all required dimensions, timestamps, session links, and quality scores.
  - Zero migration scripts or schema modifications required.

==================================================
H. FRONTEND UI ARCHITECTURE
==================================================

1. Navigation & Views:
   - Add `movementDnaView` nav tab.
   - Responsive layout:
     - Desktop: 2-column top grid (Left: Hero DNA Card + Limiters; Right: Native 5-Axis Movement DNA Radar Canvas), followed by 5 Dimension Cards, Evolution Timeline Chart with metric toggles, AI Movement Report card, and sticky [ GENERATE MY ADAPTIVE WORKOUT ] CTA.
     - Tablet & Mobile: Seamless vertical collapse with touch-friendly controls.

2. Native HTML5 Canvas 5-Axis Radar:
   - Axes (Stability top, Tempo right, ROM bottom, Symmetry left, Consistency upper right/left).
   - Renders:
     - Baseline polygon (dashed amber line)
     - Recent polygon (semi-transparent glowing neon cyan fill with solid stroke)
     - Interactive hover / animated transition.
     - Null symmetry handling: cleanly collapses to 4-axis diamond when bilateral movements are not present.

3. Native Canvas Multi-Metric Timeline:
   - Smooth Bézier splines plotting longitudinal scores over sessions.
   - Interactive toggle buttons: `[ All | ROM | Stability | Tempo | Consistency | Symmetry | Overall ]`.

4. Post-Workout Enhancement:
   - Enriches `#workoutResultStep` with:
     - Movement Quality Score
     - Movement DNA Change (Δ%)
     - Strongest Improvement badge
     - Current Limiter badge
     - Direct `[ VIEW MOVEMENT DNA ]` and `[ GENERATE ADAPTIVE WORKOUT ]` buttons.

==================================================
I. MATHEMATICAL CALCULATIONS
==================================================

1. Longitudinal Averages & Baseline:
   Let F = [f_1, f_2, ..., f_N] be chronological fingerprints for the user (f_1 earliest, f_N latest):
   - Baseline Average (M_base): Average of the first min(N, 2) sessions.
   - Recent Average (M_recent): Average of the last min(N, 3) sessions.
   - Overall Average (M_overall): (1/N) * sum(f_i(M)).

2. Delta & Percentage Change:
   ΔM = M_recent - M_base
   Δ% = (ΔM / M_base) * 100  (if M_base > 0 else 0.0)

3. Improvement Velocity:
   Velocity = ΔM / max(N - 1, 1)  (score delta per session)

4. Trend Classification:
   Trend =
     - "INSUFFICIENT DATA" if N < 2
     - "IMPROVING" if ΔM >= +3.0
     - "DECLINING" if ΔM <= -3.0
     - "STABLE" if -3.0 < ΔM < +3.0

5. Overall Movement DNA Score:
   S_DNA = round((ROM + Stability + Tempo + Consistency + (Symmetry if present else avg of others)) / (5 or 4), 1)
   Derived directly from the normalized 0–100 scale, matching the existing `overall_movement_quality` formulation.

==================================================
J. SECURITY CONSIDERATIONS
==================================================

- Strict JWT Authentication: Every request extracts `auth_user_id` from JWT payload via `get_current_user_id`.
- Tenant Isolation: Database queries strictly filter `MovementFingerprintModel.user_id == auth_user_id`. Never trust user IDs provided in the request body or query params.
- No Sensitive Data: Telemetry does not store images, videos, or PII.

==================================================
K. PERFORMANCE CONSIDERATIONS
==================================================

- Zero CV Overhead: Movement DNA calculations are executed strictly on-demand when the user visits the dashboard or completes a workout. Never executed inside `process_frame()` or real-time webcam loops.
- Efficient Indexing: Uses existing indices `ix_movement_fingerprints_user_exercise` and `ix_movement_fingerprints_user_created`.
- Zero Heavy Frontend Libraries: Pure Vanilla JavaScript and HTML5 Canvas API (no Chart.js, D3, or external CDNs).

==================================================
L. REGRESSION RISKS & MITIGATION
==================================================

- Risk: Altering workout result flow breaks rep counting or form score logging.
  - Mitigation: Workout completion logic in `workout.js` is only augmented; core ingestion `POST /api/v1/workouts` remains identical.
- Risk: Null `bilateral_symmetry` breaking 5-axis radar math.
  - Mitigation: Mathematical checks dynamically handle `None` values and collapse to 4 axes without NaN errors.
- Risk: Database contention on multi-session queries.
  - Mitigation: Bounded query limits (`limit=50`) with indexed timestamp sorting.

==================================================
M. TEST STRATEGY (test_movement_dna.py)
==================================================

20 test cases covering all verification points:
1. Empty history (0 workouts) returns default DNA profile with `INSUFFICIENT DATA` and `Low` confidence.
2. Single-session baseline returns valid profile with `INSUFFICIENT DATA` trend.
3. Minimum history threshold (>= 2 sessions) activates trend analysis.
4. Baseline calculation correctly averages initial sessions.
5. Recent average correctly averages recent sessions.
6. Absolute delta calculation (ΔM).
7. Percentage change calculation (Δ%).
8. Improving trend classification (Δ >= +3.0).
9. Stable trend classification (-3.0 < Δ < +3.0).
10. Declining trend classification (Δ <= -3.0).
11. Strongest dimension identification.
12. Primary and secondary limiter identification.
13. Confidence scaling (`Low` for <= 1, `Moderate` for 2–3, `High` for 4+).
14. Null `bilateral_symmetry` handling for unilateral exercises.
15. Strict multi-user data isolation (User A vs User B).
16. Unauthenticated request rejection (401/403).
17. REST API response validation (`GET /api/v1/movement-intelligence/dna`).
18. Seamless Adaptive Training Engine integration.
19. Existing movement fingerprint database compatibility.
20. Full regression verification across all existing test suites.

==================================================
N. ACCEPTANCE CRITERIA
==================================================

- [x] Phase 0 read-only inspection complete.
- [ ] `backend/services/movement_dna.py` implemented with deterministic formulas.
- [ ] `backend/api/movement_dna.py` mounted at `GET /api/v1/movement-intelligence/dna`.
- [ ] `frontend/movement_dna.js` implemented with 5-axis Canvas radar, timeline spline, and adaptive training binding.
- [ ] `frontend/index.html` updated with Movement DNA dashboard and post-workout result enhancements.
- [ ] `frontend/style.css` updated with cyberpunk glassmorphism design.
- [ ] `test_movement_dna.py` passes with 100% score (20/20).
- [ ] All 10 existing regression test suites pass cleanly.
