from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.models.goal import UserGoalModel
from backend.models.workout import WorkoutSessionModel
from backend.models.exercise import ExerciseModel
from backend.schemas.goal import GoalCreate, GoalUpdate, GoalProgressResponse

class GoalService:
    @staticmethod
    def get_start_of_week(dt: Optional[datetime] = None) -> datetime:
        if dt is None:
            dt = datetime.now(timezone.utc)
        start = dt - timedelta(days=dt.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def get_end_of_week(dt: Optional[datetime] = None) -> datetime:
        start = GoalService.get_start_of_week(dt)
        return start + timedelta(days=6, hours=23, minutes=59, seconds=59)

    @staticmethod
    def get_start_of_month(dt: Optional[datetime] = None) -> datetime:
        if dt is None:
            dt = datetime.now(timezone.utc)
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def create_goal(self, db: Session, user_id: int, goal_in: GoalCreate) -> UserGoalModel:
        now = datetime.now(timezone.utc)

        # Check for active duplicate goal
        existing_duplicate = db.query(UserGoalModel).filter(
            UserGoalModel.user_id == user_id,
            UserGoalModel.goal_type == goal_in.goal_type,
            UserGoalModel.exercise_id == goal_in.exercise_id,
            UserGoalModel.time_frame == goal_in.time_frame,
            UserGoalModel.is_completed == False
        ).first()

        if existing_duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An active {goal_in.time_frame} goal for type '{goal_in.goal_type}' already exists."
            )

        # Determine start_date and default end_date based on time_frame
        time_frame = goal_in.time_frame or "WEEKLY"
        if time_frame == "WEEKLY":
            start_date = self.get_start_of_week(now)
            default_end = self.get_end_of_week(now)
        elif time_frame == "MONTHLY":
            start_date = self.get_start_of_month(now)
            default_end = None
        else: # ALL_TIME
            start_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
            default_end = None

        end_date = goal_in.end_date if goal_in.end_date is not None else default_end

        # Exercise validation if provided
        if goal_in.exercise_id is not None:
            exercise = db.query(ExerciseModel).filter(ExerciseModel.id == goal_in.exercise_id).first()
            if not exercise:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Exercise with id {goal_in.exercise_id} not found."
                )

        new_goal = UserGoalModel(
            user_id=user_id,
            exercise_id=goal_in.exercise_id,
            goal_type=goal_in.goal_type,
            target_value=goal_in.target_value,
            time_frame=time_frame,
            start_date=start_date,
            end_date=end_date,
            is_completed=False,
            created_at=now
        )
        db.add(new_goal)
        db.commit()
        db.refresh(new_goal)
        return new_goal

    def get_user_goals(self, db: Session, user_id: int) -> List[GoalProgressResponse]:
        goals = db.query(UserGoalModel).filter(
            UserGoalModel.user_id == user_id
        ).order_by(UserGoalModel.is_completed.asc(), UserGoalModel.created_at.desc()).all()

        return [self.calculate_goal_progress(db, goal) for goal in goals]

    def get_goal(self, db: Session, goal_id: int, user_id: int) -> UserGoalModel:
        goal = db.query(UserGoalModel).filter(
            UserGoalModel.id == goal_id,
            UserGoalModel.user_id == user_id
        ).first()

        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found or permission denied."
            )
        return goal

    def update_goal(self, db: Session, goal_id: int, user_id: int, update_in: GoalUpdate) -> GoalProgressResponse:
        goal = self.get_goal(db, goal_id, user_id)

        if update_in.target_value is not None:
            goal.target_value = update_in.target_value
        if update_in.time_frame is not None:
            goal.time_frame = update_in.time_frame
        if update_in.end_date is not None:
            goal.end_date = update_in.end_date

        db.commit()
        db.refresh(goal)
        return self.calculate_goal_progress(db, goal)

    def delete_goal(self, db: Session, goal_id: int, user_id: int) -> bool:
        goal = self.get_goal(db, goal_id, user_id)
        db.delete(goal)
        db.commit()
        return True

    def calculate_goal_progress(self, db: Session, goal: UserGoalModel) -> GoalProgressResponse:
        now = datetime.now(timezone.utc)

        # Normalize naive datetimes from DB to UTC aware
        start_date = goal.start_date
        if start_date and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)

        end_date = goal.end_date
        if end_date and end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        # Base query filtering strictly valid completed workouts (repetitions >= 1)
        query = db.query(WorkoutSessionModel).filter(
            WorkoutSessionModel.user_id == goal.user_id,
            WorkoutSessionModel.repetitions >= 1,
            WorkoutSessionModel.started_at >= start_date
        )

        if end_date:
            query = query.filter(WorkoutSessionModel.started_at <= end_date)

        if goal.exercise_id:
            query = query.filter(WorkoutSessionModel.exercise_id == goal.exercise_id)

        goal_type = goal.goal_type.upper()
        current_val = 0.0

        if goal_type == "REPETITION":
            res = query.with_entities(func.coalesce(func.sum(WorkoutSessionModel.repetitions), 0)).scalar()
            current_val = float(res or 0)

        elif goal_type == "FREQUENCY":
            # Count distinct workout dates
            res = query.with_entities(func.count(func.distinct(func.date(WorkoutSessionModel.started_at)))).scalar()
            current_val = float(res or 0)

        elif goal_type == "FORM_SCORE":
            res = query.with_entities(func.coalesce(func.avg(WorkoutSessionModel.form_score), 0.0)).scalar()
            current_val = round(float(res or 0.0), 1)

        elif goal_type == "EXERCISE_PR":
            res = query.with_entities(func.coalesce(func.max(WorkoutSessionModel.repetitions), 0)).scalar()
            current_val = float(res or 0)

        # Compute percentage
        target_val = float(goal.target_value)
        percentage = min(100.0, round((current_val / target_val) * 100.0, 1)) if target_val > 0 else 0.0

        # State transition to completed
        if current_val >= target_val and not goal.is_completed:
            goal.is_completed = True
            goal.completed_at = now
            db.commit()
            db.refresh(goal)

        # Days remaining
        days_remaining = None
        if end_date:
            diff = (end_date - now).days
            days_remaining = max(0, diff) if end_date > now else 0

        # Exercise name
        exercise_name = None
        if goal.exercise_id:
            ex = db.query(ExerciseModel).filter(ExerciseModel.id == goal.exercise_id).first()
            if ex:
                exercise_name = ex.name

        return GoalProgressResponse(
            id=goal.id,
            user_id=goal.user_id,
            exercise_id=goal.exercise_id,
            exercise_name=exercise_name,
            goal_type=goal.goal_type,
            target_value=target_val,
            current_value=current_val,
            progress_percentage=percentage,
            time_frame=goal.time_frame,
            start_date=start_date,
            end_date=end_date,
            is_completed=goal.is_completed,
            completed_at=goal.completed_at,
            created_at=goal.created_at,
            days_remaining=days_remaining
        )

goal_service = GoalService()
