from typing import Tuple 
"""
FitQuest Human Movement Intelligence Engine — Phase 4: Movement DNA™ Service

Provides deterministic, explainable, and longitudinal Movement DNA™ profiling
derived from the user's persistent movement_fingerprints history.

Five Biomechanical Dimensions:
1. Range of Motion (ROM)
2. Movement Stability
3. Tempo Control
4. Repetition Consistency
5. Bilateral Symmetry

Core Capabilities:
- Longitudinal Baseline (first 1-2 sessions) vs Recent Average (last 3 sessions)
- Overall Longitudinal Average
- Absolute Metric Delta (ΔM) & Percentage Improvement (Δ%)
- Improvement Velocity (rate of change per session)
- Directional Trend Vector (IMPROVING / STABLE / DECLINING / INSUFFICIENT DATA)
- Strongest Characteristic & Primary/Secondary Movement Limiters
- Explainable AI Movement Report (Deterministic non-clinical insights)
- Direct Integration with Phase 3 Adaptive Training Engine
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.models.movement_fingerprint import MovementFingerprintModel
from backend.models.exercise import ExerciseModel

logger = logging.getLogger(__name__)

# Performance Classification Thresholds
METRIC_THRESHOLDS = {
    "STRONG": 80.0,
    "ADEQUATE": 65.0,
    "NEEDS_ATTENTION": 50.0,
    # Below 50.0 is HIGH_PRIORITY
}

DIMENSION_LABELS = {
    "range_of_motion": "Range of Motion",
    "movement_stability": "Movement Stability",
    "tempo_control": "Tempo Control",
    "repetition_consistency": "Repetition Consistency",
    "bilateral_symmetry": "Bilateral Symmetry"
}


class MovementDNAService:
    """
    Service Layer computing deterministic longitudinal Movement DNA profiles.
    """

    @staticmethod
    def get_user_movement_dna(
        db: Session,
        user_id: int,
        exercise_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Computes the complete Movement DNA™ profile for the authenticated user.
        Strictly deterministic, explainable, and scoped to user_id.
        """
        # 1. Fetch chronological fingerprints for the user
        query = db.query(MovementFingerprintModel).filter(
            MovementFingerprintModel.user_id == user_id
        )
        if exercise_id is not None:
            query = query.filter(MovementFingerprintModel.exercise_id == exercise_id)

        # Order chronologically ascending (earliest to latest)
        fingerprints: List[MovementFingerprintModel] = query.order_by(
            MovementFingerprintModel.created_at.asc()
        ).limit(100).all()

        n_sessions = len(fingerprints)

        # 2. Handle Zero History (Empty State)
        if n_sessions == 0:
            return MovementDNAService._build_empty_dna_profile()

        # 3. Partition Baseline and Recent
        if n_sessions == 1:
            baseline_fps = fingerprints
            recent_fps = fingerprints
        elif n_sessions in (2, 3):
            baseline_fps = fingerprints[:1]
            recent_fps = fingerprints[1:]
        else:
            baseline_fps = fingerprints[:2]
            recent_fps = fingerprints[-3:]

        # 4. Compute Dimension Averages
        dimensions_data: Dict[str, Dict[str, Any]] = {}
        dimension_keys = [
            "range_of_motion",
            "movement_stability",
            "tempo_control",
            "repetition_consistency",
            "bilateral_symmetry"
        ]

        recent_scores: Dict[str, float] = {}

        for key in dimension_keys:
            # Extract raw values
            all_vals = [getattr(fp, key) for fp in fingerprints if getattr(fp, key) is not None]
            base_vals = [getattr(fp, key) for fp in baseline_fps if getattr(fp, key) is not None]
            rec_vals = [getattr(fp, key) for fp in recent_fps if getattr(fp, key) is not None]

            if not all_vals:
                # E.g. Bilateral symmetry on unilateral exercises
                dimensions_data[key] = {
                    "key": key,
                    "label": DIMENSION_LABELS[key],
                    "score": None,
                    "baseline": None,
                    "recent": None,
                    "overall_avg": None,
                    "delta": 0.0,
                    "pct_change": 0.0,
                    "velocity": 0.0,
                    "status": "N/A",
                    "trend": "INSUFFICIENT DATA",
                    "interpretation": "Bilateral symmetry is not applicable for unilateral movements."
                }
                continue

            base_avg = round(sum(base_vals) / len(base_vals), 1) if base_vals else 0.0
            rec_avg = round(sum(rec_vals) / len(rec_vals), 1) if rec_vals else 0.0
            overall_avg = round(sum(all_vals) / len(all_vals), 1)

            # Store recent score for ranking
            recent_scores[key] = rec_avg

            # Trend & Delta Calculations
            if n_sessions < 2:
                delta = 0.0
                pct_change = 0.0
                velocity = 0.0
                trend = "INSUFFICIENT DATA"
            else:
                delta = round(rec_avg - base_avg, 1)
                pct_change = round((delta / base_avg * 100.0), 1) if base_avg > 0 else 0.0
                velocity = round(delta / max(n_sessions - 1, 1), 2)
                if delta >= 3.0:
                    trend = "IMPROVING"
                elif delta <= -3.0:
                    trend = "DECLINING"
                else:
                    trend = "STABLE"

            status = MovementDNAService._classify_metric_status(rec_avg)
            interpretation = MovementDNAService._generate_dimension_interpretation(key, rec_avg, delta, trend, status)

            dimensions_data[key] = {
                "key": key,
                "label": DIMENSION_LABELS[key],
                "score": rec_avg,
                "baseline": base_avg,
                "recent": rec_avg,
                "overall_avg": overall_avg,
                "delta": delta,
                "pct_change": pct_change,
                "velocity": velocity,
                "status": status,
                "trend": trend,
                "interpretation": interpretation
            }

        # 5. Overall Movement DNA Score & Overall Trend
        valid_rec_scores = [v for v in recent_scores.values() if v is not None]
        overall_score = round(sum(valid_rec_scores) / len(valid_rec_scores), 1) if valid_rec_scores else 0.0

        all_overall_scores = [fp.overall_movement_quality for fp in fingerprints if fp.overall_movement_quality is not None]
        base_overall = round(sum([fp.overall_movement_quality for fp in baseline_fps]) / len(baseline_fps), 1) if baseline_fps else overall_score
        rec_overall = round(sum([fp.overall_movement_quality for fp in recent_fps]) / len(recent_fps), 1) if recent_fps else overall_score

        if n_sessions < 2:
            overall_delta = 0.0
            overall_pct_change = 0.0
            overall_velocity = 0.0
            overall_trend = "INSUFFICIENT DATA"
        else:
            overall_delta = round(rec_overall - base_overall, 1)
            overall_pct_change = round((overall_delta / base_overall * 100.0), 1) if base_overall > 0 else 0.0
            overall_velocity = round(overall_delta / max(n_sessions - 1, 1), 2)
            if overall_delta >= 3.0:
                overall_trend = "IMPROVING"
            elif overall_delta <= -3.0:
                overall_trend = "DECLINING"
            else:
                overall_trend = "STABLE"

        # 6. Identify Strongest Dimension and Primary/Secondary Limiters
        sorted_dimensions = sorted(recent_scores.items(), key=lambda item: item[1], reverse=True)

        strongest_key = sorted_dimensions[0][0] if sorted_dimensions else "range_of_motion"
        strongest_score = recent_scores.get(strongest_key, 0.0)

        primary_limiter_key = sorted_dimensions[-1][0] if sorted_dimensions else "movement_stability"
        primary_limiter_score = recent_scores.get(primary_limiter_key, 0.0)

        secondary_limiter_key = sorted_dimensions[-2][0] if len(sorted_dimensions) >= 2 else primary_limiter_key
        secondary_limiter_score = recent_scores.get(secondary_limiter_key, 0.0)

        # 7. Confidence Tier
        if n_sessions <= 1:
            confidence = "Low"
            confidence_reason = "Baseline established from 1 recorded session. Complete more workouts to unlock full longitudinal trajectory."
        elif n_sessions <= 3:
            confidence = "Moderate"
            confidence_reason = f"Derived from {n_sessions} recorded movement sessions with initial trend vectors."
        else:
            confidence = "High"
            confidence_reason = f"High confidence profile calculated from {n_sessions} longitudinal movement sessions."

        # 8. Limiter Explanations & Adaptive Training Binding
        why_matters, ai_response = MovementDNAService._explain_limiter(primary_limiter_key, primary_limiter_score)

        # 9. Structured Timeline Points for Canvas Charting
        timeline = []
        for fp in fingerprints:
            timeline.append({
                "session_id": fp.workout_session_id or fp.id,
                "date": fp.created_at.isoformat() if fp.created_at else datetime.now(timezone.utc).isoformat(),
                "exercise_name": fp.exercise_name or "Exercise",
                "exercise_id": fp.exercise_id,
                "overall": fp.overall_movement_quality,
                "range_of_motion": fp.range_of_motion,
                "movement_stability": fp.movement_stability,
                "tempo_control": fp.tempo_control,
                "repetition_consistency": fp.repetition_consistency,
                "bilateral_symmetry": fp.bilateral_symmetry
            })

        # 10. Explainable AI Movement Report
        ai_report = MovementDNAService._generate_ai_report(
            strongest_key, strongest_score,
            primary_limiter_key, primary_limiter_score,
            dimensions_data, overall_trend, overall_delta, overall_pct_change, n_sessions
        )

        return {
            "overall_score": overall_score,
            "total_sessions_analyzed": n_sessions,
            "confidence": confidence,
            "confidence_reason": confidence_reason,
            "strongest_dimension": {
                "key": strongest_key,
                "label": DIMENSION_LABELS[strongest_key],
                "score": strongest_score,
                "status": MovementDNAService._classify_metric_status(strongest_score)
            },
            "primary_limiter": {
                "key": primary_limiter_key,
                "label": DIMENSION_LABELS[primary_limiter_key],
                "score": primary_limiter_score,
                "status": MovementDNAService._classify_metric_status(primary_limiter_score),
                "why_it_matters": why_matters,
                "ai_response": ai_response
            },
            "secondary_limiter": {
                "key": secondary_limiter_key,
                "label": DIMENSION_LABELS[secondary_limiter_key],
                "score": secondary_limiter_score,
                "status": MovementDNAService._classify_metric_status(secondary_limiter_score)
            },
            "trend": {
                "direction": overall_trend,
                "delta": overall_delta,
                "pct_change": overall_pct_change,
                "velocity_per_session": overall_velocity
            },
            "dimensions": dimensions_data,
            "timeline": timeline,
            "ai_report": ai_report,
            "adaptive_action": {
                "endpoint": "/api/v1/adaptive-training/generate",
                "primary_focus": primary_limiter_key,
                "recommended_title": f"Adaptive Session: {DIMENSION_LABELS[primary_limiter_key]} Focus"
            }
        }

    @staticmethod
    def _classify_metric_status(score: Optional[float]) -> str:
        if score is None:
            return "N/A"
        if score >= METRIC_THRESHOLDS["STRONG"]:
            return "STRONG"
        elif score >= METRIC_THRESHOLDS["ADEQUATE"]:
            return "ADEQUATE"
        elif score >= METRIC_THRESHOLDS["NEEDS_ATTENTION"]:
            return "NEEDS ATTENTION"
        else:
            return "HIGH PRIORITY"

    @staticmethod
    def _generate_dimension_interpretation(
        key: str,
        score: float,
        delta: float,
        trend: str,
        status: str
    ) -> str:
        """Generates deterministic non-clinical interpretation for dimension card."""
        label = DIMENSION_LABELS.get(key, key)
        if key == "range_of_motion":
            if status == "STRONG":
                return "Consistently achieving full biomechanical joint excursion through target depth."
            elif status == "ADEQUATE":
                return "Good joint excursion with minor depth reductions under repetition fatigue."
            else:
                return "Joint excursion is shortened; focus on deep controlled stretch through full range."

        elif key == "movement_stability":
            if status == "STRONG":
                return "Excellent core stiffness and minimal joint jitter during active repetitions."
            elif status == "ADEQUATE":
                return "Moderate stability with slight torso sway during peak eccentric-concentric transition."
            else:
                return "Higher angular velocity variance observed; prioritize joint locking and core stabilization."

        elif key == "tempo_control":
            if status == "STRONG":
                return "Smooth, controlled cadence rhythm across both concentric and eccentric phases."
            elif status == "ADEQUATE":
                return "Steady tempo with slight cadence acceleration on late set repetitions."
            else:
                return "Fast eccentric descent observed; slow down the lowering phase (e.g. 3-second descent)."

        elif key == "repetition_consistency":
            if status == "STRONG":
                return "Uniform rep-to-rep kinematic trajectory with low coefficient of variation."
            elif status == "ADEQUATE":
                return "Consistent movement patterns with minor rep-to-rep speed variances."
            else:
                return "High rep-to-rep variability; focus on identical cadence and path on every repetition."

        elif key == "bilateral_symmetry":
            if status == "STRONG":
                return "Symmetrical left and right joint kinematics and balanced bilateral load distribution."
            elif status == "ADEQUATE":
                return "Minor bilateral disparity within normal functional movement variance."
            else:
                return "Asymmetric joint angles detected; focus on balanced left and right side force output."

        return f"{label} currently performing at {status.lower()} movement quality."

    @staticmethod
    def _explain_limiter(key: str, score: float) -> Tuple[str, str]:
        """Provides non-clinical 'Why This Matters' and 'AI Response' for primary limiter."""
        if key == "tempo_control":
            why = "Inconsistent or rushed eccentric tempo reduces muscle time-under-tension and relies on momentum rather than controlled muscular deceleration."
            response = "Prescribing elongated 3-1-2 eccentric descent tempos and cadence audio-visual cues to restore full pacing control."
        elif key == "movement_stability":
            why = "Joint jitter and torso sway indicate compensatory recruitment under load, reducing movement efficiency and force transfer."
            response = "Prescribing stabilization-focused exercises (Planks, Glute Bridges) and joint-locking cues during active sets."
        elif key == "range_of_motion":
            why = "Shortened joint excursions limit full-muscle recruitment and active mobility at end ranges."
            response = "Prescribing full-excursion drills with 2-second isometric peak holds to expand active joint depth."
        elif key == "repetition_consistency":
            why = "High rep-to-rep variance suggests premature fatigue or loss of movement rhythm between early and late set repetitions."
            response = "Prescribing manageable volume blocks with strict pacing metronomes to build repeatable motor patterns."
        elif key == "bilateral_symmetry":
            why = "Disproportionate left/right load distribution can reinforce unilateral dominance and kinematic imbalance."
            response = "Prescribing bilateral balance cues and symmetric pressing/squatting drills with synchronized lockouts."
        else:
            why = "Identified as your lowest relative dimension score across historical workouts."
            response = "Calibrating next adaptive training session to prioritize this movement dimension."

        return why, response

    @staticmethod
    def _generate_ai_report(
        strongest_key: str,
        strongest_score: float,
        limiter_key: str,
        limiter_score: float,
        dimensions: Dict[str, Any],
        overall_trend: str,
        overall_delta: float,
        overall_pct_change: float,
        n_sessions: int
    ) -> Dict[str, str]:
        """Generates deterministic, structured 5-part AI Movement Report."""
        strong_label = DIMENSION_LABELS.get(strongest_key, strongest_key)
        limiter_label = DIMENSION_LABELS.get(limiter_key, limiter_key)

        what_well = f"Your {strong_label} is your highest-scoring movement characteristic at {strongest_score:.1f}/100, demonstrating consistent biomechanical execution."

        what_limiting = f"{limiter_label} ({limiter_score:.1f}/100) is your primary limiting factor, exhibiting the largest opportunity for technique refinement."

        if n_sessions < 2:
            what_changed = "Baseline movement telemetry recorded. Complete additional sessions to establish longitudinal improvement velocity."
        elif overall_trend == "IMPROVING":
            what_changed = f"Overall movement quality has improved by +{overall_delta:.1f} pts (+{overall_pct_change:.1f}%) across your recent training sessions."
        elif overall_trend == "DECLINING":
            what_changed = f"Movement quality dipped by {overall_delta:.1f} pts ({overall_pct_change:.1f}%), suggesting potential fatigue or rushed execution."
        else:
            what_changed = f"Movement quality remains stable across sessions with steady cadence and form retention."

        what_recommends = f"Focus on stabilizing your {limiter_label.lower()} by controlling your repetition tempo and eliminating momentum."

        next_step = f"Click 'Generate Adaptive Workout' to launch a custom routine calibrated to reinforce your {limiter_label.lower()}."

        return {
            "what_you_do_well": what_well,
            "what_is_limiting_you": what_limiting,
            "what_changed": what_changed,
            "what_fitquest_recommends": what_recommends,
            "next_step": next_step
        }

    @staticmethod
    def _build_empty_dna_profile() -> Dict[str, Any]:
        """Structured default profile for users with zero workout history."""
        empty_dim = {
            "score": 0.0, "baseline": 0.0, "recent": 0.0, "overall_avg": 0.0,
            "delta": 0.0, "pct_change": 0.0, "velocity": 0.0,
            "status": "N/A", "trend": "INSUFFICIENT DATA",
            "interpretation": "No recorded movement data. Complete your first workout to establish your Movement DNA."
        }
        dimensions = {
            k: {**empty_dim, "key": k, "label": DIMENSION_LABELS[k]}
            for k in DIMENSION_LABELS
        }

        return {
            "overall_score": 0.0,
            "total_sessions_analyzed": 0,
            "confidence": "Low",
            "confidence_reason": "No recorded workout history. Complete your first workout to establish your Movement DNA.",
            "strongest_dimension": {"key": "range_of_motion", "label": "Range of Motion", "score": 0.0, "status": "N/A"},
            "primary_limiter": {
                "key": "movement_stability", "label": "Movement Stability", "score": 0.0, "status": "N/A",
                "why_it_matters": "Movement DNA is established after your first workout session.",
                "ai_response": "Complete any workout to begin automated movement decoding."
            },
            "secondary_limiter": {"key": "tempo_control", "label": "Tempo Control", "score": 0.0, "status": "N/A"},
            "trend": {"direction": "INSUFFICIENT DATA", "delta": 0.0, "pct_change": 0.0, "velocity_per_session": 0.0},
            "dimensions": dimensions,
            "timeline": [],
            "ai_report": {
                "what_you_do_well": "Complete your first workout to reveal your movement strengths.",
                "what_is_limiting_you": "No movement limiters detected yet.",
                "what_changed": "Awaiting initial movement baseline data.",
                "what_fitquest_recommends": "Select any single exercise or structured routine to begin.",
                "next_step": "Start a workout session with your webcam enabled."
            },
            "adaptive_action": {
                "endpoint": "/api/v1/adaptive-training/generate",
                "primary_focus": "movement_stability",
                "recommended_title": "Adaptive Session: Baseline Calibration"
            }
        }


# Global Singleton
movement_dna_service = MovementDNAService()
