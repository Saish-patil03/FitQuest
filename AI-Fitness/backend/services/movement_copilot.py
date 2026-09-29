"""
FitQuest Human Movement Intelligence Engine — Phase 5: MOVEMENT COPILOT™
Real-Time Biomechanical Degradation Detection, Context-Aware Coaching, & Closed-Loop Recovery.

Responsibilities:
1. Maintain session-scoped in-memory rolling telemetry state per user session.
2. Calculate rolling biomechanical dimension scores (ROM, Stability, Tempo, Consistency, Symmetry).
3. Detect sustained movement degradation across rolling window (ignoring single-frame noise).
4. Identify primary degrading dimension & classify severity (INFO, WARNING, CRITICAL).
5. Generate context-aware, exercise-specific coaching cues for all 20 supported exercises.
6. Closed-loop recovery verification: track user response after coaching and confirm recovery.
7. Integrate Phase 4 Movement DNA limiters and Phase 3 Adaptive Training tempo targets.
8. Generate post-workout Movement Copilot session intelligence summary.

Zero-Hallucination & Non-Clinical:
All evaluations are derived from genuine kinematic telemetry. Language is strictly coaching-focused.
"""

import time
import math
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from backend.services.movement_intelligence import (
    MovementAnalyzer,
    FrameTelemetrySample,
    EXERCISE_BENCHMARKS
)


# ---------------------------------------------------------------------------
# Exercise-Specific Coaching Cue Matrix for All 20 Exercises
# ---------------------------------------------------------------------------
EXERCISE_COACHING_MATRIX: Dict[str, Dict[str, Dict[str, str]]] = {
    # 1. Bicep Curl
    "1": {
        "range_of_motion": {
            "DESCENT": "Lower all the way down to full elbow extension.",
            "ASCENT": "Curl up fully to achieve peak contraction at the top.",
            "DEFAULT": "Ensure full range of motion from bottom extension to top squeeze."
        },
        "movement_stability": {
            "DESCENT": "Lock your elbows to your torso — avoid swinging your upper body.",
            "ASCENT": "Keep your elbows pinned in place and isolate your biceps.",
            "DEFAULT": "Stabilize your torso and avoid using body momentum."
        },
        "tempo_control": {
            "DESCENT": "Slow down your lowering phase — aim for a 2 to 3 second descent.",
            "ASCENT": "Control the upward curl without jerking the weight.",
            "DEFAULT": "Maintain a steady, controlled tempo throughout the rep."
        },
        "repetition_consistency": {
            "DEFAULT": "Keep your rep cadence and elbow path uniform on every rep."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Match your left and right arm speeds and curl heights evenly."
        }
    },
    # 2. Squat
    "2": {
        "range_of_motion": {
            "DESCENT": "Sink deeper into your squat until hips reach knee level.",
            "ASCENT": "Drive all the way up to full hip and knee extension.",
            "DEFAULT": "Focus on full squat depth while keeping chest proud."
        },
        "movement_stability": {
            "DESCENT": "Control your descent — keep your knees tracking steadily over toes.",
            "ASCENT": "Drive evenly through midfoot without letting knees cave inward.",
            "DEFAULT": "Maintain a stable, upright torso and steady foot pressure."
        },
        "tempo_control": {
            "DESCENT": "You're rushing the descent. Slow down and control the eccentric phase.",
            "ASCENT": "Explode upward smoothly without bouncing at the bottom.",
            "DEFAULT": "Control your descent speed and avoid rushing the inflection point."
        },
        "repetition_consistency": {
            "DEFAULT": "Maintain the same depth and pacing across consecutive reps."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Distribute your weight equally between left and right legs."
        }
    },
    # 3. Push-up
    "3": {
        "range_of_motion": {
            "DESCENT": "Lower chest closer to the floor for full chest depth.",
            "ASCENT": "Press up to full elbow extension at the top.",
            "DEFAULT": "Maximize push-up depth without losing plank alignment."
        },
        "movement_stability": {
            "DESCENT": "Brace your core and glutes — maintain a rigid, straight spine.",
            "ASCENT": "Push the ground away without letting your hips sag or pike.",
            "DEFAULT": "Keep your head, spine, and hips in a straight alignment."
        },
        "tempo_control": {
            "DESCENT": "Control your lowering phase — avoid dropping suddenly.",
            "ASCENT": "Press up smoothly with controlled force.",
            "DEFAULT": "Avoid rushing through reps; maintain deliberate pacing."
        },
        "repetition_consistency": {
            "DEFAULT": "Keep your hand placement and chest depth identical on each rep."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Press equally with both arms to keep shoulders level."
        }
    },
    # 4. Lunges
    "4": {
        "range_of_motion": {
            "DESCENT": "Lower back knee toward floor until front knee reaches 90 degrees.",
            "ASCENT": "Drive fully back up through your front heel.",
            "DEFAULT": "Achieve full lunge depth with controlled split stance."
        },
        "movement_stability": {
            "DESCENT": "Control your front knee — keep it aligned over your ankle.",
            "ASCENT": "Stabilize your torso upright as you push back up.",
            "DEFAULT": "Keep your pelvis square and avoid lateral torso wobble."
        },
        "tempo_control": {
            "DESCENT": "Slow the descent into the lunge; do not crash your back knee.",
            "ASCENT": "Push up with steady control.",
            "DEFAULT": "Maintain steady cadence on each leg."
        },
        "repetition_consistency": {
            "DEFAULT": "Ensure consistent stride length and depth on each rep."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Match depth and balance between both legs."
        }
    },
    # 5. Shoulder Press
    "5": {
        "range_of_motion": {
            "ASCENT": "Press fully overhead to complete lockout without arching back.",
            "DESCENT": "Lower handles down to ear level for full range.",
            "DEFAULT": "Ensure full vertical excursion from shoulders to overhead."
        },
        "movement_stability": {
            "ASCENT": "Brace your abs to prevent excessive lumbar hyperextension.",
            "DESCENT": "Keep your ribcage tucked and shoulder blades active.",
            "DEFAULT": "Maintain vertical torso stability throughout the press."
        },
        "tempo_control": {
            "DESCENT": "Resist gravity on the way down — 2 second controlled lower.",
            "ASCENT": "Press upward with controlled acceleration.",
            "DEFAULT": "Avoid dropping the weight rapidly on the eccentric phase."
        },
        "repetition_consistency": {
            "DEFAULT": "Maintain a consistent overhead path on every rep."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Keep both arms pressing in synchrony at identical heights."
        }
    },
    # 6. Jumping Jacks
    "6": {
        "range_of_motion": {
            "DEFAULT": "Reach arms fully overhead and widen foot stance."
        },
        "movement_stability": {
            "DEFAULT": "Land softly on the balls of your feet with knees slightly bent."
        },
        "tempo_control": {
            "DEFAULT": "Maintain a steady, rhythmic jumping cadence."
        },
        "repetition_consistency": {
            "DEFAULT": "Keep your jump timing and arm swing regular."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Coordinate arm and leg spread symmetrically."
        }
    },
    # 7. High Knees
    "7": {
        "range_of_motion": {
            "DEFAULT": "Drive knees up to hip height (90 degrees) on each step."
        },
        "movement_stability": {
            "DEFAULT": "Stay upright; avoid leaning backwards as fatigue sets in."
        },
        "tempo_control": {
            "DEFAULT": "Maintain high cadence and light, rapid foot contact."
        },
        "repetition_consistency": {
            "DEFAULT": "Keep consistent knee lift height throughout the set."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Drive both left and right knees to equal height."
        }
    },
    # 8. Mountain Climbers
    "8": {
        "range_of_motion": {
            "DEFAULT": "Drive knees fully forward toward chest on each stride."
        },
        "movement_stability": {
            "DEFAULT": "Keep hips low in line with shoulders; prevent bouncing."
        },
        "tempo_control": {
            "DEFAULT": "Maintain a smooth, continuous piston rhythm."
        },
        "repetition_consistency": {
            "DEFAULT": "Keep your stride rhythm even on both sides."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Drive left and right legs with equal power."
        }
    },
    # 9. Plank
    "9": {
        "range_of_motion": {
            "DEFAULT": "Maintain a neutral, flat line from head to heels."
        },
        "movement_stability": {
            "DEFAULT": "Your hips are sagging. Squeeze glutes and brace your core."
        },
        "tempo_control": {
            "DEFAULT": "Breathe steadily and hold isometric tension."
        },
        "repetition_consistency": {
            "DEFAULT": "Maintain rigid isometric posture throughout the hold."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Keep shoulders and hips level with no rotational tilt."
        }
    },
    # 10. Calf Raise
    "10": {
        "range_of_motion": {
            "ASCENT": "Push all the way up onto balls of feet for peak contraction.",
            "DESCENT": "Lower heels fully for maximum calf stretch.",
            "DEFAULT": "Maximize vertical ankle excursion."
        },
        "movement_stability": {
            "DEFAULT": "Keep ankles aligned; avoid rolling onto the outer edges of feet."
        },
        "tempo_control": {
            "ASCENT": "Hold for a 1-second pause at the peak.",
            "DESCENT": "Lower down slowly under control (2-3 seconds).",
            "DEFAULT": "Avoid bouncing at the bottom of the movement."
        },
        "repetition_consistency": {
            "DEFAULT": "Keep peak height consistent across all repetitions."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Apply equal upward drive across both feet."
        }
    },
    # 11. Lateral Raise
    "11": {
        "range_of_motion": {
            "DEFAULT": "Raise arms until parallel to the floor at shoulder height."
        },
        "movement_stability": {
            "DEFAULT": "Keep torso stationary — do not swing torso or use momentum."
        },
        "tempo_control": {
            "DEFAULT": "Control the lowering phase; do not let dumbbells drop."
        },
        "repetition_consistency": {
            "DEFAULT": "Keep arm elevation and elbow angle uniform."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Raise both arms to the exact same height simultaneously."
        }
    },
    # 12. Overhead Squat
    "12": {
        "range_of_motion": {
            "DEFAULT": "Reach full squat depth while keeping arms locked overhead."
        },
        "movement_stability": {
            "DEFAULT": "Keep arms vertically aligned and chest upright."
        },
        "tempo_control": {
            "DEFAULT": "Control your descent to preserve shoulder and hip balance."
        },
        "repetition_consistency": {
            "DEFAULT": "Maintain identical overhead lockout on every repetition."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Keep overhead bar/hands level throughout the squat."
        }
    },
    # 13. Russian Twists
    "13": {
        "range_of_motion": {
            "DEFAULT": "Rotate fully across torso to engage obliques on both sides."
        },
        "movement_stability": {
            "DEFAULT": "Keep feet elevated and spine braced at a 45-degree angle."
        },
        "tempo_control": {
            "DEFAULT": "Slow down the twist; avoid jerky momentum."
        },
        "repetition_consistency": {
            "DEFAULT": "Maintain equal rotation angles left and right."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Rotate with equal depth to both sides."
        }
    },
    # 14. Glute Bridge
    "14": {
        "range_of_motion": {
            "DEFAULT": "Drive hips upward until thighs and torso form a straight line."
        },
        "movement_stability": {
            "DEFAULT": "Drive through heels and squeeze glutes at the top."
        },
        "tempo_control": {
            "DEFAULT": "Pause 1 second at the peak and lower under control."
        },
        "repetition_consistency": {
            "DEFAULT": "Maintain full hip extension on every rep."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Keep pelvis level with equal drive from both glutes."
        }
    },
    # 15. Tricep Dips
    "15": {
        "range_of_motion": {
            "DEFAULT": "Lower until elbows reach a 90-degree angle, then press up."
        },
        "movement_stability": {
            "DEFAULT": "Keep shoulders depressed and elbows tracking straight back."
        },
        "tempo_control": {
            "DEFAULT": "Control the descent; avoid sudden dropping."
        },
        "repetition_consistency": {
            "DEFAULT": "Hit the same depth on each repetition."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Press equally with both triceps to keep shoulders level."
        }
    },
    # 16. Wall Sit
    "16": {
        "range_of_motion": {
            "DEFAULT": "Adjust hips and knees to a 90-degree angle."
        },
        "movement_stability": {
            "DEFAULT": "Press lower back firmly into the wall and keep knees steady."
        },
        "tempo_control": {
            "DEFAULT": "Breathe steadily and hold solid isometric position."
        },
        "repetition_consistency": {
            "DEFAULT": "Maintain steady posture without sliding upward."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Distribute weight evenly across both feet."
        }
    },
    # 17. Deadlift
    "17": {
        "range_of_motion": {
            "DEFAULT": "Hinge hips back fully and stand tall to complete hip lockout."
        },
        "movement_stability": {
            "DEFAULT": "Maintain a neutral spine; do not round your lower back."
        },
        "tempo_control": {
            "DEFAULT": "Lower with a controlled hip hinge and drive up with power."
        },
        "repetition_consistency": {
            "DEFAULT": "Keep bar path close to legs on every repetition."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Pull evenly with both legs and keep shoulders square."
        }
    },
    # 18. Burpees
    "18": {
        "range_of_motion": {
            "DEFAULT": "Lower chest fully to floor and jump with arms overhead."
        },
        "movement_stability": {
            "DEFAULT": "Land softly in squat before placing hands on floor."
        },
        "tempo_control": {
            "DEFAULT": "Maintain a continuous, controlled rhythm."
        },
        "repetition_consistency": {
            "DEFAULT": "Keep transitions between phases smooth and consistent."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Jump and land evenly on both feet."
        }
    },
    # 19. Hammer Curl
    "19": {
        "range_of_motion": {
            "DEFAULT": "Curl up to chest height and lower fully to straight arms."
        },
        "movement_stability": {
            "DEFAULT": "Pin elbows to ribcage and eliminate torso swing."
        },
        "tempo_control": {
            "DEFAULT": "Slow down the descent (2-3 seconds) to maximize tension."
        },
        "repetition_consistency": {
            "DEFAULT": "Maintain identical neutral wrist orientation on every rep."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Match curl height and speed across both arms."
        }
    },
    # 20. Crunch
    "20": {
        "range_of_motion": {
            "DEFAULT": "Lift shoulder blades completely off the floor to contract abs."
        },
        "movement_stability": {
            "DEFAULT": "Support head gently without pulling on your neck."
        },
        "tempo_control": {
            "DEFAULT": "Pause at top crunch position and lower under control."
        },
        "repetition_consistency": {
            "DEFAULT": "Maintain focused abdominal flexion on each rep."
        },
        "bilateral_symmetry": {
            "DEFAULT": "Lift both shoulders evenly without twisting."
        }
    }
}

DIMENSION_LABELS = {
    "range_of_motion": "Range of Motion",
    "movement_stability": "Movement Stability",
    "tempo_control": "Tempo Control",
    "repetition_consistency": "Repetition Consistency",
    "bilateral_symmetry": "Bilateral Symmetry"
}


# ---------------------------------------------------------------------------
# Copilot Session State & Telemetry Window
# ---------------------------------------------------------------------------
@dataclass
class CopilotSessionState:
    session_id: str
    user_id: int
    exercise_id: str = "1"
    exercise_name: str = "Exercise"
    created_at: float = field(default_factory=time.time)
    
    # Rolling telemetry samples (last 60 samples ~ 6-8 seconds)
    samples: List[FrameTelemetrySample] = field(default_factory=list)
    
    # Rep-level summaries
    rep_metrics: List[Dict[str, float]] = field(default_factory=list)
    
    # Baseline metrics (established over initial samples / reps)
    baseline_established: bool = False
    baseline_metrics: Dict[str, float] = field(default_factory=lambda: {
        "range_of_motion": 80.0,
        "movement_stability": 80.0,
        "tempo_control": 80.0,
        "repetition_consistency": 80.0,
        "bilateral_symmetry": 85.0
    })
    
    # Current active rolling metrics
    current_metrics: Dict[str, float] = field(default_factory=lambda: {
        "range_of_motion": 80.0,
        "movement_stability": 80.0,
        "tempo_control": 80.0,
        "repetition_consistency": 80.0,
        "bilateral_symmetry": 85.0
    })
    
    # Historical events for session timeline
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Active coaching & recovery tracking
    active_coaching: Optional[Dict[str, Any]] = None
    recovery_target: Optional[Dict[str, Any]] = None
    last_coaching_timestamp: float = 0.0
    cooldown_seconds: float = 5.0
    
    # Session stats
    total_interventions: int = 0
    successful_corrections: int = 0
    interventions_by_dimension: Dict[str, int] = field(default_factory=dict)
    recoveries_by_dimension: Dict[str, List[float]] = field(default_factory=dict)
    
    # Phase 3 & 4 Context Integration
    dna_primary_limiter: Optional[str] = None
    adaptive_tempo_target: Optional[str] = None


class MovementCopilotEngine:
    """
    Real-Time Biomechanical Movement Intelligence & Closed-Loop Coaching Engine.
    Operates in-memory and session-scoped with zero clinical diagnosis claims.
    """
    
    def __init__(self):
        # Session states keyed by session_id
        self._sessions: Dict[str, CopilotSessionState] = {}
    
    def get_or_create_session(
        self,
        session_id: str,
        user_id: int,
        exercise_id: str = "1",
        exercise_name: Optional[str] = None,
        dna_primary_limiter: Optional[str] = None,
        adaptive_tempo_target: Optional[str] = None
    ) -> CopilotSessionState:
        """
        Retrieves or initializes a Copilot session state for user_id.
        Enforces user ownership on existing sessions.
        """
        ex_id_str = str(exercise_id).strip()
        benchmark = EXERCISE_BENCHMARKS.get(ex_id_str, {})
        resolved_name = exercise_name or benchmark.get("name", "Exercise")
        
        if session_id in self._sessions:
            sess = self._sessions[session_id]
            # Verify user ownership
            if sess.user_id != user_id:
                raise PermissionError(f"Unauthorized session access: session '{session_id}' does not belong to user {user_id}")
            # If exercise changed, reset session exercise state
            if sess.exercise_id != ex_id_str:
                sess.exercise_id = ex_id_str
                sess.exercise_name = resolved_name
                sess.samples.clear()
                sess.rep_metrics.clear()
                sess.baseline_established = False
                sess.active_coaching = None
                sess.recovery_target = None
            if dna_primary_limiter:
                sess.dna_primary_limiter = dna_primary_limiter
            if adaptive_tempo_target:
                sess.adaptive_tempo_target = adaptive_tempo_target
            return sess
        
        # Initialize new session state
        sess = CopilotSessionState(
            session_id=session_id,
            user_id=user_id,
            exercise_id=ex_id_str,
            exercise_name=resolved_name,
            dna_primary_limiter=dna_primary_limiter,
            adaptive_tempo_target=adaptive_tempo_target
        )
        self._sessions[session_id] = sess
        return sess

    def reset_session(self, session_id: str, user_id: int, new_exercise_id: Optional[str] = None) -> bool:
        """
        Resets session state (e.g. during exercise transition or manual reset).
        """
        if session_id in self._sessions:
            sess = self._sessions[session_id]
            if sess.user_id != user_id:
                raise PermissionError(f"Unauthorized session access on reset for session '{session_id}'")
            if new_exercise_id:
                sess.exercise_id = str(new_exercise_id)
                benchmark = EXERCISE_BENCHMARKS.get(sess.exercise_id, {})
                sess.exercise_name = benchmark.get("name", "Exercise")
            sess.samples.clear()
            sess.rep_metrics.clear()
            sess.baseline_established = False
            sess.active_coaching = None
            sess.recovery_target = None
            return True
        return False

    def close_session(self, session_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Finalizes Copilot session and generates post-workout intelligence summary.
        """
        if session_id in self._sessions:
            sess = self._sessions[session_id]
            if sess.user_id != user_id:
                raise PermissionError(f"Unauthorized session access on close for session '{session_id}'")
            summary = self.get_session_summary(session_id, user_id)
            self._sessions.pop(session_id, None)
            return summary
        return None

    def process_frame_telemetry(
        self,
        session_id: str,
        user_id: int,
        exercise_id: str,
        rep_count: int,
        form_score: float,
        state: str = "START",
        primary_angle: Optional[float] = None,
        left_angle: Optional[float] = None,
        right_angle: Optional[float] = None,
        torso_angle: Optional[float] = None,
        valid: bool = True,
        feedback_code: str = "GOOD_FORM",
        dna_primary_limiter: Optional[str] = None,
        adaptive_tempo_target: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Core real-time ingestion & evaluation routine.
        Called on telemetry stream to evaluate movement quality, detect degradation,
        issue context-aware coaching, and verify closed-loop recovery.
        """
        sess = self.get_or_create_session(
            session_id=session_id,
            user_id=user_id,
            exercise_id=exercise_id,
            dna_primary_limiter=dna_primary_limiter,
            adaptive_tempo_target=adaptive_tempo_target
        )
        
        now = time.time()
        
        # 1. Create Frame Sample & append to rolling buffer
        sample = FrameTelemetrySample(
            timestamp=now,
            primary_angle=primary_angle,
            secondary_angle=None,
            left_angle=left_angle,
            right_angle=right_angle,
            torso_angle=torso_angle,
            state=state,
            rep_count=rep_count,
            valid=valid,
            feedback_code=feedback_code
        )
        sess.samples.append(sample)
        if len(sess.samples) > 60:
            sess.samples.pop(0)
        
        # 2. Check sufficient samples for rolling evaluation
        if len(sess.samples) < 5:
            return self._build_status_response(
                sess=sess,
                status="IDLE",
                message="Calibrating movement telemetry...",
                coaching_cue="Position in view and begin your set.",
                severity="INFO",
                dimension=None,
                score=0.0,
                delta=0.0
            )
        
        # 3. Compute Real-Time Rolling Metrics across recent samples
        current_metrics = self._calculate_rolling_metrics(sess)
        sess.current_metrics = current_metrics
        
        # 4. Establish / Update Baseline
        if not sess.baseline_established:
            if len(sess.samples) >= 10 or rep_count >= 1:
                sess.baseline_metrics = dict(current_metrics)
                sess.baseline_established = True
                self._record_event(sess, rep_count, "BASELINE_ESTABLISHED", "Baseline movement profile established.")
        
        # 5. Check Closed-Loop Recovery if active
        recovery_result = self._check_recovery(sess, current_metrics, rep_count)
        if recovery_result is not None:
            return recovery_result
        
        # 6. Evaluate Degradation across dimensions
        degradation = self._detect_degradation(sess, current_metrics)
        
        # 7. Check Cooldown Period
        in_cooldown = (now - sess.last_coaching_timestamp) < sess.cooldown_seconds
        
        if degradation and not in_cooldown:
            # Trigger Coaching Cue
            dim_key = degradation["dimension"]
            severity = degradation["severity"]
            score = current_metrics.get(dim_key, 70.0)
            base_score = sess.baseline_metrics.get(dim_key, 80.0)
            delta = score - base_score
            
            movement_phase = self._map_movement_phase(state)
            cue = self._generate_coaching_cue(
                exercise_id=sess.exercise_id,
                dimension=dim_key,
                phase=movement_phase,
                severity=severity,
                dna_limiter=sess.dna_primary_limiter,
                adaptive_tempo=sess.adaptive_tempo_target
            )
            
            # Record active coaching & start recovery tracking
            sess.active_coaching = {
                "dimension": dim_key,
                "dimension_label": DIMENSION_LABELS.get(dim_key, dim_key),
                "severity": severity,
                "score_at_issue": score,
                "timestamp": now,
                "rep_at_issue": rep_count,
                "cue": cue
            }
            sess.recovery_target = {
                "dimension": dim_key,
                "baseline_score": score,
                "target_score": min(100.0, score + 6.0),
                "timestamp": now,
                "rep_start": rep_count
            }
            sess.last_coaching_timestamp = now
            sess.total_interventions += 1
            sess.interventions_by_dimension[dim_key] = sess.interventions_by_dimension.get(dim_key, 0) + 1
            
            self._record_event(
                sess,
                rep_count,
                f"INTERVENTION_{severity}",
                f"{DIMENSION_LABELS.get(dim_key, dim_key)} {severity}: {cue}"
            )
            
            return self._build_status_response(
                sess=sess,
                status="WARNING" if severity != "INFO" else "INFO",
                message=f"{DIMENSION_LABELS.get(dim_key, dim_key)} is declining.",
                coaching_cue=cue,
                severity=severity,
                dimension=dim_key,
                score=score,
                previous_score=base_score,
                delta=delta,
                movement_phase=movement_phase,
                cooldown_active=False,
                recovery_tracking=True
            )
        
        # 8. Nominal State / Monitoring
        status_msg = "Movement is stable and on target."
        if sess.active_coaching and sess.recovery_target:
            status_msg = f"Monitoring correction for {DIMENSION_LABELS.get(sess.recovery_target['dimension'], '')}..."
        
        return self._build_status_response(
            sess=sess,
            status="MONITORING",
            message=status_msg,
            coaching_cue=sess.active_coaching["cue"] if (sess.active_coaching and in_cooldown) else "Maintain your form and steady cadence.",
            severity="INFO",
            dimension=sess.recovery_target["dimension"] if sess.recovery_target else None,
            score=current_metrics.get("movement_stability", 80.0),
            delta=0.0,
            movement_phase=self._map_movement_phase(state),
            cooldown_active=in_cooldown,
            recovery_tracking=bool(sess.recovery_target)
        )

    # -----------------------------------------------------------------------
    # Internal Calculation & Biomechanics Helpers
    # -----------------------------------------------------------------------
    def _calculate_rolling_metrics(self, sess: CopilotSessionState) -> Dict[str, float]:
        """
        Computes the 5 core biomechanical dimension scores over the recent sample window.
        Uses authoritative MovementAnalyzer formulas.
        """
        samples = sess.samples[-25:]  # last 25 samples
        ex_key = sess.exercise_id
        benchmark = EXERCISE_BENCHMARKS.get(ex_key, {})
        is_plank = (ex_key == "9" or benchmark.get("name") == "Plank")
        
        # 1. ROM Score
        valid_angles = [s.primary_angle for s in samples if s.valid and s.primary_angle is not None]
        _, rom_score = MovementAnalyzer.calculate_rom(valid_angles, benchmark, is_plank=is_plank)
        if not valid_angles or len(valid_angles) < 2:
            rom_score = sess.baseline_metrics.get("range_of_motion", 80.0)
            
        # 2. Stability Score
        _, stability_score = MovementAnalyzer.calculate_stability(samples, is_plank=is_plank)
        has_torso = any(s.torso_angle is not None for s in samples if s.valid)
        if not has_torso and not valid_angles:
            stability_score = sess.baseline_metrics.get("movement_stability", 80.0)
            
        # 3. Tempo Score
        duration = samples[-1].timestamp - samples[0].timestamp if len(samples) >= 2 else 0.0
        rep_delta = max(0, samples[-1].rep_count - samples[0].rep_count)
        
        if len(samples) >= 6 and duration > 0.3:
            if rep_delta > 0:
                avg_rep_sec = duration / rep_delta
            else:
                avg_rep_sec = 2.5
                
            ideal_sec = benchmark.get("ideal_rep_duration_sec", 2.5)
            if sess.adaptive_tempo_target:
                try:
                    parts = [float(p) for p in sess.adaptive_tempo_target.split("-")]
                    if len(parts) == 3:
                        ideal_sec = sum(parts)
                except Exception:
                    pass
                    
            tempo_err = abs(avg_rep_sec - ideal_sec)
            tempo_score = int(np.clip(100.0 - (tempo_err * 22.0), 20.0, 100.0))
        else:
            tempo_score = sess.baseline_metrics.get("tempo_control", 80.0)
            
        # 4. Consistency Score
        if len(sess.rep_metrics) >= 2:
            scores = [r.get("overall", 80.0) for r in sess.rep_metrics[-5:]]
            std_val = float(np.std(scores))
            consistency_score = int(np.clip(100.0 - (std_val * 3.0), 20.0, 100.0))
        else:
            consistency_score = sess.baseline_metrics.get("repetition_consistency", 80.0)
            
        # 5. Bilateral Symmetry Score
        _, sym_score = MovementAnalyzer.calculate_symmetry(samples, benchmark)
        if sym_score is None and benchmark.get("bilateral", True):
            sym_score = sess.baseline_metrics.get("bilateral_symmetry", 85.0)
            
        res = {
            "range_of_motion": round(float(rom_score), 1),
            "movement_stability": round(float(stability_score), 1),
            "tempo_control": round(float(tempo_score), 1),
            "repetition_consistency": round(float(consistency_score), 1)
        }
        if sym_score is not None:
            res["bilateral_symmetry"] = round(float(sym_score), 1)
        return res

    def _detect_degradation(
        self,
        sess: CopilotSessionState,
        current_metrics: Dict[str, float]
    ) -> Optional[Dict[str, Any]]:
        """
        Detects meaningful degradation across dimensions compared to baseline.
        Prioritizes the dimension with the largest negative drop.
        """
        if not sess.baseline_established:
            return None
            
        worst_dim = None
        worst_delta = 0.0
        worst_severity = None
        
        for dim, cur_val in current_metrics.items():
            base_val = sess.baseline_metrics.get(dim, 80.0)
            delta = cur_val - base_val
            
            # Heighten sensitivity if this is the user's Movement DNA limiter
            threshold_mod = 2.0 if sess.dna_primary_limiter == dim else 0.0
            
            # Degradation thresholds
            if delta <= (-20.0 + threshold_mod) or cur_val < 50.0:
                severity = "CRITICAL"
            elif delta <= (-10.0 + threshold_mod) or cur_val < 65.0:
                severity = "WARNING"
            elif delta <= (-6.0 + threshold_mod):
                severity = "INFO"
            else:
                continue
                
            if delta < worst_delta:
                worst_delta = delta
                worst_dim = dim
                worst_severity = severity
                
        if worst_dim and worst_severity:
            return {
                "dimension": worst_dim,
                "severity": worst_severity,
                "delta": worst_delta
            }
        return None

    def _check_recovery(
        self,
        sess: CopilotSessionState,
        current_metrics: Dict[str, float],
        rep_count: int
    ) -> Optional[Dict[str, Any]]:
        """
        Closed-loop recovery verification.
        Tests if the user corrected their movement on the affected dimension.
        """
        target = sess.recovery_target
        if not target:
            return None
            
        dim = target["dimension"]
        baseline_score = target["baseline_score"]
        current_score = current_metrics.get(dim, baseline_score)
        
        # Check if score improved by at least +5.0 points or +8%
        score_gain = current_score - baseline_score
        pct_gain = (score_gain / max(baseline_score, 1.0)) * 100.0
        
        if score_gain >= 5.0 or pct_gain >= 8.0:
            # Recovery confirmed!
            dim_label = DIMENSION_LABELS.get(dim, dim)
            sess.successful_corrections += 1
            if dim not in sess.recoveries_by_dimension:
                sess.recoveries_by_dimension[dim] = []
            sess.recoveries_by_dimension[dim].append(score_gain)
            
            msg = "Movement recovered."
            cue = f"Great correction! Your {dim_label} improved +{score_gain:.1f} pts (+{pct_gain:.1f}%)."
            
            self._record_event(sess, rep_count, "RECOVERY_CONFIRMED", f"✓ {dim_label} recovered (+{pct_gain:.1f}%)")
            
            # Clear recovery state & start cooldown
            sess.recovery_target = None
            sess.active_coaching = None
            sess.last_coaching_timestamp = time.time()
            
            return self._build_status_response(
                sess=sess,
                status="RECOVERED",
                message=msg,
                coaching_cue=cue,
                severity="INFO",
                dimension=dim,
                score=current_score,
                previous_score=baseline_score,
                delta=score_gain,
                movement_phase="RECOVERY",
                cooldown_active=True,
                recovery_tracking=False
            )
        return None

    def _generate_coaching_cue(
        self,
        exercise_id: str,
        dimension: str,
        phase: str = "DEFAULT",
        severity: str = "WARNING",
        dna_limiter: Optional[str] = None,
        adaptive_tempo: Optional[str] = None
    ) -> str:
        """
        Generates contextual, exercise-specific coaching cue.
        """
        ex_matrix = EXERCISE_COACHING_MATRIX.get(str(exercise_id), EXERCISE_COACHING_MATRIX.get("2", {}))
        dim_cues = ex_matrix.get(dimension, {})
        
        # Check phase-specific cue
        cue = dim_cues.get(phase, dim_cues.get("DEFAULT"))
        if not cue:
            cue = f"Focus on maintaining proper {DIMENSION_LABELS.get(dimension, dimension)}."
            
        # Add severity / context prefix if applicable
        if dimension == "tempo_control" and adaptive_tempo:
            return f"You're moving faster than today's {adaptive_tempo} tempo target. {cue}"
        elif dimension == dna_limiter:
            return f"Movement DNA limiter alert: {cue}"
        elif severity == "CRITICAL":
            return f"Form alert: {cue} Reset your stance before the next rep."
        return cue

    def _map_movement_phase(self, state: str) -> str:
        """
        Maps tracker state to canonical biomechanical phase.
        """
        s = str(state).upper()
        if any(w in s for w in ["DOWN", "ECCENTRIC", "DESCENDING", "LOWERING"]):
            return "DESCENT"
        elif any(w in s for w in ["UP", "CONCENTRIC", "ASCENDING", "RAISING"]):
            return "ASCENT"
        elif any(w in s for w in ["BOTTOM", "INFLECTION", "DEEP"]):
            return "INFLECTION"
        elif any(w in s for w in ["TOP", "PEAK", "LOCK"]):
            return "PEAK"
        elif any(w in s for w in ["HOLD", "PLANK"]):
            return "HOLD"
        return "PREPARE"

    def _record_event(self, sess: CopilotSessionState, rep: int, event_type: str, message: str):
        """
        Appends a structured event to the session event timeline.
        """
        event = {
            "timestamp": time.time(),
            "rep": rep,
            "type": event_type,
            "message": message
        }
        sess.events.append(event)
        if len(sess.events) > 20:
            sess.events.pop(0)

    def _build_status_response(
        self,
        sess: CopilotSessionState,
        status: str,
        message: str,
        coaching_cue: str,
        severity: str = "INFO",
        dimension: Optional[str] = None,
        score: float = 0.0,
        previous_score: float = 0.0,
        delta: float = 0.0,
        movement_phase: str = "PREPARE",
        cooldown_active: bool = False,
        recovery_tracking: bool = False
    ) -> Dict[str, Any]:
        """
        Builds authoritative, formatted response for the frontend Copilot HUD.
        """
        dim_label = DIMENSION_LABELS.get(dimension, dimension) if dimension else "Overall Movement"
        pct_change = (delta / max(previous_score, 1.0)) * 100.0 if previous_score > 0 else 0.0
        
        return {
            "status": status,
            "active": status in ["WARNING", "CRITICAL", "RECOVERED"],
            "exercise": sess.exercise_name,
            "dimension": dimension,
            "dimension_label": dim_label,
            "severity": severity,
            "score": round(float(score), 1),
            "previous_score": round(float(previous_score), 1),
            "delta": round(float(delta), 1),
            "pct_change": round(float(pct_change), 1),
            "message": message,
            "coaching_cue": coaching_cue,
            "movement_phase": movement_phase,
            "cooldown_active": cooldown_active,
            "recovery_tracking": recovery_tracking,
            "current_metrics": sess.current_metrics,
            "recent_events": sess.events[-5:]
        }

    def get_session_summary(self, session_id: str, user_id: int) -> Dict[str, Any]:
        """
        Generates deterministic post-workout session intelligence summary.
        """
        sess = self._sessions.get(session_id)
        if not sess or sess.user_id != user_id:
            return {
                "session_id": session_id,
                "total_interventions": 0,
                "successful_corrections": 0,
                "recovery_rate_pct": 0.0,
                "biggest_recovery": None,
                "most_frequent_limiter": None,
                "verdict": "No Copilot telemetry was recorded for this session."
            }
            
        interventions = sess.total_interventions
        corrections = sess.successful_corrections
        rate = round((corrections / max(interventions, 1)) * 100.0, 1) if interventions > 0 else 100.0
        
        # Identify biggest recovery
        biggest_rec = None
        max_gain = 0.0
        for dim, gains in sess.recoveries_by_dimension.items():
            if gains:
                avg_g = float(np.mean(gains))
                if avg_g > max_gain:
                    max_gain = avg_g
                    biggest_rec = {
                        "dimension": dim,
                        "label": DIMENSION_LABELS.get(dim, dim),
                        "gain_pts": round(max_gain, 1)
                    }
                    
        # Identify most frequent limiter
        freq_limiter = None
        if sess.interventions_by_dimension:
            sorted_dims = sorted(sess.interventions_by_dimension.items(), key=lambda x: x[1], reverse=True)
            freq_limiter = {
                "dimension": sorted_dims[0][0],
                "label": DIMENSION_LABELS.get(sorted_dims[0][0], sorted_dims[0][0]),
                "count": sorted_dims[0][1]
            }
            
        # Formulate deterministic verdict
        if interventions == 0:
            verdict = "Flawless movement consistency throughout your set. No biomechanical degradation detected."
        elif rate >= 80.0:
            verdict = f"Outstanding responsiveness. You corrected {corrections} of {interventions} form cues immediately."
        elif rate >= 50.0:
            verdict = f"Good coachability. You recovered on {corrections} form corrections. Continue focusing on {freq_limiter['label'] if freq_limiter else 'movement stability'}."
        else:
            verdict = f"Fatigue was observed across {interventions} cues. Focus on controlled eccentric pacing in your next session."
            
        return {
            "session_id": session_id,
            "exercise_name": sess.exercise_name,
            "total_interventions": interventions,
            "successful_corrections": corrections,
            "recovery_rate_pct": rate,
            "biggest_recovery": biggest_rec,
            "most_frequent_limiter": freq_limiter,
            "verdict": verdict,
            "events_count": len(sess.events)
        }


# Singleton Engine Instance
movement_copilot_engine = MovementCopilotEngine()
