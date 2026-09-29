import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.models.user import UserModel
from backend.models.workout import WorkoutSessionModel
from backend.services.gamification_service import gamification_service
from backend.services.readiness_service import readiness_service
from backend.schemas.leaderboard import (
    LeaderboardBadge,
    LeaderboardEntry,
    CurrentUserLeaderboardStatus,
    LeaderboardResponse,
)

class LeaderboardService:
    """
    Deterministic Leaderboard Service for FitQuest V1.
    Calculates period-specific (Weekly, Monthly, All-Time) rankings based on:
      1. Workout Performance (30%)
      2. Consistency / Streak (25%)
      3. Form Quality (20%)
      4. Improvement (15%)
      5. Readiness / Recovery (10%)
    Strictly anti-farming, bounded, deterministic, and free of generative AI.
    """

    ALLOWED_PERIODS = ["weekly", "monthly", "all_time"]

    @staticmethod
    def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def get_period_boundaries(self, period: str, now: Optional[datetime] = None) -> Tuple[Optional[datetime], Optional[datetime], Optional[datetime], Optional[datetime]]:
        """
        Calculates UTC start and end bounds for the current and previous calendar periods.
        Returns: (curr_start, curr_end, prev_start, prev_end)
        """
        if now is None:
            now = datetime.now(timezone.utc)
        now = self._ensure_utc(now)

        if period == "weekly":
            # Monday 00:00:00 UTC of current week
            curr_start = datetime.combine(now.date() - timedelta(days=now.weekday()), time.min, tzinfo=timezone.utc)
            curr_end = now
            # Previous calendar week (Monday to Sunday)
            prev_start = curr_start - timedelta(days=7)
            prev_end = curr_start
            return curr_start, curr_end, prev_start, prev_end

        elif period == "monthly":
            # 1st day of current calendar month 00:00:00 UTC
            curr_start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
            curr_end = now
            # Previous calendar month
            if now.month == 1:
                prev_start = datetime(now.year - 1, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
            else:
                prev_start = datetime(now.year, now.month - 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            prev_end = curr_start
            return curr_start, curr_end, prev_start, prev_end

        elif period == "all_time":
            # Cumulative: no start boundary, end boundary is now
            return None, now, None, None

        else:
            raise ValueError(f"Invalid leaderboard period '{period}'. Allowed periods: {self.ALLOWED_PERIODS}")

    def _get_user_period_workouts(
        self,
        db: Session,
        user_id: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[WorkoutSessionModel]:
        """
        Retrieves valid workout sessions (repetitions >= 1) for a user within specified date bounds.
        """
        query = db.query(WorkoutSessionModel).filter(
            WorkoutSessionModel.user_id == user_id,
            WorkoutSessionModel.repetitions >= 1
        )
        if start_date is not None:
            query = query.filter(WorkoutSessionModel.started_at >= start_date)
        if end_date is not None:
            query = query.filter(WorkoutSessionModel.started_at <= end_date)

        return query.order_by(WorkoutSessionModel.started_at.asc()).all()

    # -------------------------------------------------------------------------
    # COMPONENT 1: WORKOUT PERFORMANCE (30%)
    # -------------------------------------------------------------------------
    def calculate_performance_component(
        self,
        period: str,
        sessions: List[WorkoutSessionModel]
    ) -> float:
        """
        Calculates normalized workout performance [0.0, 100.0].
        Anti-farming safeguards:
          - Workouts capped at realistic calendar limits (up to 40 pts)
          - Repetitions dampened via square-root scaling (up to 35 pts)
          - Training duration in minutes capped (up to 25 pts)
        """
        if not sessions:
            return 0.0

        completed_count = len(sessions)
        total_reps = sum(s.repetitions for s in sessions)
        total_duration_sec = sum(s.duration_sec or 0 for s in sessions)
        total_duration_min = total_duration_sec / 60.0

        if period == "weekly":
            # Target: ~5 workouts/week, ~200 reps/week, ~100 active mins/week
            workouts_pts = min(40.0, completed_count * 8.0)
            reps_pts = min(35.0, math.sqrt(total_reps) * 2.5)
            duration_pts = min(25.0, total_duration_min / 4.0)
        elif period == "monthly":
            # Target: ~20 workouts/month, ~800 reps/month, ~400 active mins/month
            workouts_pts = min(40.0, completed_count * 2.0)
            reps_pts = min(35.0, math.sqrt(total_reps) * 1.25)
            duration_pts = min(25.0, total_duration_min / 16.0)
        else:  # all_time
            # Target: ~50 workouts, ~5,000 reps, ~1,000 active mins
            workouts_pts = min(40.0, completed_count * 0.8)
            reps_pts = min(35.0, math.sqrt(total_reps) * 0.5)
            duration_pts = min(25.0, total_duration_min / 40.0)

        raw = workouts_pts + reps_pts + duration_pts
        return round(min(100.0, max(0.0, raw)), 2)

    # -------------------------------------------------------------------------
    # COMPONENT 2: CONSISTENCY / STREAK (25%)
    # -------------------------------------------------------------------------
    def calculate_consistency_component(
        self,
        db: Session,
        user_id: int,
        period: str,
        sessions: List[WorkoutSessionModel]
    ) -> float:
        """
        Calculates normalized consistency [0.0, 100.0].
        Considers active workout days in the period (up to 50 pts)
        and active streak (up to 50 pts).
        """
        if not sessions:
            return 0.0

        # Unique calendar dates with workouts in the period
        active_dates = {
            s.started_at.date() if hasattr(s.started_at, 'date') else s.started_at
            for s in sessions if s.started_at is not None
        }
        active_days = len(active_dates)

        # Retrieve streak metrics from existing gamification service
        streak_data = gamification_service.get_user_streak(db, user_id)
        current_streak = streak_data.current_streak
        longest_streak = streak_data.longest_streak

        if period == "weekly":
            # Target: 5 active days out of 7 (50 pts), 5-day active streak (50 pts)
            active_days_pts = min(50.0, (active_days / 5.0) * 50.0)
            streak_pts = min(50.0, current_streak * 10.0)
        elif period == "monthly":
            # Target: 15 active days out of ~30 (50 pts), 10-day active streak (50 pts)
            active_days_pts = min(50.0, (active_days / 15.0) * 50.0)
            streak_pts = min(50.0, current_streak * 5.0)
        else:  # all_time
            # Target: 30 total workout days (50 pts), 25-day max streak (50 pts)
            active_days_pts = min(50.0, (streak_data.total_workout_days / 30.0) * 50.0)
            streak_pts = min(50.0, max(current_streak, longest_streak) * 2.0)

        raw = active_days_pts + streak_pts
        return round(min(100.0, max(0.0, raw)), 2)

    # -------------------------------------------------------------------------
    # COMPONENT 3: FORM QUALITY (20%)
    # -------------------------------------------------------------------------
    def calculate_form_component(
        self,
        sessions: List[WorkoutSessionModel]
    ) -> float:
        """
        Calculates normalized form quality [0.0, 100.0].
        Consumes existing CV/OpenCV/YOLO form telemetry from WorkoutSessionModel.form_score.
        Uses safe neutral fallback (50.0) if sessions exist but lack valid form data.
        Returns 0.0 if no sessions exist.
        """
        if not sessions:
            return 0.0

        valid_form_scores = [
            s.form_score for s in sessions
            if s.form_score is not None and s.form_score > 0
        ]

        if valid_form_scores:
            avg_form = sum(valid_form_scores) / len(valid_form_scores)
            return round(min(100.0, max(0.0, avg_form)), 2)

        # Neutral fallback for sessions without CV telemetry
        return 50.0

    # -------------------------------------------------------------------------
    # COMPONENT 4: IMPROVEMENT (15%)
    # -------------------------------------------------------------------------
    def calculate_improvement_component(
        self,
        period: str,
        current_sessions: List[WorkoutSessionModel],
        baseline_sessions: List[WorkoutSessionModel]
    ) -> float:
        """
        Calculates normalized improvement [0.0, 100.0].
        Compares recent activity vs earlier baseline.
        Neutral fallback (50.0) if insufficient baseline data exists.
        """
        if not current_sessions:
            return 0.0

        if not baseline_sessions:
            # First period or insufficient historical data
            return 50.0

        # 1. Form Score Delta
        curr_form = [s.form_score for s in current_sessions if s.form_score is not None and s.form_score > 0]
        base_form = [s.form_score for s in baseline_sessions if s.form_score is not None and s.form_score > 0]

        avg_curr_form = (sum(curr_form) / len(curr_form)) if curr_form else 50.0
        avg_base_form = (sum(base_form) / len(base_form)) if base_form else 50.0
        form_delta = avg_curr_form - avg_base_form  # Range approx -20 to +20

        # 2. Volume Delta
        curr_reps = sum(s.repetitions for s in current_sessions)
        base_reps = sum(s.repetitions for s in baseline_sessions)
        vol_delta_ratio = (curr_reps - base_reps) / max(1, base_reps)
        clamped_vol_delta = max(-0.5, min(0.5, vol_delta_ratio))

        # Composite improvement centered at 50.0
        score = 50.0 + (form_delta * 1.5) + (clamped_vol_delta * 30.0)
        return round(min(100.0, max(10.0, score)), 2)

    # -------------------------------------------------------------------------
    # COMPONENT 5: READINESS / RECOVERY (10%)
    # -------------------------------------------------------------------------
    def calculate_readiness_component(
        self,
        db: Session,
        user_id: int,
        has_period_activity: bool
    ) -> float:
        """
        Calculates normalized readiness/recovery [0.0, 100.0].
        Consumes existing ReadinessService.
        Private readiness values are NEVER exposed in public leaderboard responses.
        Uses safe neutral fallback (50.0) if readiness data is unavailable.
        Returns 0.0 if user has no activity at all.
        """
        if not has_period_activity:
            return 0.0

        try:
            readiness_data = readiness_service.calculate_user_readiness(db, user_id)
            if readiness_data.status == "INSUFFICIENT_DATA" or readiness_data.readiness_score is None:
                return 50.0
            return round(min(100.0, max(0.0, float(readiness_data.readiness_score))), 2)
        except Exception:
            return 50.0

    # -------------------------------------------------------------------------
    # COMPOSITE & FITQUEST SCORE SCALING
    # -------------------------------------------------------------------------
    def compute_user_fitquest_score(
        self,
        db: Session,
        user: UserModel,
        period: str,
        curr_start: Optional[datetime],
        curr_end: Optional[datetime],
        prev_start: Optional[datetime],
        prev_end: Optional[datetime]
    ) -> Dict[str, Any]:
        """
        Computes the 5 normalized components, composite score, and final gamified FitQuest Score.
        """
        curr_sessions = self._get_user_period_workouts(db, user.id, curr_start, curr_end)

        if not curr_sessions:
            return {
                "user_id": user.id,
                "display_name": user.name,
                "avatar_initial": user.name[0].upper() if user.name else "A",
                "fitquest_score": 0,
                "streak": 0,
                "normalized_performance": 0.0,
                "normalized_consistency": 0.0,
                "normalized_form": 0.0,
                "normalized_improvement": 0.0,
                "normalized_readiness": 0.0,
                "earliest_achievement_dt": datetime.max.replace(tzinfo=timezone.utc),
                "is_visible": bool(getattr(user, "leaderboard_visible", True)),
                "has_activity": False
            }

        # Baseline sessions for improvement comparison
        if period in ["weekly", "monthly"] and prev_start and prev_end:
            base_sessions = self._get_user_period_workouts(db, user.id, prev_start, prev_end)
        elif period == "all_time":
            # For all-time, compare second half of sessions vs first half if enough data
            half = len(curr_sessions) // 2
            base_sessions = curr_sessions[:half] if half >= 2 else []
        else:
            base_sessions = []

        norm_perf = self.calculate_performance_component(period, curr_sessions)
        norm_cons = self.calculate_consistency_component(db, user.id, period, curr_sessions)
        norm_form = self.calculate_form_component(curr_sessions)
        norm_imp = self.calculate_improvement_component(period, curr_sessions, base_sessions)
        norm_read = self.calculate_readiness_component(db, user.id, has_period_activity=True)

        # 5-Component Deterministic Formula:
        # Workout Performance        30%
        # Consistency / Streak        25%
        # Form Quality                20%
        # Improvement                 15%
        # Readiness / Recovery        10%
        composite = (
            norm_perf * 0.30 +
            norm_cons * 0.25 +
            norm_form * 0.20 +
            norm_imp  * 0.15 +
            norm_read * 0.10
        )

        # Gamified Integer-style Scaling:
        # Converts composite [0, 100] to understandable FitQuest Score range [0, ~3000+]
        # e.g., 94.7% -> 2,840 FitScore; 64% -> 1,920 FitScore; 29.2% -> 875 FitScore
        fitquest_score = int(round(composite * 30.0))

        # Current streak from gamification service
        streak_data = gamification_service.get_user_streak(db, user.id)
        current_streak = streak_data.current_streak

        # Earliest session date in period (tie-breaker signal)
        earliest_dt = curr_sessions[0].started_at if curr_sessions else datetime.max
        earliest_dt = self._ensure_utc(earliest_dt)

        return {
            "user_id": user.id,
            "display_name": user.name,
            "avatar_initial": user.name[0].upper() if user.name else "A",
            "fitquest_score": fitquest_score,
            "streak": current_streak,
            "normalized_performance": norm_perf,
            "normalized_consistency": norm_cons,
            "normalized_form": norm_form,
            "normalized_improvement": norm_imp,
            "normalized_readiness": norm_read,
            "earliest_achievement_dt": earliest_dt,
            "is_visible": bool(getattr(user, "leaderboard_visible", True)),
            "has_activity": True
        }

    # -------------------------------------------------------------------------
    # MAIN LEADERBOARD AGGREGATION & RANKING
    # -------------------------------------------------------------------------
    def get_leaderboard(
        self,
        db: Session,
        current_user_id: int,
        period: str = "weekly",
        now: Optional[datetime] = None
    ) -> LeaderboardResponse:
        """
        Computes and returns the complete Leaderboard response for the authenticated user and period.
        Respects privacy controls, performs deterministic ranking and tie-breaking,
        and provides accurate user-standing metrics.
        """
        if period not in self.ALLOWED_PERIODS:
            raise ValueError(f"Invalid leaderboard period '{period}'. Allowed periods: {self.ALLOWED_PERIODS}")

        curr_start, curr_end, prev_start, prev_end = self.get_period_boundaries(period, now)

        # Fetch all registered users in the database (real data only)
        users = db.query(UserModel).all()

        scored_users: List[Dict[str, Any]] = []
        user_scores_map: Dict[int, Dict[str, Any]] = {}

        for user in users:
            score_data = self.compute_user_fitquest_score(
                db=db,
                user=user,
                period=period,
                curr_start=curr_start,
                curr_end=curr_end,
                prev_start=prev_start,
                prev_end=prev_end
            )
            scored_users.append(score_data)
            user_scores_map[user.id] = score_data

        # Deterministic Ranking Order:
        # 1. Higher FitQuest Score descending
        # 2. Higher Consistency component descending
        # 3. Higher Form component descending
        # 4. Earlier achievement date ascending
        # 5. User ID ascending
        def sort_key(item: Dict[str, Any]):
            return (
                -item["fitquest_score"],
                -item["normalized_consistency"],
                -item["normalized_form"],
                item["earliest_achievement_dt"] or datetime.max.replace(tzinfo=timezone.utc),
                item["user_id"]
            )

        scored_users.sort(key=sort_key)

        # Assign public ranks to visible athletes with activity
        public_entries: List[LeaderboardEntry] = []
        rank_counter = 1

        # Cache of user achievements for badge display
        user_badges_cache: Dict[int, List[LeaderboardBadge]] = {}

        for item in scored_users:
            if not item["is_visible"]:
                continue
            # Only include users with activity or positive score in public rankings
            if not item["has_activity"] and item["fitquest_score"] == 0:
                continue

            uid = item["user_id"]
            if uid not in user_badges_cache:
                achievements = gamification_service.get_user_achievements(db, uid)
                earned = [
                    LeaderboardBadge(id=a.id, title=a.title, icon=a.icon)
                    for a in achievements if a.earned
                ][:3]  # Show up to 3 earned badges
                user_badges_cache[uid] = earned

            entry = LeaderboardEntry(
                rank=rank_counter,
                user_id=item["user_id"],
                display_name=item["display_name"],
                avatar_initial=item["avatar_initial"],
                fitquest_score=item["fitquest_score"],
                streak=item["streak"],
                badges=user_badges_cache[uid]
            )
            public_entries.append(entry)
            item["assigned_rank"] = rank_counter
            rank_counter += 1

        # Calculate Previous Period Ranks for Rank Movement (Weekly & Monthly only)
        prev_ranks_map: Dict[int, int] = {}
        if period in ["weekly", "monthly"] and prev_start and prev_end:
            prev_scored: List[Dict[str, Any]] = []
            for user in users:
                prev_sessions = self._get_user_period_workouts(db, user.id, prev_start, prev_end)
                if prev_sessions:
                    prev_score_data = self.compute_user_fitquest_score(
                        db=db,
                        user=user,
                        period=period,
                        curr_start=prev_start,
                        curr_end=prev_end,
                        prev_start=None,
                        prev_end=None
                    )
                    prev_scored.append(prev_score_data)

            prev_scored.sort(key=sort_key)
            p_rank = 1
            for p_item in prev_scored:
                if p_item["is_visible"] and p_item["has_activity"]:
                    prev_ranks_map[p_item["user_id"]] = p_rank
                    p_rank += 1

        # Build Current User Status
        current_user_obj = user_scores_map.get(current_user_id)
        current_user_status: Optional[CurrentUserLeaderboardStatus] = None

        if current_user_obj:
            curr_rank = current_user_obj.get("assigned_rank")
            is_vis = current_user_obj["is_visible"]
            has_act = current_user_obj["has_activity"]
            user_score = current_user_obj["fitquest_score"]

            # Rank change calculation
            rank_change: Optional[int] = None
            if curr_rank is not None and current_user_id in prev_ranks_map:
                prev_rank = prev_ranks_map[current_user_id]
                # Positive delta means user moved UP (e.g. from 5 to 2 = +3 positions)
                rank_change = prev_rank - curr_rank

            # Points to next rank calculation
            points_to_next: Optional[int] = None
            if curr_rank is not None and curr_rank > 1:
                # Find athlete at curr_rank - 1
                athlete_above = next((e for e in public_entries if e.rank == curr_rank - 1), None)
                if athlete_above:
                    points_to_next = max(1, (athlete_above.fitquest_score - user_score) + 1)
            elif curr_rank is None and public_entries:
                # User has no rank yet, points to reach lowest ranked athlete
                lowest_athlete = public_entries[-1]
                points_to_next = max(1, (lowest_athlete.fitquest_score - user_score) + 1)

            # Encouraging status messages
            message = None
            if not is_vis:
                message = "Private Mode — You are hidden from the public leaderboard. You can re-enable visibility in your Profile."
            elif not has_act:
                message = "Complete your first workout this period to join the leaderboard!"
            elif curr_rank == 1:
                if len(public_entries) == 1:
                    message = "You're currently #1! Keep training — more athletes will appear as the FitQuest community grows."
                else:
                    message = "You're leading the leaderboard! Keep defending your position."

            current_user_status = CurrentUserLeaderboardStatus(
                rank=curr_rank,
                user_id=current_user_id,
                display_name=current_user_obj["display_name"],
                avatar_initial=current_user_obj["avatar_initial"],
                fitquest_score=user_score,
                streak=current_user_obj["streak"],
                rank_change=rank_change,
                points_to_next_rank=points_to_next,
                is_visible=is_vis,
                message=message
            )

        updated_at_iso = (now or datetime.now(timezone.utc)).isoformat()

        return LeaderboardResponse(
            period=period,
            updated_at=updated_at_iso,
            total_athletes=len(public_entries),
            entries=public_entries,
            current_user=current_user_status
        )

# Singleton instance
leaderboard_service = LeaderboardService()
