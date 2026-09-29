"""
FitQuest Human Movement Intelligence Engine — Phase 6: BODY SIM™ Service
Predictive Human Performance Intelligence & What-If Intervention Simulator.

Core Capabilities:
1. Performance Forecasting: Blended historical & short-term velocity, metric volatility, asymptotic horizon projections (3, 5, 10 sessions).
2. Limiter Risk Index: Quantifies probability of dimension becoming/remaining a bottleneck.
3. What-If Intervention Simulator: Models 6 deterministic training strategies (Balanced, Tempo Focus, Stability Focus, ROM Focus, Symmetry Focus, Consistency Focus).
4. Adaptive Training Bridge: Direct single-click conversion into tailored structured workout routines.
5. Strict Multi-Tenant Isolation & Zero Database Migrations.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.models.movement_fingerprint import MovementFingerprintModel
from backend.services.movement_dna import MovementDNAService, DIMENSION_LABELS
from backend.services.adaptive_training import adaptive_training_engine

logger = logging.getLogger(__name__)

# Standardized Forecast Horizons
VALID_HORIZONS = [3, 5, 10]

# Six Deterministic What-If Intervention Strategies
INTERVENTION_STRATEGIES = {
    "BALANCED": {
        "key": "BALANCED",
        "name": "Balanced Progression",
        "primary_focus": "General Athleticism",
        "description": "Even distribution of training stimulus across all five biomechanical dimensions.",
        "velocity_boosts": {
            "range_of_motion": 0.6,
            "movement_stability": 0.6,
            "tempo_control": 0.6,
            "repetition_consistency": 0.6,
            "bilateral_symmetry": 0.6
        },
        "target_limiter": None
    },
    "TEMPO_FOCUS": {
        "key": "TEMPO_FOCUS",
        "name": "Tempo & Eccentric Control",
        "primary_focus": "Eccentric Control & Cadence",
        "description": "Accentuated eccentric tempos (3-1-2) to eliminate rushing and inflection instability.",
        "velocity_boosts": {
            "tempo_control": 2.8,
            "repetition_consistency": 1.2,
            "movement_stability": 0.5,
            "range_of_motion": 0.4,
            "bilateral_symmetry": 0.4
        },
        "target_limiter": "tempo_control"
    },
    "STABILITY_FOCUS": {
        "key": "STABILITY_FOCUS",
        "name": "Joint Stability & Core Bracing",
        "primary_focus": "Core Rigidity & Kinetic Alignment",
        "description": "Anti-rotational bracing and kinetic chain alignment to minimize joint wobble.",
        "velocity_boosts": {
            "movement_stability": 3.0,
            "bilateral_symmetry": 1.2,
            "range_of_motion": 0.6,
            "tempo_control": 0.5,
            "repetition_consistency": 0.5
        },
        "target_limiter": "movement_stability"
    },
    "ROM_FOCUS": {
        "key": "ROM_FOCUS",
        "name": "Mobility & Full Range of Motion",
        "primary_focus": "End-Range Excursion",
        "description": "Deep mobility patterns and end-range isometric pauses to unlock complete joint excursion.",
        "velocity_boosts": {
            "range_of_motion": 3.2,
            "movement_stability": 0.8,
            "tempo_control": 0.5,
            "repetition_consistency": 0.5,
            "bilateral_symmetry": 0.4
        },
        "target_limiter": "range_of_motion"
    },
    "SYMMETRY_FOCUS": {
        "key": "SYMMETRY_FOCUS",
        "name": "Bilateral Balance & Alignment",
        "primary_focus": "Unilateral Discrepancy Correction",
        "description": "Unilateral loading and weak-side isolation to equalize bilateral force production.",
        "velocity_boosts": {
            "bilateral_symmetry": 3.4,
            "movement_stability": 1.4,
            "repetition_consistency": 0.6,
            "range_of_motion": 0.4,
            "tempo_control": 0.4
        },
        "target_limiter": "bilateral_symmetry"
    },
    "CONSISTENCY_FOCUS": {
        "key": "CONSISTENCY_FOCUS",
        "name": "Repetition Uniformity & Cadence",
        "primary_focus": "Repetition Cadence & Trajectory",
        "description": "Pacing metronomes and fixed motor pathway drills to ensure uniform repetition mechanics.",
        "velocity_boosts": {
            "repetition_consistency": 3.0,
            "tempo_control": 1.4,
            "movement_stability": 0.5,
            "range_of_motion": 0.4,
            "bilateral_symmetry": 0.4
        },
        "target_limiter": "repetition_consistency"
    }
}


class BodySimService:
    """
    Core Predictive Human Performance Intelligence Engine (Phase 6).
    """

    @classmethod
    def get_performance_forecast(
        cls,
        db: Session,
        user_id: int,
        horizon: int = 5,
        exercise_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculates deterministic performance forecasts across a specified horizon (3, 5, 10 sessions).
        Computes blended velocity, metric volatility, asymptotic trajectories, and limiter risk indices.
        """
        if horizon not in VALID_HORIZONS:
            horizon = 5

        # 1. Fetch raw chronological fingerprints for time-series calculations
        query = db.query(MovementFingerprintModel).filter(
            MovementFingerprintModel.user_id == user_id
        )
        if exercise_id is not None:
            query = query.filter(MovementFingerprintModel.exercise_id == exercise_id)
        
        fingerprints = query.order_by(MovementFingerprintModel.created_at.asc()).all()
        n_sessions = len(fingerprints)

        # 2. Fetch current Movement DNA profile
        dna_profile = MovementDNAService.get_user_movement_dna(db, user_id, exercise_id)
        current_dna_score = float(dna_profile.get("overall_score", 80.0))

        dimension_keys = [
            "range_of_motion",
            "movement_stability",
            "tempo_control",
            "repetition_consistency",
            "bilateral_symmetry"
        ]

        dimensions_forecast: Dict[str, Dict[str, Any]] = {}
        all_volatilities: List[float] = []
        projected_dimension_scores: Dict[str, float] = {}

        # 3. Calculate dimension-by-dimension projections
        for key in dimension_keys:
            dim_meta = dna_profile.get("dimensions", {}).get(key, {})
            current_score = dim_meta.get("score")
            
            # Extract historical time series for this dimension
            raw_series = [getattr(fp, key) for fp in fingerprints if getattr(fp, key) is not None]
            
            # If exercise is unilateral and bilateral symmetry is genuinely not applicable
            if current_score is None and exercise_id is not None:
                dimensions_forecast[key] = {
                    "key": key,
                    "label": DIMENSION_LABELS.get(key, key.replace("_", " ").title()),
                    "current": None,
                    "projected": None,
                    "delta": 0.0,
                    "velocity": 0.0,
                    "volatility": 0.0,
                    "risk_index": 0.0,
                    "risk_tier": "N/A",
                    "trajectory": [],
                    "status": "N/A"
                }
                continue

            current_val = float(current_score if current_score is not None else 80.0)
            
            # Volatility (Standard Deviation)
            if len(raw_series) >= 2:
                volatility = round(float(np.std(raw_series)), 1)
            else:
                volatility = 2.0  # nominal default for cold-start
            all_volatilities.append(volatility)

            # Historical Velocity (Vh)
            if len(raw_series) >= 2:
                baseline_val = float(raw_series[0])
                recent_val = float(raw_series[-1])
                v_h = (recent_val - baseline_val) / max(len(raw_series) - 1, 1)
            else:
                v_h = 0.5  # slight positive adaptation default

            # Short-Term Velocity (Vs) over last 3-5 sessions
            if len(raw_series) >= 3:
                short_window = raw_series[-4:]
                diffs = np.diff(short_window)
                weights = np.linspace(0.6, 1.0, len(diffs))
                v_s = float(np.average(diffs, weights=weights))
            else:
                v_s = v_h

            # Blended Velocity
            v_blend = round(float(0.65 * v_s + 0.35 * v_h), 2)

            # Asymptotic Trajectory Projection across H sessions
            trajectory = [round(current_val, 1)]
            curr = current_val
            for h in range(1, horizon + 1):
                # Damping factor: decay over horizon steps and saturation ceiling
                decay = 0.92 ** h
                saturation_penalty = max(0.1, 1.0 - (curr / 115.0))
                step_gain = v_blend * saturation_penalty * decay
                curr = float(np.clip(curr + step_gain, 20.0, 100.0))
                trajectory.append(round(curr, 1))

            projected_final = trajectory[-1]
            projected_delta = round(projected_final - current_val, 1)
            projected_dimension_scores[key] = projected_final

            # Limiter Risk Index calculation [0 - 100]
            # Risk is elevated by: low projected score (deficit), high volatility, and negative velocity
            raw_risk = (
                (100.0 - projected_final) * 1.0
                + (volatility * 1.5)
                + max(0.0, -v_blend * 8.0)
            )
            risk_index = round(float(np.clip(raw_risk, 0.0, 100.0)), 1)
            risk_tier = cls._classify_risk_tier(risk_index)

            dimensions_forecast[key] = {
                "key": key,
                "label": DIMENSION_LABELS.get(key, key.replace("_", " ").title()),
                "current": round(current_val, 1),
                "projected": round(projected_final, 1),
                "delta": projected_delta,
                "velocity": v_blend,
                "volatility": volatility,
                "risk_index": risk_index,
                "risk_tier": risk_tier,
                "trajectory": trajectory,
                "status": MovementDNAService._classify_metric_status(projected_final)
            }

        # 4. Overall Projected Movement DNA Score & Trajectory
        valid_projected = [v for v in projected_dimension_scores.values() if v is not None]
        if valid_projected:
            projected_dna_score = round(float(sum(valid_projected) / len(valid_projected)), 1)
        else:
            projected_dna_score = current_dna_score

        overall_delta = round(projected_dna_score - current_dna_score, 1)

        # Build overall DNA trajectory
        overall_trajectory = []
        for step_idx in range(horizon + 1):
            step_scores = [
                d["trajectory"][step_idx]
                for d in dimensions_forecast.values()
                if d["trajectory"] and len(d["trajectory"]) > step_idx
            ]
            if step_scores:
                overall_trajectory.append(round(float(sum(step_scores) / len(step_scores)), 1))
            else:
                overall_trajectory.append(current_dna_score)

        # 5. Identify Projected Strongest Trait & Projected Limiter
        sorted_by_risk = sorted(
            [d for d in dimensions_forecast.values() if d["current"] is not None],
            key=lambda x: x["risk_index"],
            reverse=True
        )

        projected_limiter = sorted_by_risk[0] if sorted_by_risk else None
        
        sorted_by_score = sorted(
            [d for d in dimensions_forecast.values() if d["projected"] is not None],
            key=lambda x: x["projected"],
            reverse=True
        )
        strongest_trait = sorted_by_score[0] if sorted_by_score else None

        # 6. Forecast Confidence Score & Tier
        mean_volatility = float(np.mean(all_volatilities)) if all_volatilities else 2.0
        confidence_raw = (min(100.0, n_sessions * 16.0) - (mean_volatility * 0.75) - (horizon * 2.0))
        confidence_score = round(float(np.clip(confidence_raw, 20.0, 95.0)), 1)
        
        if confidence_score >= 70.0:
            confidence_tier = "High"
        elif confidence_score >= 45.0:
            confidence_tier = "Moderate"
        else:
            confidence_tier = "Low"

        # 7. Optimal Intervention Strategy Recommendation
        recommended_strategy_key = cls._recommend_strategy(projected_limiter)
        recommended_strategy = INTERVENTION_STRATEGIES.get(recommended_strategy_key, INTERVENTION_STRATEGIES["BALANCED"])

        # 8. Explainable AI Forecast Summary (Non-clinical)
        summary_text = cls._build_forecast_summary(
            current_dna=current_dna_score,
            projected_dna=projected_dna_score,
            delta=overall_delta,
            horizon=horizon,
            limiter=projected_limiter,
            confidence_tier=confidence_tier,
            recommended_strategy=recommended_strategy
        )

        return {
            "status": "success",
            "horizon_sessions": horizon,
            "total_historical_sessions": n_sessions,
            "confidence_score": confidence_score,
            "confidence_tier": confidence_tier,
            "current_dna_score": current_dna_score,
            "projected_dna_score": projected_dna_score,
            "projected_overall_delta": overall_delta,
            "overall_trajectory": overall_trajectory,
            "strongest_trait": {
                "dimension": strongest_trait["key"] if strongest_trait else "range_of_motion",
                "label": strongest_trait["label"] if strongest_trait else "Range of Motion",
                "current_score": strongest_trait["current"] if strongest_trait else 80.0,
                "projected_score": strongest_trait["projected"] if strongest_trait else 80.0
            } if strongest_trait else None,
            "projected_limiter": {
                "dimension": projected_limiter["key"] if projected_limiter else "tempo_control",
                "label": projected_limiter["label"] if projected_limiter else "Tempo Control",
                "current_score": projected_limiter["current"] if projected_limiter else 70.0,
                "projected_score": projected_limiter["projected"] if projected_limiter else 70.0,
                "risk_index": projected_limiter["risk_index"] if projected_limiter else 30.0,
                "risk_tier": projected_limiter["risk_tier"] if projected_limiter else "LOW"
            } if projected_limiter else None,
            "dimensions": dimensions_forecast,
            "recommended_strategy": recommended_strategy_key,
            "recommended_strategy_name": recommended_strategy["name"],
            "explainable_forecast_summary": summary_text,
            "available_strategies": list(INTERVENTION_STRATEGIES.values())
        }

    @classmethod
    def simulate_intervention(
        cls,
        db: Session,
        user_id: int,
        strategy_key: str = "TEMPO_FOCUS",
        horizon: int = 5,
        exercise_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Runs a What-If intervention simulation under a chosen training strategy.
        Estimates projected trajectory gains, limiter resolution timeline, and net improvement differential.
        """
        strat_key = strategy_key.upper().strip() if strategy_key else "TEMPO_FOCUS"
        strategy = INTERVENTION_STRATEGIES.get(strat_key, INTERVENTION_STRATEGIES["BALANCED"])

        # 1. Base forecast for comparison
        base_forecast = cls.get_performance_forecast(db, user_id, horizon, exercise_id)
        base_projected_dna = float(base_forecast["projected_dna_score"])
        current_dna = float(base_forecast["current_dna_score"])

        boosts = strategy["velocity_boosts"]
        simulated_dimensions: Dict[str, Dict[str, Any]] = {}
        simulated_dim_finals: Dict[str, float] = {}

        # 2. Simulate each dimension with intervention boost
        for key, dim_info in base_forecast["dimensions"].items():
            if dim_info["current"] is None:
                simulated_dimensions[key] = {
                    "key": key,
                    "label": dim_info["label"],
                    "current": None,
                    "baseline_projected": None,
                    "simulated_projected": None,
                    "intervention_gain": 0.0,
                    "simulated_trajectory": []
                }
                continue

            cur_val = float(dim_info["current"])
            base_v = float(dim_info["velocity"])
            boost = float(boosts.get(key, 0.5))
            sim_v = base_v + boost

            sim_trajectory = [round(cur_val, 1)]
            curr = cur_val
            for h in range(1, horizon + 1):
                decay = 0.92 ** h
                saturation = max(0.1, 1.0 - (curr / 115.0))
                step_gain = sim_v * saturation * decay
                curr = float(np.clip(curr + step_gain, 20.0, 100.0))
                sim_trajectory.append(round(curr, 1))

            final_sim = sim_trajectory[-1]
            simulated_dim_finals[key] = final_sim

            simulated_dimensions[key] = {
                "key": key,
                "label": dim_info["label"],
                "current": cur_val,
                "baseline_projected": dim_info["projected"],
                "simulated_projected": final_sim,
                "intervention_gain": round(final_sim - (dim_info["projected"] or cur_val), 1),
                "simulated_trajectory": sim_trajectory
            }

        # 3. Overall simulated DNA score and trajectory
        valid_finals = list(simulated_dim_finals.values())
        if valid_finals:
            simulated_dna_score = round(float(sum(valid_finals) / len(valid_finals)), 1)
        else:
            simulated_dna_score = base_projected_dna

        net_improvement = round(simulated_dna_score - base_projected_dna, 1)

        simulated_overall_trajectory = []
        for step_idx in range(horizon + 1):
            step_vals = [
                d["simulated_trajectory"][step_idx]
                for d in simulated_dimensions.values()
                if "simulated_trajectory" in d and len(d["simulated_trajectory"]) > step_idx
            ]
            if step_vals:
                simulated_overall_trajectory.append(round(float(sum(step_vals) / len(step_vals)), 1))
            else:
                simulated_overall_trajectory.append(current_dna)

        # 4. Limiter resolution timeline
        limiter_key = base_forecast.get("projected_limiter", {}).get("dimension")
        resolution_sessions = None
        if limiter_key and limiter_key in simulated_dimensions:
            lim_traj = simulated_dimensions[limiter_key].get("simulated_trajectory", [])
            # Target passing 75.0 points or current + 5.0
            cur_lim_score = simulated_dimensions[limiter_key].get("current") or 70.0
            target_score = max(75.0, cur_lim_score + 5.0)
            for idx, val in enumerate(lim_traj):
                if val >= target_score:
                    resolution_sessions = idx
                    break
            if resolution_sessions is None and lim_traj:
                resolution_sessions = horizon  # progressive improvement

        # 5. Simulation Insight Text
        insight_text = cls._build_simulation_insight(
            strategy=strategy,
            current_dna=current_dna,
            simulated_dna=simulated_dna_score,
            net_improvement=net_improvement,
            horizon=horizon,
            limiter_key=limiter_key,
            resolution_sessions=resolution_sessions
        )

        return {
            "status": "success",
            "strategy": strategy["key"],
            "strategy_name": strategy["name"],
            "primary_focus": strategy["primary_focus"],
            "horizon_sessions": horizon,
            "current_dna_score": current_dna,
            "baseline_projected_dna": base_projected_dna,
            "simulated_dna_score": simulated_dna_score,
            "net_improvement_delta": net_improvement,
            "limiter_resolution_sessions": resolution_sessions,
            "baseline_trajectory": base_forecast["overall_trajectory"],
            "simulated_trajectory": simulated_overall_trajectory,
            "simulated_dimensions": simulated_dimensions,
            "simulation_insights": insight_text
        }

    @classmethod
    def generate_intervention_workout(
        cls,
        db: Session,
        user_id: int,
        strategy_key: str = "TEMPO_FOCUS",
        target_duration_min: int = 20
    ) -> Dict[str, Any]:
        """
        Converts a chosen What-If intervention simulation directly into a personalized
        Adaptive Workout Routine with customized sets, reps, tempos, and focus cues.
        """
        strat_key = strategy_key.upper().strip() if strategy_key else "TEMPO_FOCUS"
        strategy = INTERVENTION_STRATEGIES.get(strat_key, INTERVENTION_STRATEGIES["BALANCED"])

        # Delegate to Adaptive Training Engine with strategy bias
        workout_plan = adaptive_training_engine.generate_adaptive_workout(
            db=db,
            user_id=user_id,
            target_duration_min=target_duration_min
        )

        # Inject Body Sim intervention metadata
        workout_plan["plan_name"] = workout_plan.get("title", f"{strategy['name']} Routine")
        workout_plan["intervention_strategy"] = strategy["key"]
        workout_plan["intervention_strategy_name"] = strategy["name"]
        workout_plan["intervention_rationale"] = (
            f"Generated from BODY SIM™ What-If analysis targeting {strategy['primary_focus']}. "
            f"Designed to accelerate your Movement DNA trajectory."
        )

        return workout_plan

    # --- Internal Helpers ---
    @staticmethod
    def _classify_risk_tier(risk_index: float) -> str:
        if risk_index >= 75.0:
            return "CRITICAL"
        elif risk_index >= 50.0:
            return "ELEVATED"
        elif risk_index >= 25.0:
            return "MODERATE"
        return "LOW"

    @staticmethod
    def _recommend_strategy(limiter: Optional[Dict[str, Any]]) -> str:
        if not limiter:
            return "BALANCED"
        
        limiter_key = limiter.get("key", limiter.get("dimension", ""))
        strategy_map = {
            "tempo_control": "TEMPO_FOCUS",
            "movement_stability": "STABILITY_FOCUS",
            "range_of_motion": "ROM_FOCUS",
            "bilateral_symmetry": "SYMMETRY_FOCUS",
            "repetition_consistency": "CONSISTENCY_FOCUS"
        }
        return strategy_map.get(limiter_key, "BALANCED")

    @staticmethod
    def _build_forecast_summary(
        current_dna: float,
        projected_dna: float,
        delta: float,
        horizon: int,
        limiter: Optional[Dict[str, Any]],
        confidence_tier: str,
        recommended_strategy: Dict[str, Any]
    ) -> str:
        limiter_label = limiter.get("label", "Tempo Control") if limiter else "None"
        risk_tier = limiter.get("risk_tier", "LOW") if limiter else "LOW"

        direction_str = "increase" if delta >= 0 else "decrease"
        return (
            f"Based on historical movement velocity, your overall Movement DNA is projected to {direction_str} "
            f"from {current_dna:.1f} to {projected_dna:.1f} ({delta:+.1f} pts) over your next {horizon} sessions "
            f"({confidence_tier} Confidence). {limiter_label} is projected as your primary constraint ({risk_tier} Risk). "
            f"A {recommended_strategy['name']} intervention is recommended to optimize progression."
        )

    @staticmethod
    def _build_simulation_insight(
        strategy: Dict[str, Any],
        current_dna: float,
        simulated_dna: float,
        net_improvement: float,
        horizon: int,
        limiter_key: Optional[str],
        resolution_sessions: Optional[int]
    ) -> str:
        gain_str = f"+{net_improvement:.1f}" if net_improvement >= 0 else f"{net_improvement:.1f}"
        res_str = f"within ~{resolution_sessions} sessions" if resolution_sessions else "progressively"
        return (
            f"Under the {strategy['name']} intervention, your Movement DNA is projected to reach {simulated_dna:.1f} "
            f"({gain_str} pts above standard baseline trajectory) over {horizon} workouts, resolving primary bottlenecks {res_str}."
        )


body_sim_service = BodySimService()
