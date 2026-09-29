from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session

from backend.models.workout import WorkoutSessionModel
from backend.models.exercise import ExerciseModel
from backend.schemas.training_load import TrainingLoadResponse, TrainingLoadSupportingMetrics

class TrainingLoadService:
    @staticmethod
    def calculate_session_load(repetitions: int, duration_sec: int, form_score: float) -> float:
        """
        Session Load = repetitions * (duration_sec / 60.0) * (form_score / 100.0)
        """
        if repetitions < 1:
            return 0.0
        dur_min = duration_sec / 60.0
        form_ratio = form_score / 100.0
        return float(repetitions) * dur_min * form_ratio

    def calculate_user_training_load(self, db: Session, user_id: int) -> TrainingLoadResponse:
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        twenty_eight_days_ago = now - timedelta(days=28)

        # Base query for strictly valid completed workouts (repetitions >= 1)
        valid_query = db.query(WorkoutSessionModel).filter(
            WorkoutSessionModel.user_id == user_id,
            WorkoutSessionModel.repetitions >= 1
        )

        total_valid_count = valid_query.count()

        # STATE 1: Insufficient Data (0 valid workouts)
        if total_valid_count == 0:
            return TrainingLoadResponse(
                acute_load_7d=0.0,
                chronic_load_28d=0.0,
                training_load_ratio=0.0,
                training_load_zone="INSUFFICIENT_DATA",
                recovery_score=None,
                recovery_status="INSUFFICIENT_DATA",
                recommended_action="COMPLETE_FIRST_WORKOUT",
                supporting_metrics=TrainingLoadSupportingMetrics(
                    valid_workouts_7d=0,
                    total_reps_7d=0,
                    days_since_last_workout=None,
                    recent_avg_form=None,
                    form_trend="INSUFFICIENT_DATA",
                    acute_load_7d=0.0,
                    chronic_load_28d=0.0,
                    training_load_ratio=0.0
                ),
                explanation="Complete your first valid workout session to unlock Recovery & Training Load Insights."
            )

        # STATE 2: Valid Workout History Available
        # 1. Acute Training Load (ATL - Last 7 Days)
        w_7d = valid_query.filter(WorkoutSessionModel.started_at >= seven_days_ago).all()
        count_7d = len(w_7d)
        reps_7d = sum(w.repetitions for w in w_7d)
        atl_7d = round(sum(self.calculate_session_load(w.repetitions, w.duration_sec, w.form_score) for w in w_7d), 1)

        # 2. Chronic Training Load (CTL - Last 28 Days)
        w_28d = valid_query.filter(WorkoutSessionModel.started_at >= twenty_eight_days_ago).all()
        total_28d_load = sum(self.calculate_session_load(w.repetitions, w.duration_sec, w.form_score) for w in w_28d)
        ctl_28d = round(total_28d_load / 4.0, 1)

        # 3. Training Load Ratio (TLR)
        tlr = round(atl_7d / max(1.0, ctl_28d), 2)

        # 4. Training Load Zone
        if tlr < 0.8:
            tlr_zone = "UNDER_TRAINING"
        elif 0.8 <= tlr <= 1.3:
            tlr_zone = "OPTIMAL"
        elif 1.3 < tlr <= 1.5:
            tlr_zone = "HIGH_LOAD"
        else: # tlr > 1.5
            tlr_zone = "OVER_REACHING"

        # 5. Days Since Last Valid Workout
        most_recent = valid_query.order_by(WorkoutSessionModel.started_at.desc()).first()
        most_recent_dt = most_recent.started_at
        if most_recent_dt.tzinfo is None:
            most_recent_dt = most_recent_dt.replace(tzinfo=timezone.utc)
        days_since_last = max(0, (now - most_recent_dt).days)

        # 6. Recent Average Form & Form Trend
        recent_avg_form = round(sum(w.form_score for w in w_7d) / count_7d, 1) if count_7d > 0 else None
        if recent_avg_form is None:
            latest_5 = valid_query.order_by(WorkoutSessionModel.started_at.desc()).limit(5).all()
            recent_avg_form = round(sum(w.form_score for w in latest_5) / len(latest_5), 1) if latest_5 else 85.0

        recent_sessions = valid_query.order_by(WorkoutSessionModel.started_at.desc()).limit(6).all()
        form_trend = "STABLE"
        form_trend_penalty = 0

        if len(recent_sessions) >= 4:
            latest_2_avg = sum(s.form_score for s in recent_sessions[:2]) / 2.0
            prior_avg = sum(s.form_score for s in recent_sessions[2:]) / len(recent_sessions[2:])
            if latest_2_avg >= prior_avg + 2.0:
                form_trend = "IMPROVING"
            elif latest_2_avg <= prior_avg - 5.0:
                form_trend = "DECLINING"
                form_trend_penalty = -5

        # 7. Recovery Score (0 - 100)
        # Factor A: Rest Gap Score (40 pts max)
        if days_since_last == 0:
            rest_pts = 15
        elif days_since_last == 1:
            rest_pts = 40
        elif 2 <= days_since_last <= 3:
            rest_pts = 35
        else: # >= 4 days
            rest_pts = 25

        # Factor B: Form Stability Score (30 pts max)
        if recent_avg_form >= 90.0:
            form_pts = 30
        elif recent_avg_form >= 80.0:
            form_pts = 24
        elif recent_avg_form >= 70.0:
            form_pts = 18
        else:
            form_pts = 10
        form_pts = max(0, min(30, form_pts + form_trend_penalty))

        # Factor C: Load Balance Score (30 pts max)
        if tlr < 0.8:
            load_pts = 25
        elif 0.8 <= tlr <= 1.3:
            load_pts = 30
        elif 1.3 < tlr <= 1.5:
            load_pts = 15
        else: # > 1.5
            load_pts = 5

        recovery_raw = rest_pts + form_pts + load_pts
        recovery_score = min(100, max(0, int(round(recovery_raw))))

        # 8. Recovery Status Category
        if recovery_score >= 80:
            recovery_status = "FULLY_RECOVERED"
        elif recovery_score >= 60:
            recovery_status = "MODERATELY_RECOVERED"
        elif recovery_score >= 40:
            recovery_status = "PARTIALLY_RECOVERED"
        else:
            recovery_status = "FATIGUE_ACCUMULATED"

        # 9. Recommended Action
        if tlr_zone == "OVER_REACHING" or recovery_score < 40:
            recommended_action = "REST_OR_RECOVER"
        elif tlr_zone == "HIGH_LOAD" or recovery_score < 60:
            recommended_action = "REDUCE_INTENSITY"
        elif tlr_zone == "UNDER_TRAINING":
            recommended_action = "TRAIN_MODERATELY"
        else: # OPTIMAL + good recovery
            recommended_action = "TRAIN_NORMAL"

        # 10. Explanation Generation
        zone_label = tlr_zone.replace("_", " ").title()
        status_label = recovery_status.replace("_", " ").title()
        explanation = (
            f"Your 7-day training load ({atl_7d} pts) vs 28-day chronic load ({ctl_28d} pts) "
            f"yields a Training Load Ratio of {tlr} ({zone_label}). "
            f"With {days_since_last} day{'s' if days_since_last != 1 else ''} of rest and {recent_avg_form}% form accuracy, "
            f"your estimated recovery status is {status_label} ({recovery_score}%)."
        )

        return TrainingLoadResponse(
            acute_load_7d=atl_7d,
            chronic_load_28d=ctl_28d,
            training_load_ratio=tlr,
            training_load_zone=tlr_zone,
            recovery_score=recovery_score,
            recovery_status=recovery_status,
            recommended_action=recommended_action,
            supporting_metrics=TrainingLoadSupportingMetrics(
                valid_workouts_7d=count_7d,
                total_reps_7d=reps_7d,
                days_since_last_workout=days_since_last,
                recent_avg_form=recent_avg_form,
                form_trend=form_trend,
                acute_load_7d=atl_7d,
                chronic_load_28d=ctl_28d,
                training_load_ratio=tlr
            ),
            explanation=explanation
        )

training_load_service = TrainingLoadService()
