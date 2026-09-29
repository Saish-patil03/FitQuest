import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models.movement_fingerprint import MovementFingerprintModel
from backend.models.exercise import ExerciseModel

logger = logging.getLogger(__name__)

class MovementFingerprintService:
    """
    Service Layer for persisting and analyzing longitudinal Movement Fingerprints
    and Movement Evolution trajectories across workout sessions.
    """

    @staticmethod
    def save_fingerprint(
        db: Session,
        user_id: int,
        exercise_id: int,
        exercise_name: str,
        movement_intelligence: Dict[str, Any],
        workout_session_id: Optional[int] = None,
        form_score: float = 100.0,
        repetition_count: int = 0,
        session_duration: int = 0
    ) -> Optional[MovementFingerprintModel]:
        """
        Safely extracts numerical biomechanical metrics from Movement Intelligence telemetry
        and persists a MovementFingerprintModel record to the database.
        Ensures idempotent deduplication per workout_session_id.
        """
        try:
            # 1. Deduplication: Prevent duplicate records for the same workout session
            if workout_session_id:
                existing = db.query(MovementFingerprintModel).filter(
                    MovementFingerprintModel.workout_session_id == workout_session_id
                ).first()
                if existing:
                    return existing

            # 2. Extract metrics from Movement Signature
            sig = movement_intelligence.get("movement_signature", {}) if movement_intelligence else {}
            
            rom = float(sig.get("rom_score", 0.0) or 0.0)
            stability = float(sig.get("stability_score", 0.0) or 0.0)
            tempo = float(sig.get("tempo_score", 0.0) or 0.0)
            consistency = float(sig.get("consistency_score", 0.0) or 0.0)
            symmetry_val = sig.get("symmetry_score")
            symmetry = float(symmetry_val) if symmetry_val is not None else None
            quality = float(sig.get("movement_quality_score", 0.0) or 0.0)

            # 3. Create Model Instance
            fingerprint = MovementFingerprintModel(
                user_id=user_id,
                workout_session_id=workout_session_id,
                exercise_id=exercise_id,
                exercise_name=exercise_name or "Exercise",
                range_of_motion=round(rom, 1),
                movement_stability=round(stability, 1),
                tempo_control=round(tempo, 1),
                repetition_consistency=round(consistency, 1),
                bilateral_symmetry=round(symmetry, 1) if symmetry is not None else None,
                overall_movement_quality=round(quality, 1),
                form_score=round(float(form_score), 1),
                repetition_count=int(repetition_count),
                session_duration=int(session_duration),
                created_at=datetime.now(timezone.utc)
            )

            db.add(fingerprint)
            db.commit()
            db.refresh(fingerprint)
            return fingerprint

        except Exception as e:
            db.rollback()
            logger.error(f"[MovementFingerprintService] Failed to persist movement fingerprint: {e}", exc_info=True)
            return None

    @staticmethod
    def get_user_fingerprints(
        db: Session,
        user_id: int,
        exercise_id: Optional[int] = None,
        limit: int = 50
    ) -> List[MovementFingerprintModel]:
        """
        Retrieves historical movement fingerprints strictly scoped to the authenticated user.
        """
        query = db.query(MovementFingerprintModel).filter(
            MovementFingerprintModel.user_id == user_id
        )
        if exercise_id is not None:
            query = query.filter(MovementFingerprintModel.exercise_id == exercise_id)
        
        return query.order_by(MovementFingerprintModel.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_session_fingerprint(
        db: Session,
        session_id: int,
        user_id: int
    ) -> Optional[MovementFingerprintModel]:
        """
        Retrieves a single movement fingerprint linked to a workout session for authenticated user.
        """
        return db.query(MovementFingerprintModel).filter(
            MovementFingerprintModel.workout_session_id == session_id,
            MovementFingerprintModel.user_id == user_id
        ).first()

    @staticmethod
    def get_exercise_history(
        db: Session,
        user_id: int,
        exercise_id: int
    ) -> List[MovementFingerprintModel]:
        """
        Retrieves chronological history of fingerprints for a specific exercise and user.
        """
        return db.query(MovementFingerprintModel).filter(
            MovementFingerprintModel.user_id == user_id,
            MovementFingerprintModel.exercise_id == exercise_id
        ).order_by(MovementFingerprintModel.created_at.asc()).all()

    @staticmethod
    def calculate_evolution(
        db: Session,
        user_id: int,
        exercise_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Computes longitudinal Movement Evolution comparing Baseline vs Latest performance,
        calculating metric trends (improving/stable/declining), and providing deterministic insights.
        """
        # 1. Resolve exercise target
        target_exercise = None
        if exercise_id is not None:
            target_exercise = db.query(ExerciseModel).filter(ExerciseModel.id == exercise_id).first()
        
        if not target_exercise:
            # Pick user's most practiced exercise or default to first available
            fav = db.query(
                MovementFingerprintModel.exercise_id,
                func.count(MovementFingerprintModel.id).label("cnt")
            ).filter(
                MovementFingerprintModel.user_id == user_id
            ).group_by(
                MovementFingerprintModel.exercise_id
            ).order_by(
                func.count(MovementFingerprintModel.id).desc()
            ).first()

            if fav:
                target_exercise = db.query(ExerciseModel).filter(ExerciseModel.id == fav.exercise_id).first()
            else:
                target_exercise = db.query(ExerciseModel).first()

        ex_id = target_exercise.id if target_exercise else (exercise_id or 1)
        ex_name = target_exercise.name if target_exercise else "Exercise"

        # 2. Fetch chronological history
        history = MovementFingerprintService.get_exercise_history(db, user_id, ex_id)
        num_sessions = len(history)

        # 3. Handle Empty History (0 sessions)
        if num_sessions == 0:
            return {
                "exercise_id": ex_id,
                "exercise_name": ex_name,
                "sessions_analyzed": 0,
                "overall": {
                    "initial": 0.0,
                    "latest": 0.0,
                    "change": 0.0,
                    "change_pct": 0.0,
                    "trend": "baseline"
                },
                "metrics": {
                    "rom": {"initial": 0.0, "latest": 0.0, "change": 0.0, "change_pct": 0.0, "trend": "baseline", "available": False},
                    "stability": {"initial": 0.0, "latest": 0.0, "change": 0.0, "change_pct": 0.0, "trend": "baseline", "available": False},
                    "tempo": {"initial": 0.0, "latest": 0.0, "change": 0.0, "change_pct": 0.0, "trend": "baseline", "available": False},
                    "consistency": {"initial": 0.0, "latest": 0.0, "change": 0.0, "change_pct": 0.0, "trend": "baseline", "available": False},
                    "symmetry": {"initial": None, "latest": None, "change": 0.0, "change_pct": 0.0, "trend": "baseline", "available": False}
                },
                "baseline_signature": {
                    "rom_score": 0, "stability_score": 0, "tempo_score": 0, "consistency_score": 0, "symmetry_score": None, "movement_quality_score": 0
                },
                "current_signature": {
                    "rom_score": 0, "stability_score": 0, "tempo_score": 0, "consistency_score": 0, "symmetry_score": None, "movement_quality_score": 0
                },
                "timeline": [],
                "ai_insight": f"No movement history recorded yet for {ex_name}. Complete your first workout session to establish your baseline Movement Fingerprint.",
                "recommendations": [
                    "Perform a complete set to begin tracking your movement quality trajectory.",
                    "Focus on controlled repetitions with consistent depth and pacing."
                ]
            }

        # 4. Handle 1 Session (Baseline established)
        if num_sessions == 1:
            fp = history[0]
            base_sig = {
                "rom_score": round(fp.range_of_motion),
                "stability_score": round(fp.movement_stability),
                "tempo_score": round(fp.tempo_control),
                "consistency_score": round(fp.repetition_consistency),
                "symmetry_score": round(fp.bilateral_symmetry) if fp.bilateral_symmetry is not None else None,
                "movement_quality_score": round(fp.overall_movement_quality)
            }
            return {
                "exercise_id": ex_id,
                "exercise_name": ex_name,
                "sessions_analyzed": 1,
                "overall": {
                    "initial": round(fp.overall_movement_quality, 1),
                    "latest": round(fp.overall_movement_quality, 1),
                    "change": 0.0,
                    "change_pct": 0.0,
                    "trend": "baseline"
                },
                "metrics": {
                    "rom": {"initial": round(fp.range_of_motion, 1), "latest": round(fp.range_of_motion, 1), "change": 0.0, "change_pct": 0.0, "trend": "baseline", "available": True},
                    "stability": {"initial": round(fp.movement_stability, 1), "latest": round(fp.movement_stability, 1), "change": 0.0, "change_pct": 0.0, "trend": "baseline", "available": True},
                    "tempo": {"initial": round(fp.tempo_control, 1), "latest": round(fp.tempo_control, 1), "change": 0.0, "change_pct": 0.0, "trend": "baseline", "available": True},
                    "consistency": {"initial": round(fp.repetition_consistency, 1), "latest": round(fp.repetition_consistency, 1), "change": 0.0, "change_pct": 0.0, "trend": "baseline", "available": True},
                    "symmetry": {
                        "initial": round(fp.bilateral_symmetry, 1) if fp.bilateral_symmetry is not None else None,
                        "latest": round(fp.bilateral_symmetry, 1) if fp.bilateral_symmetry is not None else None,
                        "change": 0.0,
                        "change_pct": 0.0,
                        "trend": "baseline",
                        "available": fp.bilateral_symmetry is not None
                    }
                },
                "baseline_signature": base_sig,
                "current_signature": base_sig,
                "timeline": [
                    {
                        "session_index": 1,
                        "session_id": fp.workout_session_id,
                        "date": fp.created_at.strftime("%b %d") if fp.created_at else "Session 1",
                        "quality": round(fp.overall_movement_quality, 1),
                        "rom": round(fp.range_of_motion, 1),
                        "stability": round(fp.movement_stability, 1),
                        "tempo": round(fp.tempo_control, 1),
                        "consistency": round(fp.repetition_consistency, 1),
                        "symmetry": round(fp.bilateral_symmetry, 1) if fp.bilateral_symmetry is not None else None
                    }
                ],
                "ai_insight": f"Baseline movement signature established at {round(fp.overall_movement_quality, 1)} quality score. Complete additional sessions to generate longitudinal evolution insights.",
                "recommendations": [
                    f"Maintain consistent workout frequency for {ex_name} to develop trend analysis.",
                    "Focus on smooth, steady cadence during both concentric and eccentric phases."
                ]
            }

        # 5. Handle Multi-Session Evolution (2+ sessions)
        first_fp = history[0]
        latest_fp = history[-1]

        def _calc_metric_diff(init_val: Optional[float], cur_val: Optional[float]) -> Dict[str, Any]:
            if init_val is None or cur_val is None:
                return {
                    "initial": None,
                    "latest": None,
                    "change": 0.0,
                    "change_pct": 0.0,
                    "trend": "stable",
                    "available": False
                }
            
            diff = round(cur_val - init_val, 1)
            pct = round((diff / max(init_val, 1.0)) * 100.0, 1)
            
            if diff >= 3.0:
                trend = "improving"
            elif diff <= -3.0:
                trend = "declining"
            else:
                trend = "stable"

            return {
                "initial": round(init_val, 1),
                "latest": round(cur_val, 1),
                "change": diff,
                "change_pct": pct,
                "trend": trend,
                "available": True
            }

        overall_diff = _calc_metric_diff(first_fp.overall_movement_quality, latest_fp.overall_movement_quality)
        rom_diff = _calc_metric_diff(first_fp.range_of_motion, latest_fp.range_of_motion)
        stability_diff = _calc_metric_diff(first_fp.movement_stability, latest_fp.movement_stability)
        tempo_diff = _calc_metric_diff(first_fp.tempo_control, latest_fp.tempo_control)
        consistency_diff = _calc_metric_diff(first_fp.repetition_consistency, latest_fp.repetition_consistency)
        symmetry_diff = _calc_metric_diff(first_fp.bilateral_symmetry, latest_fp.bilateral_symmetry)

        # Baseline and Current Signatures
        baseline_sig = {
            "rom_score": round(first_fp.range_of_motion),
            "stability_score": round(first_fp.movement_stability),
            "tempo_score": round(first_fp.tempo_control),
            "consistency_score": round(first_fp.repetition_consistency),
            "symmetry_score": round(first_fp.bilateral_symmetry) if first_fp.bilateral_symmetry is not None else None,
            "movement_quality_score": round(first_fp.overall_movement_quality)
        }
        current_sig = {
            "rom_score": round(latest_fp.range_of_motion),
            "stability_score": round(latest_fp.movement_stability),
            "tempo_score": round(latest_fp.tempo_control),
            "consistency_score": round(latest_fp.repetition_consistency),
            "symmetry_score": round(latest_fp.bilateral_symmetry) if latest_fp.bilateral_symmetry is not None else None,
            "movement_quality_score": round(latest_fp.overall_movement_quality)
        }

        # Timeline points
        timeline = [
            {
                "session_index": i + 1,
                "session_id": fp.workout_session_id,
                "date": fp.created_at.strftime("%b %d") if fp.created_at else f"S{i+1}",
                "quality": round(fp.overall_movement_quality, 1),
                "rom": round(fp.range_of_motion, 1),
                "stability": round(fp.movement_stability, 1),
                "tempo": round(fp.tempo_control, 1),
                "consistency": round(fp.repetition_consistency, 1),
                "symmetry": round(fp.bilateral_symmetry, 1) if fp.bilateral_symmetry is not None else None
            }
            for i, fp in enumerate(history)
        ]

        # 6. Generate Deterministic AI Movement Insight & Recommendations
        ai_insight = MovementFingerprintService._generate_movement_insight(
            ex_name, num_sessions, overall_diff, rom_diff, stability_diff, tempo_diff, consistency_diff, symmetry_diff
        )
        recommendations = MovementFingerprintService._generate_recommendations(
            latest_fp, rom_diff, stability_diff, tempo_diff, consistency_diff, symmetry_diff
        )

        return {
            "exercise_id": ex_id,
            "exercise_name": ex_name,
            "sessions_analyzed": num_sessions,
            "overall": overall_diff,
            "metrics": {
                "rom": rom_diff,
                "stability": stability_diff,
                "tempo": tempo_diff,
                "consistency": consistency_diff,
                "symmetry": symmetry_diff
            },
            "baseline_signature": baseline_sig,
            "current_signature": current_sig,
            "timeline": timeline,
            "ai_insight": ai_insight,
            "recommendations": recommendations
        }

    @staticmethod
    def get_session_comparison(
        db: Session,
        user_id: int,
        exercise_id: int,
        current_quality_score: float,
        current_session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Compares a completed workout session with previous historical sessions for that exercise.
        """
        query = db.query(MovementFingerprintModel).filter(
            MovementFingerprintModel.user_id == user_id,
            MovementFingerprintModel.exercise_id == exercise_id
        )
        if current_session_id:
            query = query.filter(MovementFingerprintModel.workout_session_id != current_session_id)

        prev_fingerprints = query.all()
        if not prev_fingerprints:
            return {
                "has_history": False,
                "this_session": round(current_quality_score, 1),
                "previous_avg": round(current_quality_score, 1),
                "change": 0.0,
                "change_pct": 0.0,
                "trend": "baseline",
                "message": "Baseline session recorded."
            }

        avg_quality = sum(fp.overall_movement_quality for fp in prev_fingerprints) / len(prev_fingerprints)
        diff = round(current_quality_score - avg_quality, 1)
        pct = round((diff / max(avg_quality, 1.0)) * 100.0, 1)

        if diff >= 2.5:
            trend = "improving"
            msg = f"↑ {abs(pct)}% higher movement quality than your previous average."
        elif diff <= -2.5:
            trend = "declining"
            msg = f"↓ {abs(pct)}% lower movement quality than your previous average."
        else:
            trend = "stable"
            msg = "Consistent with your established movement performance level."

        return {
            "has_history": True,
            "this_session": round(current_quality_score, 1),
            "previous_avg": round(avg_quality, 1),
            "change": diff,
            "change_pct": pct,
            "trend": trend,
            "message": msg
        }

    @staticmethod
    def _generate_movement_insight(
        exercise_name: str,
        num_sessions: int,
        overall: Dict[str, Any],
        rom: Dict[str, Any],
        stability: Dict[str, Any],
        tempo: Dict[str, Any],
        consistency: Dict[str, Any],
        symmetry: Dict[str, Any]
    ) -> str:
        """
        Builds explainable, deterministic, non-medical performance observations.
        """
        # Find strongest improving metric
        metrics_pool = [
            ("range of motion", rom["change"], rom["available"]),
            ("movement stability", stability["change"], stability["available"]),
            ("tempo control", tempo["change"], tempo["available"]),
            ("movement consistency", consistency["change"], consistency["available"]),
            ("bilateral symmetry", symmetry["change"], symmetry["available"]),
        ]
        available_pool = [m for m in metrics_pool if m[2]]
        available_pool.sort(key=lambda x: x[1], reverse=True)

        best_metric, best_gain, _ = available_pool[0] if available_pool else ("movement quality", 0, True)
        worst_metric, worst_gain, _ = available_pool[-1] if available_pool else ("tempo", 0, True)

        if overall["trend"] == "improving":
            if best_gain >= 5.0:
                return f"Your {exercise_name.lower()} movement quality improved by {overall['change_pct']}% across {num_sessions} sessions, driven primarily by gains in {best_metric} (+{best_gain}°/pts)."
            return f"Your {exercise_name.lower()} form demonstrates steady positive adaptation, with overall movement quality up {overall['change_pct']}% over {num_sessions} sessions."
        elif overall["trend"] == "declining":
            return f"Your {exercise_name.lower()} movement quality decreased by {abs(overall['change_pct'])}% across recent sessions. Performance dip is most evident in {worst_metric} ({worst_gain} pts). Consider moderating rep speed."
        else:
            return f"Your {exercise_name.lower()} biomechanics are stabilized across {num_sessions} sessions. Movement quality is consistent at {overall['latest']} pts."

    @staticmethod
    def _generate_recommendations(
        latest_fp: MovementFingerprintModel,
        rom: Dict[str, Any],
        stability: Dict[str, Any],
        tempo: Dict[str, Any],
        consistency: Dict[str, Any],
        symmetry: Dict[str, Any]
    ) -> List[str]:
        """
        Generates deterministic training recommendations based on lowest metrics.
        """
        recs = []
        scores = [
            ("ROM", latest_fp.range_of_motion, "Focus on controlled full range of motion while maintaining proper joint alignment."),
            ("Stability", latest_fp.movement_stability, "Slow down transitions between concentric and eccentric phases to minimize joint jitter."),
            ("Tempo", latest_fp.tempo_control, "Maintain an even, rhythmic cadence across all repetitions without rushing."),
            ("Consistency", latest_fp.repetition_consistency, "Aim for identical movement depth and pacing from rep 1 through your final rep.")
        ]
        if latest_fp.bilateral_symmetry is not None:
            scores.append(("Symmetry", latest_fp.bilateral_symmetry, "Focus on balanced weight distribution and even joint displacement between left and right sides."))

        # Sort by score ascending (lowest first)
        scores.sort(key=lambda x: x[1])

        # Pick top 2 focus areas
        for item in scores[:2]:
            recs.append(item[2])

        if latest_fp.overall_movement_quality >= 85.0:
            recs.insert(0, "High overall movement efficiency detected. Ready for progressive overload or increased volume.")

        return recs


movement_fingerprint_service = MovementFingerprintService()
