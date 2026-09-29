from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import exc

from backend.models import WorkoutSessionModel, UserAchievementModel
from backend.schemas.achievement import StreakResponse, AchievementResponse

# Master Catalogue of the 8 FitQuest Gamification Achievements
ACHIEVEMENT_CATALOGUE: List[Dict[str, Any]] = [
    {
        "id": "FIRST_WORKOUT",
        "title": "First Workout",
        "description": "Complete your first valid workout.",
        "icon": "fa-medal",
        "target": 1,
        "evaluator": lambda total_valid, curr_streak, max_streak: min(total_valid, 1)
    },
    {
        "id": "THREE_DAY_STREAK",
        "title": "3 Day Streak",
        "description": "Maintain a 3-day workout streak.",
        "icon": "fa-fire",
        "target": 3,
        "evaluator": lambda total_valid, curr_streak, max_streak: min(max_streak, 3)
    },
    {
        "id": "SEVEN_DAY_STREAK",
        "title": "7 Day Streak",
        "description": "Maintain a 7-day workout streak.",
        "icon": "fa-fire-flame-curved",
        "target": 7,
        "evaluator": lambda total_valid, curr_streak, max_streak: min(max_streak, 7)
    },
    {
        "id": "FOURTEEN_DAY_STREAK",
        "title": "14 Day Streak",
        "description": "Maintain a 14-day workout streak.",
        "icon": "fa-fire-burner",
        "target": 14,
        "evaluator": lambda total_valid, curr_streak, max_streak: min(max_streak, 14)
    },
    {
        "id": "THIRTY_DAY_STREAK",
        "title": "30 Day Streak",
        "description": "Maintain a 30-day workout streak.",
        "icon": "fa-crown",
        "target": 30,
        "evaluator": lambda total_valid, curr_streak, max_streak: min(max_streak, 30)
    },
    {
        "id": "TEN_WORKOUTS",
        "title": "10 Workouts",
        "description": "Complete 10 valid workout sessions.",
        "icon": "fa-dumbbell",
        "target": 10,
        "evaluator": lambda total_valid, curr_streak, max_streak: min(total_valid, 10)
    },
    {
        "id": "FIFTY_WORKOUTS",
        "title": "50 Workouts",
        "description": "Complete 50 valid workout sessions.",
        "icon": "fa-trophy",
        "target": 50,
        "evaluator": lambda total_valid, curr_streak, max_streak: min(total_valid, 50)
    },
    {
        "id": "HUNDRED_WORKOUTS",
        "title": "100 Workouts",
        "description": "Complete 100 valid workout sessions.",
        "icon": "fa-award",
        "target": 100,
        "evaluator": lambda total_valid, curr_streak, max_streak: min(total_valid, 100)
    }
]

class GamificationService:
    """
    Business logic for Streaks, Activity Calendar, and Gamification Achievements.
    """

    @staticmethod
    def get_user_valid_sessions(db: Session, user_id: int) -> List[WorkoutSessionModel]:
        """
        Retrieves all valid workout sessions (repetitions >= 1) for a user, ordered by started_at.
        """
        return (
            db.query(WorkoutSessionModel)
            .filter(
                WorkoutSessionModel.user_id == user_id,
                WorkoutSessionModel.repetitions >= 1
            )
            .order_by(WorkoutSessionModel.started_at.asc())
            .all()
        )

    @staticmethod
    def calculate_streak_metrics(sessions: List[WorkoutSessionModel], target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Calculates current_streak, longest_streak, total_workout_days, total_valid_workouts,
        today_completed, and active_dates from valid workout sessions.
        """
        # Extract unique calendar dates for valid workouts
        active_dates_list: List[date] = sorted(list({
            s.started_at.date() if hasattr(s.started_at, 'date') else s.started_at
            for s in sessions if s.started_at is not None
        }))

        total_valid_workouts = len(sessions)
        total_workout_days = len(active_dates_list)
        active_date_set = set(active_dates_list)

        utc_today = datetime.now(timezone.utc).date()
        local_today = date.today()
        if target_date:
            ref_date = target_date
        elif local_today in active_date_set:
            ref_date = local_today
        elif utc_today in active_date_set:
            ref_date = utc_today
        else:
            ref_date = local_today

        today_completed = ref_date in active_date_set

        if not active_dates_list:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "total_workout_days": 0,
                "total_valid_workouts": 0,
                "today_completed": False,
                "active_dates": []
            }

        # 1. Calculate current_streak
        yesterday = ref_date - timedelta(days=1)
        current_streak = 0

        if ref_date in active_date_set:
            curr = ref_date
            while curr in active_date_set:
                current_streak += 1
                curr -= timedelta(days=1)
        elif yesterday in active_date_set:
            curr = yesterday
            while curr in active_date_set:
                current_streak += 1
                curr -= timedelta(days=1)
        else:
            current_streak = 0

        # 2. Calculate historical longest_streak
        longest_streak = 0
        temp_streak = 0
        prev_date: Optional[date] = None

        for d in active_dates_list:
            if prev_date is None:
                temp_streak = 1
            elif d == prev_date + timedelta(days=1):
                temp_streak += 1
            else:
                temp_streak = 1
            prev_date = d
            if temp_streak > longest_streak:
                longest_streak = temp_streak

        longest_streak = max(longest_streak, current_streak)

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_workout_days": total_workout_days,
            "total_valid_workouts": total_valid_workouts,
            "today_completed": today_completed,
            "active_dates": [d.strftime("%Y-%m-%d") for d in active_dates_list]
        }

    @classmethod
    def get_user_streak(cls, db: Session, user_id: int) -> StreakResponse:
        """
        Retrieves current streak metrics for an authenticated user.
        """
        sessions = cls.get_user_valid_sessions(db, user_id)
        metrics = cls.calculate_streak_metrics(sessions)
        return StreakResponse(**metrics)

    @classmethod
    def evaluate_and_award_achievements(cls, db: Session, user_id: int) -> List[UserAchievementModel]:
        """
        Evaluates user metrics and unlocks any newly earned achievements automatically.
        Enforces idempotency and unique constraint to prevent duplicate awards.
        """
        sessions = cls.get_user_valid_sessions(db, user_id)
        metrics = cls.calculate_streak_metrics(sessions)

        valid_workouts = metrics["total_valid_workouts"]
        curr_streak = metrics["current_streak"]
        max_streak = metrics["longest_streak"]

        # Fetch already earned achievements for this user
        earned_records = (
            db.query(UserAchievementModel)
            .filter(UserAchievementModel.user_id == user_id)
            .all()
        )
        earned_set = {rec.achievement_type for rec in earned_records}

        newly_unlocked: List[UserAchievementModel] = []

        for ach in ACHIEVEMENT_CATALOGUE:
            ach_id = ach["id"]
            if ach_id in earned_set:
                continue

            progress = ach["evaluator"](valid_workouts, curr_streak, max_streak)
            if progress >= ach["target"]:
                try:
                    new_award = UserAchievementModel(
                        user_id=user_id,
                        achievement_type=ach_id,
                        earned_at=datetime.now(timezone.utc)
                    )
                    db.add(new_award)
                    db.commit()
                    db.refresh(new_award)
                    newly_unlocked.append(new_award)
                    earned_set.add(ach_id)
                except exc.IntegrityError:
                    db.rollback()

        return newly_unlocked

    @classmethod
    def get_user_achievements(cls, db: Session, user_id: int) -> List[AchievementResponse]:
        """
        Retrieves complete list of achievements with earned status and progress.
        """
        sessions = cls.get_user_valid_sessions(db, user_id)
        metrics = cls.calculate_streak_metrics(sessions)

        valid_workouts = metrics["total_valid_workouts"]
        curr_streak = metrics["current_streak"]
        max_streak = metrics["longest_streak"]

        # Evaluate and unlock any eligible achievements first
        cls.evaluate_and_award_achievements(db, user_id)

        earned_records = (
            db.query(UserAchievementModel)
            .filter(UserAchievementModel.user_id == user_id)
            .all()
        )
        earned_map = {rec.achievement_type: rec.earned_at for rec in earned_records}

        results: List[AchievementResponse] = []
        for ach in ACHIEVEMENT_CATALOGUE:
            ach_id = ach["id"]
            is_earned = ach_id in earned_map
            progress = ach["evaluator"](valid_workouts, curr_streak, max_streak)

            results.append(
                AchievementResponse(
                    id=ach_id,
                    title=ach["title"],
                    description=ach["description"],
                    icon=ach["icon"],
                    earned=is_earned,
                    earned_at=earned_map.get(ach_id),
                    progress=progress,
                    target=ach["target"]
                )
            )

        return results

gamification_service = GamificationService()
