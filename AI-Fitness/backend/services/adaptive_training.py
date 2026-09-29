"""
FitQuest Human Movement Intelligence Engine — Phase 3: Adaptive AI Training Engine

Closed-Loop Personalized Workout Intelligence:
Converts historical biomechanical movement fingerprints into an intelligent,
deterministic, and explainable adaptive training prescription.

Capabilities:
1. User Adaptive Profile: Derived longitudinal strengths, limiting factors, and trend vectors.
2. Weakness & Limiters Engine: Classifies ROM, Stability, Tempo, Consistency, and Symmetry into
   explainable performance tiers (STRONG, ADEQUATE, NEEDS ATTENTION, HIGH PRIORITY).
3. Explainable Adaptation Rules: Modulates exercise selection, target sets/reps, eccentric tempos,
   and biomechanical focus cues based on historical evidence.
4. Deterministic Recommendation Engine: Scores and ranks exercises from the 20-exercise catalogue
   with clear "Why was this selected?" rationales.
5. Personalized Workout Generator: Generates multi-exercise routines compatible with
   FitQuest's structured workout execution orchestrator.
6. Post-Workout Adaptation Impact: Evaluates session performance against historical benchmarks.

Safety & Non-Clinical Integrity:
- Strictly non-clinical, performance/movement-quality terminology only.
- No video or image storage.
- Strict user data isolation.
- Zero computer vision overhead (runs purely on-demand).
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models.movement_fingerprint import MovementFingerprintModel
from backend.models.exercise import ExerciseModel
from backend.models.workout import WorkoutSessionModel
from backend.services.movement_intelligence import EXERCISE_BENCHMARKS

logger = logging.getLogger(__name__)

# Metric Classification Thresholds
METRIC_THRESHOLDS = {
    "STRONG": 80.0,
    "ADEQUATE": 65.0,
    "NEEDS_ATTENTION": 50.0,
    # Below 50.0 is HIGH_PRIORITY
}

# Exercise Catalog Metadata & Biomechanical Affinity Matrix
EXERCISE_METADATA = {
    1: {
        "name": "Bicep Curl",
        "category": "Upper Body",
        "muscle_group": "Biceps & Forearms",
        "difficulty": "Beginner",
        "affinities": {"tempo_control": 0.95, "bilateral_symmetry": 0.90, "repetition_consistency": 0.85, "range_of_motion": 0.80, "movement_stability": 0.70},
        "default_sets": 3,
        "default_reps": 12,
        "default_rest_sec": 30
    },
    2: {
        "name": "Squat",
        "category": "Lower Body",
        "muscle_group": "Quads, Glutes & Core",
        "difficulty": "Intermediate",
        "affinities": {"range_of_motion": 0.95, "movement_stability": 0.95, "tempo_control": 0.85, "bilateral_symmetry": 0.85, "repetition_consistency": 0.80},
        "default_sets": 3,
        "default_reps": 12,
        "default_rest_sec": 45
    },
    3: {
        "name": "Push-up",
        "category": "Upper Body",
        "muscle_group": "Chest, Triceps & Core",
        "difficulty": "Intermediate",
        "affinities": {"movement_stability": 0.90, "tempo_control": 0.90, "bilateral_symmetry": 0.85, "repetition_consistency": 0.85, "range_of_motion": 0.80},
        "default_sets": 3,
        "default_reps": 10,
        "default_rest_sec": 45
    },
    4: {
        "name": "Lunges",
        "category": "Lower Body",
        "muscle_group": "Quads, Glutes & Hamstrings",
        "difficulty": "Intermediate",
        "affinities": {"movement_stability": 0.95, "range_of_motion": 0.90, "tempo_control": 0.80, "repetition_consistency": 0.75, "bilateral_symmetry": 0.50},
        "default_sets": 3,
        "default_reps": 10,
        "default_rest_sec": 45
    },
    5: {
        "name": "Shoulder Press",
        "category": "Upper Body",
        "muscle_group": "Deltoids & Triceps",
        "difficulty": "Intermediate",
        "affinities": {"bilateral_symmetry": 0.95, "movement_stability": 0.90, "tempo_control": 0.85, "range_of_motion": 0.85, "repetition_consistency": 0.80},
        "default_sets": 3,
        "default_reps": 10,
        "default_rest_sec": 45
    },
    6: {
        "name": "Jumping Jacks",
        "category": "Cardio",
        "muscle_group": "Full Body & Cardio",
        "difficulty": "Beginner",
        "affinities": {"repetition_consistency": 0.95, "tempo_control": 0.85, "range_of_motion": 0.80, "bilateral_symmetry": 0.80, "movement_stability": 0.65},
        "default_sets": 3,
        "default_reps": 25,
        "default_rest_sec": 30
    },
    7: {
        "name": "High Knees",
        "category": "Cardio",
        "muscle_group": "Hip Flexors, Quads & Cardio",
        "difficulty": "Intermediate",
        "affinities": {"range_of_motion": 0.90, "repetition_consistency": 0.90, "tempo_control": 0.85, "movement_stability": 0.75, "bilateral_symmetry": 0.50},
        "default_sets": 3,
        "default_reps": 20,
        "default_rest_sec": 30
    },
    8: {
        "name": "Mountain Climbers",
        "category": "Core & Cardio",
        "muscle_group": "Core, Shoulders & Cardio",
        "difficulty": "Intermediate",
        "affinities": {"movement_stability": 0.95, "tempo_control": 0.85, "repetition_consistency": 0.85, "range_of_motion": 0.75, "bilateral_symmetry": 0.50},
        "default_sets": 3,
        "default_reps": 20,
        "default_rest_sec": 30
    },
    9: {
        "name": "Plank",
        "category": "Core",
        "muscle_group": "Transverse Abdominis & Core",
        "difficulty": "Beginner",
        "affinities": {"movement_stability": 1.00, "repetition_consistency": 0.80, "tempo_control": 0.70, "range_of_motion": 0.70, "bilateral_symmetry": 0.50},
        "default_sets": 3,
        "default_reps": 30,
        "default_rest_sec": 45
    },
    10: {
        "name": "Glute Bridge",
        "category": "Lower Body",
        "muscle_group": "Glutes & Posterior Chain",
        "difficulty": "Beginner",
        "affinities": {"movement_stability": 0.95, "range_of_motion": 0.90, "tempo_control": 0.85, "bilateral_symmetry": 0.85, "repetition_consistency": 0.80},
        "default_sets": 3,
        "default_reps": 15,
        "default_rest_sec": 30
    },
    11: {
        "name": "Sit-ups",
        "category": "Core",
        "muscle_group": "Abdominals & Hip Flexors",
        "difficulty": "Beginner",
        "affinities": {"repetition_consistency": 0.90, "tempo_control": 0.85, "range_of_motion": 0.85, "movement_stability": 0.75, "bilateral_symmetry": 0.70},
        "default_sets": 3,
        "default_reps": 15,
        "default_rest_sec": 30
    },
    12: {
        "name": "Crunches",
        "category": "Core",
        "muscle_group": "Upper Abdominals",
        "difficulty": "Beginner",
        "affinities": {"repetition_consistency": 0.90, "tempo_control": 0.85, "range_of_motion": 0.80, "movement_stability": 0.75, "bilateral_symmetry": 0.70},
        "default_sets": 3,
        "default_reps": 15,
        "default_rest_sec": 30
    },
    13: {
        "name": "Leg Raises",
        "category": "Core",
        "muscle_group": "Lower Abdominals & Hip Flexors",
        "difficulty": "Intermediate",
        "affinities": {"movement_stability": 0.90, "range_of_motion": 0.90, "tempo_control": 0.85, "repetition_consistency": 0.80, "bilateral_symmetry": 0.50},
        "default_sets": 3,
        "default_reps": 12,
        "default_rest_sec": 30
    },
    14: {
        "name": "Russian Twists",
        "category": "Core",
        "muscle_group": "Obliques & Rotational Core",
        "difficulty": "Intermediate",
        "affinities": {"movement_stability": 0.90, "tempo_control": 0.85, "repetition_consistency": 0.85, "range_of_motion": 0.80, "bilateral_symmetry": 0.50},
        "default_sets": 3,
        "default_reps": 16,
        "default_rest_sec": 30
    },
    15: {
        "name": "Bicycle Crunches",
        "category": "Core",
        "muscle_group": "Obliques & Rectus Abdominis",
        "difficulty": "Intermediate",
        "affinities": {"repetition_consistency": 0.90, "tempo_control": 0.85, "movement_stability": 0.80, "range_of_motion": 0.80, "bilateral_symmetry": 0.50},
        "default_sets": 3,
        "default_reps": 16,
        "default_rest_sec": 30
    },
    16: {
        "name": "Side Lunges",
        "category": "Lower Body",
        "muscle_group": "Quads, Glutes & Adductors",
        "difficulty": "Intermediate",
        "affinities": {"movement_stability": 0.95, "range_of_motion": 0.90, "tempo_control": 0.80, "repetition_consistency": 0.75, "bilateral_symmetry": 0.50},
        "default_sets": 3,
        "default_reps": 10,
        "default_rest_sec": 45
    },
    17: {
        "name": "Calf Raises",
        "category": "Lower Body",
        "muscle_group": "Gastrocnemius & Soleus",
        "difficulty": "Beginner",
        "affinities": {"bilateral_symmetry": 0.95, "tempo_control": 0.90, "range_of_motion": 0.85, "repetition_consistency": 0.85, "movement_stability": 0.80},
        "default_sets": 3,
        "default_reps": 18,
        "default_rest_sec": 30
    },
    18: {
        "name": "Front Raises",
        "category": "Upper Body",
        "muscle_group": "Anterior Deltoids",
        "difficulty": "Beginner",
        "affinities": {"bilateral_symmetry": 0.95, "tempo_control": 0.90, "movement_stability": 0.85, "range_of_motion": 0.85, "repetition_consistency": 0.80},
        "default_sets": 3,
        "default_reps": 12,
        "default_rest_sec": 30
    },
    19: {
        "name": "Lateral Raises",
        "category": "Upper Body",
        "muscle_group": "Lateral Deltoids",
        "difficulty": "Intermediate",
        "affinities": {"bilateral_symmetry": 0.95, "tempo_control": 0.90, "movement_stability": 0.85, "range_of_motion": 0.85, "repetition_consistency": 0.80},
        "default_sets": 3,
        "default_reps": 12,
        "default_rest_sec": 30
    },
    20: {
        "name": "Tricep Extensions",
        "category": "Upper Body",
        "muscle_group": "Triceps Brachii",
        "difficulty": "Intermediate",
        "affinities": {"bilateral_symmetry": 0.95, "tempo_control": 0.90, "movement_stability": 0.85, "range_of_motion": 0.85, "repetition_consistency": 0.80},
        "default_sets": 3,
        "default_reps": 12,
        "default_rest_sec": 30
    }
}


class AdaptiveTrainingEngine:
    """
    Core AI engine for translating longitudinal movement intelligence into
    adaptive workouts, weakness-targeted exercises, and closed-loop training feedback.
    """

    @staticmethod
    def _classify_status(score: Optional[float]) -> str:
        if score is None:
            return "N/A"
        if score >= METRIC_THRESHOLDS["STRONG"]:
            return "STRONG"
        if score >= METRIC_THRESHOLDS["ADEQUATE"]:
            return "ADEQUATE"
        if score >= METRIC_THRESHOLDS["NEEDS_ATTENTION"]:
            return "NEEDS ATTENTION"
        return "HIGH PRIORITY"

    @classmethod
    def get_user_adaptive_profile(cls, db: Session, user_id: int) -> Dict[str, Any]:
        """
        Derives user's longitudinal adaptive profile from historical movement fingerprints.
        Strictly authenticated to user_id.
        """
        fingerprints: List[MovementFingerprintModel] = db.query(MovementFingerprintModel).filter(
            MovementFingerprintModel.user_id == user_id
        ).order_by(MovementFingerprintModel.created_at.asc()).all()

        total_sessions = len(fingerprints)

        # Empty History Default
        if total_sessions == 0:
            return {
                "total_sessions_analyzed": 0,
                "confidence": "Low",
                "confidence_score": 0.20,
                "confidence_reason": "No historical movement fingerprints recorded yet.",
                "primary_focus": "movement_stability",
                "secondary_focus": "tempo_control",
                "primary_focus_label": "Movement Stability",
                "secondary_focus_label": "Tempo Control",
                "strongest_area": "range_of_motion",
                "strongest_area_label": "Range of Motion",
                "weakest_area": "movement_stability",
                "weakest_area_label": "Movement Stability",
                "metric_averages": {
                    "range_of_motion": None,
                    "movement_stability": None,
                    "tempo_control": None,
                    "repetition_consistency": None,
                    "bilateral_symmetry": None,
                    "overall_movement_quality": None
                },
                "metric_status": {
                    "range_of_motion": "N/A",
                    "movement_stability": "N/A",
                    "tempo_control": "N/A",
                    "repetition_consistency": "N/A",
                    "bilateral_symmetry": "N/A"
                },
                "declining_exercises": [],
                "improving_exercises": [],
                "summary_insight": "Complete your first workout to generate your personalized biomechanical movement profile.",
                "fitquest_response": "FitQuest will observe your movement kinematics and begin adapting your training."
            }

        # Compute averages across recorded sessions
        rom_vals = [fp.range_of_motion for fp in fingerprints if fp.range_of_motion is not None]
        stab_vals = [fp.movement_stability for fp in fingerprints if fp.movement_stability is not None]
        tempo_vals = [fp.tempo_control for fp in fingerprints if fp.tempo_control is not None]
        cons_vals = [fp.repetition_consistency for fp in fingerprints if fp.repetition_consistency is not None]
        sym_vals = [fp.bilateral_symmetry for fp in fingerprints if fp.bilateral_symmetry is not None]
        qual_vals = [fp.overall_movement_quality for fp in fingerprints if fp.overall_movement_quality is not None]

        avg_rom = round(float(sum(rom_vals) / len(rom_vals)), 1) if rom_vals else 75.0
        avg_stab = round(float(sum(stab_vals) / len(stab_vals)), 1) if stab_vals else 75.0
        avg_tempo = round(float(sum(tempo_vals) / len(tempo_vals)), 1) if tempo_vals else 75.0
        avg_cons = round(float(sum(cons_vals) / len(cons_vals)), 1) if cons_vals else 75.0
        avg_sym = round(float(sum(sym_vals) / len(sym_vals)), 1) if sym_vals else None
        avg_qual = round(float(sum(qual_vals) / len(qual_vals)), 1) if qual_vals else 75.0

        metrics_map = {
            "range_of_motion": avg_rom,
            "movement_stability": avg_stab,
            "tempo_control": avg_tempo,
            "repetition_consistency": avg_cons,
        }
        if avg_sym is not None:
            metrics_map["bilateral_symmetry"] = avg_sym

        metric_labels = {
            "range_of_motion": "Range of Motion",
            "movement_stability": "Movement Stability",
            "tempo_control": "Tempo Control",
            "repetition_consistency": "Repetition Consistency",
            "bilateral_symmetry": "Bilateral Symmetry"
        }

        # Sort metrics by score ascending to identify limiters (lowest scores) and strongest
        sorted_metrics = sorted(metrics_map.items(), key=lambda item: item[1])
        weakest_key, weakest_val = sorted_metrics[0]
        secondary_key, secondary_val = sorted_metrics[1] if len(sorted_metrics) > 1 else (weakest_key, weakest_val)
        strongest_key, strongest_val = sorted_metrics[-1]

        # Calculate Confidence Score based on volume of historical evidence
        if total_sessions == 1:
            confidence = "Low"
            confidence_score = 0.35
            confidence_reason = "Initial baseline established from 1 recorded session."
        elif total_sessions in [2, 3]:
            confidence = "Moderate"
            confidence_score = 0.70
            confidence_reason = f"Identified recurring patterns across {total_sessions} sessions."
        else:
            confidence = "High"
            confidence_score = min(0.95, 0.80 + (total_sessions * 0.02))
            confidence_reason = f"High longitudinal reliability across {total_sessions} completed sessions."

        # Detect exercise-specific trends
        exercise_fps: Dict[int, List[MovementFingerprintModel]] = {}
        for fp in fingerprints:
            exercise_fps.setdefault(fp.exercise_id, []).append(fp)

        declining_exercises = []
        improving_exercises = []

        for ex_id, fps in exercise_fps.items():
            if len(fps) >= 2:
                initial_q = fps[0].overall_movement_quality
                latest_q = fps[-1].overall_movement_quality
                delta = latest_q - initial_q
                ex_name = fps[-1].exercise_name
                if delta <= -3.0:
                    declining_exercises.append(ex_name)
                elif delta >= 3.0:
                    improving_exercises.append(ex_name)

        # Generate Explainable Summary Insight
        if weakest_val < 70.0:
            summary_insight = (
                f"Your {metric_labels[strongest_key]} is performing strongly ({strongest_val}%), "
                f"while {metric_labels[weakest_key]} ({weakest_val}%) and {metric_labels[secondary_key]} ({secondary_val}%) "
                f"represent your primary movement limiting factors across recent training."
            )
            fitquest_response = (
                f"FitQuest has adapted your upcoming training to prioritize {metric_labels[weakest_key].lower()} "
                f"with controlled eccentric tempos and stable movement patterns."
            )
        else:
            summary_insight = (
                f"Your movement quality is well-balanced across all dimensions ({avg_qual}% composite average), "
                f"with {metric_labels[strongest_key]} leading at {strongest_val}%."
            )
            fitquest_response = (
                "FitQuest will progress your training volume while maintaining disciplined form consistency."
            )

        return {
            "total_sessions_analyzed": total_sessions,
            "confidence": confidence,
            "confidence_score": round(confidence_score, 2),
            "confidence_reason": confidence_reason,
            "primary_focus": weakest_key,
            "secondary_focus": secondary_key,
            "primary_focus_label": metric_labels[weakest_key],
            "secondary_focus_label": metric_labels[secondary_key],
            "strongest_area": strongest_key,
            "strongest_area_label": metric_labels[strongest_key],
            "weakest_area": weakest_key,
            "weakest_area_label": metric_labels[weakest_key],
            "metric_averages": {
                "range_of_motion": avg_rom,
                "movement_stability": avg_stab,
                "tempo_control": avg_tempo,
                "repetition_consistency": avg_cons,
                "bilateral_symmetry": avg_sym,
                "overall_movement_quality": avg_qual
            },
            "metric_status": {
                "range_of_motion": cls._classify_status(avg_rom),
                "movement_stability": cls._classify_status(avg_stab),
                "tempo_control": cls._classify_status(avg_tempo),
                "repetition_consistency": cls._classify_status(avg_cons),
                "bilateral_symmetry": cls._classify_status(avg_sym) if avg_sym is not None else "N/A"
            },
            "declining_exercises": declining_exercises,
            "improving_exercises": improving_exercises,
            "summary_insight": summary_insight,
            "fitquest_response": fitquest_response
        }

    @classmethod
    def get_exercise_recommendations(cls, db: Session, user_id: int) -> List[Dict[str, Any]]:
        """
        Evaluates the 20-exercise catalogue and deterministically ranks exercises
        addressing the user's primary and secondary biomechanical limiters.
        """
        profile = cls.get_user_adaptive_profile(db, user_id)
        primary_focus = profile["primary_focus"]
        secondary_focus = profile["secondary_focus"]

        # Fetch historical performance per exercise to modulate priority
        fps = db.query(MovementFingerprintModel).filter(
            MovementFingerprintModel.user_id == user_id
        ).all()

        ex_history_avg: Dict[int, float] = {}
        for fp in fps:
            ex_history_avg.setdefault(fp.exercise_id, []).append(fp.overall_movement_quality)

        for eid in ex_history_avg:
            vals = ex_history_avg[eid]
            ex_history_avg[eid] = sum(vals) / len(vals)

        recommendations = []

        for ex_id, meta in EXERCISE_METADATA.items():
            affinities = meta["affinities"]
            primary_affinity = affinities.get(primary_focus, 0.5)
            secondary_affinity = affinities.get(secondary_focus, 0.5)

            # Composite Score Calculation (0.0 to 100.0)
            score = (primary_affinity * 55.0) + (secondary_affinity * 30.0)

            # Bonus for addressing an exercise where user historically struggled
            hist_qual = ex_history_avg.get(ex_id)
            if hist_qual is not None:
                if hist_qual < 70.0:
                    score += 15.0  # High priority to rehabilitate form
                elif hist_qual >= 85.0:
                    score += 8.0   # Mastery progression
            else:
                score += 10.0      # Variety boost for unpracticed exercises

            score = min(100.0, round(score, 1))

            # Priority categorization
            if score >= 85.0:
                priority = "HIGH"
            elif score >= 70.0:
                priority = "OPTIMAL"
            else:
                priority = "MODERATE"

            # Determine tailored sets, reps, and tempos based on limiters
            target_sets = meta["default_sets"]
            target_reps = meta["default_reps"]
            rest_sec = meta["default_rest_sec"]

            # Tempo Modulation
            if primary_focus == "tempo_control" or secondary_focus == "tempo_control":
                tempo_str = "3-1-2"
                focus_cue = "Controlled 3s Eccentric Descent"
            elif primary_focus == "movement_stability" or secondary_focus == "movement_stability":
                tempo_str = "2-1-2"
                focus_cue = "Core & Joint Stability Lock"
                rest_sec = min(60, rest_sec + 15)  # allow fuller recovery for stability
            elif primary_focus == "range_of_motion":
                tempo_str = "2-2-1"
                focus_cue = "Full Excursion & Deep Stretch"
            elif primary_focus == "bilateral_symmetry":
                tempo_str = "2-0-2"
                focus_cue = "Balanced Left/Right Force Distribution"
            else:
                tempo_str = "2-0-2"
                focus_cue = "Consistent Repetition Rhythm"

            # Formulate explainable reason
            focus_label = profile["primary_focus_label"]
            if hist_qual and hist_qual < 70.0:
                reason = f"Your historical {meta['name']} score ({round(hist_qual, 1)}%) was constrained by {focus_label.lower()}. Practicing this movement reinforces proper mechanics."
            else:
                reason = f"This exercise develops {focus_label.lower()} with targeted joint stabilization and controlled eccentric pacing."

            recommendations.append({
                "exercise_id": ex_id,
                "exercise_name": meta["name"],
                "category": meta["category"],
                "muscle_group": meta["muscle_group"],
                "difficulty": meta["difficulty"],
                "match_score": score,
                "priority": priority,
                "target_sets": target_sets,
                "target_reps": target_reps,
                "target_tempo": tempo_str,
                "focus": focus_cue,
                "rest_duration_sec": rest_sec,
                "reason": reason
            })

        # Sort recommendations by match_score descending
        recommendations.sort(key=lambda r: r["match_score"], reverse=True)
        return recommendations

    @classmethod
    def generate_adaptive_workout(
        cls,
        db: Session,
        user_id: int,
        target_duration_min: int = 20
    ) -> Dict[str, Any]:
        """
        Generates a complete, personalized, structured workout routine matching the user's
        biomechanical limiter profile and ready for execution.
        """
        profile = cls.get_user_adaptive_profile(db, user_id)
        recommendations = cls.get_exercise_recommendations(db, user_id)

        primary_focus_label = profile["primary_focus_label"]
        secondary_focus_label = profile["secondary_focus_label"]

        # Select 3 to 4 complementary exercises with diverse muscle groups
        selected_exercises: List[Dict[str, Any]] = []
        selected_categories = set()

        for rec in recommendations:
            if len(selected_exercises) >= 4:
                break
            
            # Prioritize distinct movement patterns/categories for well-rounded workout
            if rec["category"] not in selected_categories or len(selected_exercises) < 2:
                selected_exercises.append(rec)
                selected_categories.add(rec["category"])

        # Fallback if fewer than 3 were selected
        if len(selected_exercises) < 3:
            for rec in recommendations:
                if rec not in selected_exercises:
                    selected_exercises.append(rec)
                    if len(selected_exercises) == 3:
                        break

        # Build workout plan payload matching StructuredWorkoutPlanResponse format
        plan_exercises = []
        total_sets = 0
        total_target_reps = 0

        for idx, ex in enumerate(selected_exercises, start=1):
            t_sets = ex["target_sets"]
            t_reps = ex["target_reps"]
            total_sets += t_sets
            total_target_reps += (t_sets * t_reps)

            plan_exercises.append({
                "id": idx,
                "exercise_id": ex["exercise_id"],
                "exercise_name": ex["exercise_name"],
                "order_index": idx,
                "target_sets": t_sets,
                "target_reps": t_reps,
                "target_duration_sec": 45,
                "rest_duration_sec": ex["rest_duration_sec"],
                "target_tempo": ex["target_tempo"],
                "focus": ex["focus"],
                "selection_reason": ex["reason"]
            })

        # Calculate estimated duration (active time + rest time)
        est_duration = max(15, min(35, round((total_sets * 40 + total_sets * 35) / 60)))

        plan_id = int(datetime.now(timezone.utc).timestamp()) % 1000000

        why_this_workout = (
            f"Your recent training telemetry highlights {primary_focus_label} as your primary limiter "
            f"and {secondary_focus_label} as a secondary limiter. "
            f"This routine combines compound stabilization with strict cadence pacing to enhance neuromuscular control."
        )

        return {
            "id": plan_id,
            "title": f"Adaptive Session: {primary_focus_label} Focus",
            "category": "Adaptive Intelligence",
            "description": why_this_workout,
            "difficulty": "Adaptive Intermediate",
            "estimated_duration_min": est_duration,
            "primary_focus": profile["primary_focus"],
            "primary_focus_label": primary_focus_label,
            "secondary_focus_label": secondary_focus_label,
            "confidence": profile["confidence"],
            "confidence_score": profile["confidence_score"],
            "why_this_workout": why_this_workout,
            "total_exercises": len(plan_exercises),
            "total_sets": total_sets,
            "total_target_reps": total_target_reps,
            "exercises": plan_exercises
        }

    @classmethod
    def get_adaptation_impact(
        cls,
        db: Session,
        user_id: int,
        exercise_id: int,
        session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Evaluates the impact of an adaptive workout session by comparing the newly completed
        session's primary metrics against the user's historical baseline.
        """
        fps: List[MovementFingerprintModel] = db.query(MovementFingerprintModel).filter(
            MovementFingerprintModel.user_id == user_id,
            MovementFingerprintModel.exercise_id == exercise_id
        ).order_by(MovementFingerprintModel.created_at.asc()).all()

        if not fps:
            return {
                "has_history": False,
                "message": "Baseline session recorded. Future sessions will evaluate adaptation velocity."
            }

        target_fp = fps[-1]
        if session_id:
            found = next((f for f in fps if f.workout_session_id == session_id), None)
            if found:
                target_fp = found

        prev_fps = [f for f in fps if f.id != target_fp.id]
        if not prev_fps:
            return {
                "has_history": True,
                "exercise_name": target_fp.exercise_name,
                "current_quality": target_fp.overall_movement_quality,
                "current_stability": target_fp.movement_stability,
                "current_tempo": target_fp.tempo_control,
                "previous_avg_quality": target_fp.overall_movement_quality,
                "previous_avg_stability": target_fp.movement_stability,
                "previous_avg_tempo": target_fp.tempo_control,
                "change_quality": 0.0,
                "change_stability": 0.0,
                "change_tempo": 0.0,
                "trend": "baseline",
                "message": "First session established as baseline benchmark."
            }

        prev_avg_qual = round(sum(f.overall_movement_quality for f in prev_fps) / len(prev_fps), 1)
        prev_avg_stab = round(sum(f.movement_stability for f in prev_fps) / len(prev_fps), 1)
        prev_avg_tempo = round(sum(f.tempo_control for f in prev_fps) / len(prev_fps), 1)

        delta_qual = round(target_fp.overall_movement_quality - prev_avg_qual, 1)
        delta_stab = round(target_fp.movement_stability - prev_avg_stab, 1)
        delta_tempo = round(target_fp.tempo_control - prev_avg_tempo, 1)

        if delta_qual >= 3.0:
            trend = "improving"
            message = f"Your movement quality improved (+{delta_qual} pts) with enhanced stability during this adaptive set."
        elif delta_qual <= -3.0:
            trend = "declining"
            message = f"Movement quality was lower than previous average ({delta_qual} pts). Next session will prioritize controlled pacing."
        else:
            trend = "stable"
            message = "Consistent movement execution matching your historical benchmark."

        return {
            "has_history": True,
            "exercise_name": target_fp.exercise_name,
            "current_quality": target_fp.overall_movement_quality,
            "current_stability": target_fp.movement_stability,
            "current_tempo": target_fp.tempo_control,
            "previous_avg_quality": prev_avg_qual,
            "previous_avg_stability": prev_avg_stab,
            "previous_avg_tempo": prev_avg_tempo,
            "change_quality": delta_qual,
            "change_stability": delta_stab,
            "change_tempo": delta_tempo,
            "trend": trend,
            "message": message
        }


adaptive_training_engine = AdaptiveTrainingEngine()
