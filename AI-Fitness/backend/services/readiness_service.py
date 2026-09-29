from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.models.workout import WorkoutSessionModel
from backend.models.exercise import ExerciseModel
from backend.models.goal import UserGoalModel
from backend.schemas.readiness import ReadinessResponse, ReadinessSupportingMetrics

class ReadinessService:
    def calculate_user_readiness(self, db: Session, user_id: int) -> ReadinessResponse:
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        fourteen_days_ago = now - timedelta(days=14)

        # Base query for strictly valid completed workouts (repetitions >= 1)
        valid_query = db.query(WorkoutSessionModel).filter(
            WorkoutSessionModel.user_id == user_id,
            WorkoutSessionModel.repetitions >= 1
        )

        total_valid_count = valid_query.count()

        # STATE 1: Insufficient Data (0 valid workouts)
        if total_valid_count == 0:
            return ReadinessResponse(
                readiness_score=None,
                status="INSUFFICIENT_DATA",
                recommended_intensity=None,
                recommended_focus=None,
                recommended_exercise_id=None,
                recommended_exercise_name=None,
                explanation="Complete your first valid workout session to unlock your personalized FitQuest Training Readiness.",
                supporting_metrics=ReadinessSupportingMetrics(
                    valid_workouts_last_7_days=0,
                    valid_workouts_last_14_days=0,
                    recent_total_reps_last_7_days=0,
                    recent_average_form=None,
                    days_since_last_workout=None,
                    form_trend="INSUFFICIENT_DATA"
                )
            )

        # STATE 2: Valid Workout History Available - Calculate Metrics
        # 1. Last 7 days metrics
        w_7d = valid_query.filter(WorkoutSessionModel.started_at >= seven_days_ago).all()
        count_7d = len(w_7d)
        reps_7d = sum(w.repetitions for w in w_7d)
        avg_form_7d = round(sum(w.form_score for w in w_7d) / count_7d, 1) if count_7d > 0 else None

        # Fallback to latest 5 workouts average form if no workouts in last 7 days
        if avg_form_7d is None:
            latest_5 = valid_query.order_by(WorkoutSessionModel.started_at.desc()).limit(5).all()
            avg_form_7d = round(sum(w.form_score for w in latest_5) / len(latest_5), 1) if latest_5 else 85.0

        # 2. Last 14 days count
        count_14d = valid_query.filter(WorkoutSessionModel.started_at >= fourteen_days_ago).count()

        # 3. Days since most recent workout
        most_recent_session = valid_query.order_by(WorkoutSessionModel.started_at.desc()).first()
        most_recent_dt = most_recent_session.started_at
        if most_recent_dt.tzinfo is None:
            most_recent_dt = most_recent_dt.replace(tzinfo=timezone.utc)

        days_since_last = max(0, (now - most_recent_dt).days)

        # Most recent exercise name
        most_recent_ex_name = None
        if most_recent_session.exercise_id:
            ex_obj = db.query(ExerciseModel).filter(ExerciseModel.id == most_recent_session.exercise_id).first()
            if ex_obj:
                most_recent_ex_name = ex_obj.name

        # 4. Form Trend Analysis
        recent_sessions = valid_query.order_by(WorkoutSessionModel.started_at.desc()).limit(6).all()
        form_trend = "STABLE"
        form_trend_pts = 2

        if len(recent_sessions) >= 4:
            latest_2_avg = sum(s.form_score for s in recent_sessions[:2]) / 2.0
            prior_avg = sum(s.form_score for s in recent_sessions[2:]) / len(recent_sessions[2:])
            if latest_2_avg >= prior_avg + 2.0:
                form_trend = "IMPROVING"
                form_trend_pts = 5
            elif latest_2_avg <= prior_avg - 5.0:
                form_trend = "DECLINING"
                form_trend_pts = -5

        # --------------------------------------------------
        # DETERMINISTIC SCORING ALGORITHM (0 - 100)
        # --------------------------------------------------
        # Factor A: Workload Score (30%)
        if count_7d == 0:
            workload_pts = 25
        elif 1 <= count_7d <= 3:
            workload_pts = 30
        elif 4 <= count_7d <= 5:
            workload_pts = 20
        else: # >= 6 workouts in 7 days
            workload_pts = 10

        # Factor B: Form Score & Trend (25%)
        if avg_form_7d >= 90.0:
            form_pts = 25
        elif avg_form_7d >= 80.0:
            form_pts = 20
        elif avg_form_7d >= 70.0:
            form_pts = 15
        else:
            form_pts = 10
        form_pts = max(5, form_pts + form_trend_pts)

        # Factor C: Rest Gap Score (25%)
        if days_since_last == 0:
            rest_pts = 18 # Trained earlier today/recently
        elif days_since_last == 1:
            rest_pts = 25 # Ideal 1-day recovery gap
        elif 2 <= days_since_last <= 3:
            rest_pts = 20
        else: # >= 4 days
            rest_pts = 15

        # Factor D: Frequency Balance Score (20%)
        if 2 <= count_14d <= 8:
            freq_pts = 20
        elif count_14d > 8:
            freq_pts = 12
        else:
            freq_pts = 15

        raw_score = workload_pts + form_pts + rest_pts + freq_pts
        readiness_score = min(100, max(0, int(round(raw_score))))

        # --------------------------------------------------
        # STATUS & INTENSITY MAPPING
        # --------------------------------------------------
        if readiness_score >= 80:
            status_str = "READY_TO_TRAIN"
            intensity_str = "MODERATE_TO_HIGH"
        elif readiness_score >= 60:
            status_str = "GOOD_TO_TRAIN"
            intensity_str = "MODERATE"
        elif readiness_score >= 40:
            status_str = "LIGHT_TRAINING"
            intensity_str = "LOW_TO_MODERATE"
        else:
            status_str = "RECOVERY_RECOMMENDED"
            intensity_str = "LOW"

        # --------------------------------------------------
        # MUSCLE GROUP BALANCE & RECOMMENDATION FOCUS
        # --------------------------------------------------
        lower_body_ids = {2, 4} # Squat, Lunge
        upper_body_ids = {1, 3} # Bicep Curl, Push-up
        core_ids = {5, 6}       # Jumping Jack, Plank

        lower_count = sum(1 for w in w_7d if w.exercise_id in lower_body_ids)
        upper_count = sum(1 for w in w_7d if w.exercise_id in upper_body_ids)
        core_count  = sum(1 for w in w_7d if w.exercise_id in core_ids)

        if readiness_score < 40:
            recommended_focus = "RECOVERY_LIGHT_MOVEMENT"
            recommended_ex_id = 5 # Jumping Jack / light movement
            recommended_ex_name = "Jumping Jack"
            least_trained_group = "Recovery"
        else:
            # Pick muscle group with lowest recent workout count
            if lower_count <= upper_count and lower_count <= core_count:
                recommended_focus = "LOWER_BODY"
                recommended_ex_id = 2 # Squat
                recommended_ex_name = "Squat"
                least_trained_group = "Lower Body"
            elif upper_count <= lower_count and upper_count <= core_count:
                recommended_focus = "UPPER_BODY"
                recommended_ex_id = 3 # Push-up
                recommended_ex_name = "Push-up"
                least_trained_group = "Upper Body"
            else:
                recommended_focus = "CORE"
                recommended_ex_id = 6 # Plank
                recommended_ex_name = "Plank"
                least_trained_group = "Core / Full Body"

        # Context Check: User's Active Goal
        active_goal = db.query(UserGoalModel).filter(
            UserGoalModel.user_id == user_id,
            UserGoalModel.is_completed == False,
            UserGoalModel.exercise_id.isnot(None)
        ).first()

        if active_goal and active_goal.exercise_id:
            goal_ex = db.query(ExerciseModel).filter(ExerciseModel.id == active_goal.exercise_id).first()
            if goal_ex:
                recommended_ex_id = goal_ex.id
                recommended_ex_name = goal_ex.name

        # --------------------------------------------------
        # DETERMINISTIC EXPLANATION GENERATION
        # --------------------------------------------------
        if readiness_score >= 80:
            explanation = (
                f"You have great training consistency ({count_7d} valid session{'s' if count_7d != 1 else ''} in the last 7 days) "
                f"and an optimal rest gap. Your average form accuracy is {avg_form_7d}%. "
                f"Focus on {recommended_ex_name} ({recommended_focus.replace('_', ' ').title()}) to maximize your gains today."
            )
        elif readiness_score >= 60:
            explanation = (
                f"You completed {count_7d} workout{'s' if count_7d != 1 else ''} recently with a {avg_form_7d}% form accuracy rating. "
                f"Your form trend is {form_trend.lower()}. A moderate-intensity session focusing on {recommended_ex_name} is recommended."
            )
        elif readiness_score >= 40:
            explanation = (
                f"You have logged {count_7d} workout{'s' if count_7d != 1 else ''} over the past 7 days. "
                f"Consider a lighter training volume session today to maintain form technique and prevent overload."
            )
        else:
            explanation = (
                f"High recent workout activity detected ({count_7d} session{'s' if count_7d != 1 else ''} in 7 days). "
                f"Your recent form trend is {form_trend.lower()}. Prioritize a light movement session or rest today for optimal consistency."
            )

        return ReadinessResponse(
            readiness_score=readiness_score,
            status=status_str,
            recommended_intensity=intensity_str,
            recommended_focus=recommended_focus,
            recommended_exercise_id=recommended_ex_id,
            recommended_exercise_name=recommended_ex_name,
            explanation=explanation,
            supporting_metrics=ReadinessSupportingMetrics(
                valid_workouts_last_7_days=count_7d,
                valid_workouts_last_14_days=count_14d,
                recent_total_reps_last_7_days=reps_7d,
                recent_average_form=avg_form_7d,
                days_since_last_workout=days_since_last,
                form_trend=form_trend,
                most_recent_exercise=most_recent_ex_name,
                least_trained_muscle_group=least_trained_group
            )
        )

readiness_service = ReadinessService()
