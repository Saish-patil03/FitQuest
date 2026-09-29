from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from backend.models import WorkoutSessionModel, ExerciseModel
from backend.schemas.analytics import (
    OverviewStats,
    ProgressTrendPoint,
    ExercisePerformance,
    PersonalRecord,
    RecentWorkoutItem,
    ProgressAnalyticsResponse
)
from backend.services.gamification_service import gamification_service

class AnalyticsService:
    """
    Business logic for calculating read-only Progress Analytics Dashboard metrics.
    Strictly filters out zero-repetition sessions (repetitions >= 1).
    """

    @staticmethod
    def get_user_analytics(db: Session, user_id: int, time_range: str = "all") -> ProgressAnalyticsResponse:
        now = datetime.now(timezone.utc)
        
        query = (
            db.query(WorkoutSessionModel)
            .options(joinedload(WorkoutSessionModel.exercise))
            .filter(
                WorkoutSessionModel.user_id == user_id,
                WorkoutSessionModel.repetitions >= 1
            )
        )

        # Apply time range filter if requested
        if time_range == "7d":
            cutoff = now - timedelta(days=7)
            query = query.filter(WorkoutSessionModel.started_at >= cutoff)
        elif time_range == "30d":
            cutoff = now - timedelta(days=30)
            query = query.filter(WorkoutSessionModel.started_at >= cutoff)
        elif time_range == "90d":
            cutoff = now - timedelta(days=90)
            query = query.filter(WorkoutSessionModel.started_at >= cutoff)

        valid_sessions = query.order_by(WorkoutSessionModel.started_at.asc()).all()

        # 1. Overview Statistics
        total_valid = len(valid_sessions)
        total_reps = sum(s.repetitions for s in valid_sessions) if valid_sessions else 0
        avg_form = round(sum(s.form_score for s in valid_sessions) / total_valid, 1) if total_valid > 0 else 0.0
        best_form = round(max((s.form_score for s in valid_sessions), default=0.0), 1)
        highest_reps = max((s.repetitions for s in valid_sessions), default=0)

        # Fetch streak metrics from GamificationService
        streak_data = gamification_service.get_user_streak(db, user_id)
        current_streak = streak_data.current_streak
        longest_streak = streak_data.longest_streak

        overview = OverviewStats(
            total_valid_workouts=total_valid,
            total_repetitions=total_reps,
            average_form_score=avg_form,
            current_streak=current_streak,
            longest_streak=longest_streak,
            best_form_score=best_form,
            highest_repetition_count=highest_reps
        )

        # 2. Progress Trends (Grouped by Date)
        date_map: Dict[str, Dict[str, Any]] = {}
        for s in valid_sessions:
            d_str = s.started_at.strftime("%Y-%m-%d") if s.started_at else "Unknown"
            if d_str not in date_map:
                date_map[d_str] = {"total_reps": 0, "form_sum": 0.0, "count": 0}
            date_map[d_str]["total_reps"] += s.repetitions
            date_map[d_str]["form_sum"] += s.form_score
            date_map[d_str]["count"] += 1

        progress_trends: List[ProgressTrendPoint] = []
        for d_str, val in sorted(date_map.items()):
            avg_f = round(val["form_sum"] / val["count"], 1) if val["count"] > 0 else 0.0
            progress_trends.append(
                ProgressTrendPoint(
                    date=d_str,
                    total_reps=val["total_reps"],
                    avg_form_score=avg_f,
                    workout_count=val["count"]
                )
            )

        # 3. Exercise Performance Breakdown
        ex_map: Dict[int, Dict[str, Any]] = {}
        for s in valid_sessions:
            ex_id = s.exercise_id
            ex_name = s.exercise.name if s.exercise else f"Exercise {ex_id}"
            muscle = s.exercise.muscle_group if s.exercise else None

            if ex_id not in ex_map:
                ex_map[ex_id] = {
                    "name": ex_name,
                    "muscle": muscle,
                    "count": 0,
                    "total_reps": 0,
                    "form_sum": 0.0,
                    "best_reps": 0
                }
            ex_map[ex_id]["count"] += 1
            ex_map[ex_id]["total_reps"] += s.repetitions
            ex_map[ex_id]["form_sum"] += s.form_score
            if s.repetitions > ex_map[ex_id]["best_reps"]:
                ex_map[ex_id]["best_reps"] = s.repetitions

        exercise_performance: List[ExercisePerformance] = []
        for ex_id, val in sorted(ex_map.items(), key=lambda item: item[1]["count"], reverse=True):
            avg_f = round(val["form_sum"] / val["count"], 1) if val["count"] > 0 else 0.0
            exercise_performance.append(
                ExercisePerformance(
                    exercise_id=ex_id,
                    exercise_name=val["name"],
                    muscle_group=val["muscle"],
                    workout_count=val["count"],
                    total_reps=val["total_reps"],
                    average_form_score=avg_f,
                    best_rep_count=val["best_reps"]
                )
            )

        # 4. Personal Records (PRs) per Exercise
        pr_map: Dict[int, WorkoutSessionModel] = {}
        for s in valid_sessions:
            ex_id = s.exercise_id
            if ex_id not in pr_map:
                pr_map[ex_id] = s
            else:
                existing = pr_map[ex_id]
                if s.repetitions > existing.repetitions or (s.repetitions == existing.repetitions and s.form_score > existing.form_score):
                    pr_map[ex_id] = s

        personal_records: List[PersonalRecord] = []
        for ex_id, pr_session in pr_map.items():
            ex_name = pr_session.exercise.name if pr_session.exercise else f"Exercise {ex_id}"
            personal_records.append(
                PersonalRecord(
                    exercise_id=ex_id,
                    exercise_name=ex_name,
                    max_reps=pr_session.repetitions,
                    best_form_score=round(pr_session.form_score, 1),
                    achieved_at=pr_session.started_at
                )
            )

        # 5. Recent Activity (Last 5 valid workouts)
        recent_sessions = sorted(valid_sessions, key=lambda s: s.started_at, reverse=True)[:5]
        recent_activity: List[RecentWorkoutItem] = []
        for s in recent_sessions:
            ex_name = s.exercise.name if s.exercise else f"Exercise {s.exercise_id}"
            recent_activity.append(
                RecentWorkoutItem(
                    id=s.id,
                    exercise_name=ex_name,
                    repetitions=s.repetitions,
                    duration_sec=s.duration_sec,
                    form_score=round(s.form_score, 1),
                    started_at=s.started_at
                )
            )

        return ProgressAnalyticsResponse(
            overview=overview,
            progress_trends=progress_trends,
            exercise_performance=exercise_performance,
            personal_records=personal_records,
            recent_activity=recent_activity
        )

analytics_service = AnalyticsService()
