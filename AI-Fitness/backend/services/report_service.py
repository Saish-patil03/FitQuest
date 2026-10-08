import io
import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models.user import UserModel
from backend.models.workout import WorkoutSessionModel
from backend.models.exercise import ExerciseModel
from backend.models.structured_workout import StructuredWorkoutSessionModel, StructuredWorkoutSetModel
from backend.models.movement_fingerprint import MovementFingerprintModel
from backend.models.goal import UserGoalModel
from backend.models.nutrition import NutritionProfileModel, NutritionMealLogModel
from backend.models.achievement import UserAchievementModel

from backend.services.gamification_service import gamification_service
from backend.services.readiness_service import readiness_service
from backend.services.training_load_service import training_load_service
from backend.config import settings

from backend.schemas.report import (
    ExercisePracticedStat,
    ReportAvailabilityItem,
    ReportAvailabilityResponse,
    ReportHeader,
    ReportOverview,
    WorkoutProgressSection,
    MovementProgressSection,
    ReadinessRecoverySection,
    NutritionProgressSection,
    AchievementsSection,
    WhatChangedSection,
    FitQuestReportResponse,
)


class ReportService:
    """
    Service for generating deterministic and AI-enhanced user progress reports
    and rendering downloadable PDF documents using ReportLab.
    """

    ALLOWED_PERIODS = [15, 30, 60, 90]

    PERIOD_METADATA = {
        15: {
            "title": "15-Day Progress Report",
            "subtitle": "Your first progress snapshot",
        },
        30: {
            "title": "30-Day Progress Report",
            "subtitle": "Your monthly progress overview",
        },
        60: {
            "title": "60-Day Progress Report",
            "subtitle": "Your longer-term athletic progression",
        },
        90: {
            "title": "90-Day Progress Report",
            "subtitle": "Your transformation overview",
        },
    }

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        cleaned_key = api_key.strip() if api_key and isinstance(api_key, str) else None
        self.api_key = cleaned_key or settings.effective_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model_name = model_name
        self.genai_client = None
        self.types = None

        if self.api_key:
            try:
                from google import genai
                from google.genai import types
                self.types = types
                self.genai_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                self.genai_client = None

    @staticmethod
    def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def get_user_history_days(self, db: Session, user: UserModel, now: Optional[datetime] = None) -> int:
        """
        Calculates the active history span in days for a user based on account creation
        or the earliest recorded workout session.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        now = self._ensure_utc(now)

        earliest_dates = []
        if user.created_at:
            earliest_dates.append(self._ensure_utc(user.created_at))

        first_workout = (
            db.query(func.min(WorkoutSessionModel.started_at))
            .filter(WorkoutSessionModel.user_id == user.id)
            .scalar()
        )
        if first_workout:
            earliest_dates.append(self._ensure_utc(first_workout))

        if not earliest_dates:
            return 1

        oldest = min(earliest_dates)
        diff_days = (now.date() - oldest.date()).days + 1
        return max(1, diff_days)

    def get_report_availability(self, db: Session, user_id: int, now: Optional[datetime] = None) -> ReportAvailabilityResponse:
        """
        Determines the availability of 15, 30, 60, and 90-day progress reports for a user.
        """
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        if now is None:
            now = datetime.now(timezone.utc)

        history_days = self.get_user_history_days(db, user, now)
        items: List[ReportAvailabilityItem] = []

        for period in self.ALLOWED_PERIODS:
            meta = self.PERIOD_METADATA[period]
            is_avail = history_days >= period
            start_date = now - timedelta(days=period)
            end_date = now

            if is_avail:
                status_msg = "Available to view and download"
            else:
                days_left = period - history_days
                if days_left <= 1:
                    status_msg = f"Available in {days_left} day"
                else:
                    status_msg = f"Available in {days_left} days"

            items.append(
                ReportAvailabilityItem(
                    period_days=period,
                    title=meta["title"],
                    subtitle=meta["subtitle"],
                    is_available=is_avail,
                    required_days=period,
                    user_history_days=history_days,
                    start_date=start_date,
                    end_date=end_date,
                    formatted_date_range=f"{start_date.strftime('%B %d, %Y')} – {end_date.strftime('%B %d, %Y')}",
                    status_message=status_msg,
                )
            )

        return ReportAvailabilityResponse(
            user_id=user.id,
            user_name=user.name,
            user_history_days=history_days,
            reports=items,
        )

    def generate_progress_report(
        self, db: Session, user_id: int, period_days: int, now: Optional[datetime] = None
    ) -> FitQuestReportResponse:
        """
        Aggregates historical data and generates a complete, structured Progress Report.
        """
        if period_days not in self.ALLOWED_PERIODS:
            raise ValueError(f"Invalid reporting period '{period_days}'. Supported periods are: {self.ALLOWED_PERIODS}")

        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        if now is None:
            now = datetime.now(timezone.utc)

        history_days = self.get_user_history_days(db, user, now)
        if history_days < period_days:
            days_needed = period_days - history_days
            raise ValueError(
                f"Keep going — your {period_days}-day report will be available once you have enough history ({days_needed} more day{'s' if days_needed > 1 else ''} needed)."
            )

        start_date = now - timedelta(days=period_days)
        end_date = now

        # 1. Fetch workout sessions within boundary
        workouts = (
            db.query(WorkoutSessionModel)
            .filter(
                WorkoutSessionModel.user_id == user.id,
                WorkoutSessionModel.started_at >= start_date,
                WorkoutSessionModel.started_at <= end_date,
            )
            .order_by(WorkoutSessionModel.started_at.asc())
            .all()
        )

        # 2. Basic aggregates
        workouts_completed = len(workouts)
        active_dates = set()
        total_duration_sec = 0
        total_reps = 0
        form_scores = []

        exercise_stats_map: Dict[str, Dict[str, Any]] = {}

        for w in workouts:
            if w.started_at:
                active_dates.add(w.started_at.date())
            total_duration_sec += w.duration_sec or 0
            total_reps += w.repetitions or 0
            if w.form_score is not None and w.form_score > 0:
                form_scores.append(w.form_score)

            ex_name = w.exercise.name if w.exercise else "Exercise"
            muscle_grp = w.exercise.muscle_group if w.exercise else None

            if ex_name not in exercise_stats_map:
                exercise_stats_map[ex_name] = {
                    "total_reps": 0,
                    "total_sets": 0,
                    "form_scores": [],
                    "muscle_group": muscle_grp,
                }
            exercise_stats_map[ex_name]["total_reps"] += w.repetitions or 0
            exercise_stats_map[ex_name]["total_sets"] += 1
            if w.form_score is not None and w.form_score > 0:
                exercise_stats_map[ex_name]["form_scores"].append(w.form_score)

        # 3. Structured workouts sets count
        structured_sets_count = (
            db.query(func.count(StructuredWorkoutSetModel.id))
            .join(StructuredWorkoutSessionModel, StructuredWorkoutSetModel.structured_session_id == StructuredWorkoutSessionModel.id)
            .filter(
                StructuredWorkoutSessionModel.user_id == user.id,
                StructuredWorkoutSessionModel.started_at >= start_date,
                StructuredWorkoutSessionModel.started_at <= end_date,
            )
            .scalar()
        ) or 0

        total_sets = max(workouts_completed, structured_sets_count)
        total_active_days = len(active_dates)
        total_duration_min = round(total_duration_sec / 60)
        avg_form_score = round(sum(form_scores) / len(form_scores), 1) if form_scores else None
        consistency_percentage = round((total_active_days / period_days) * 100, 1)

        # Top exercises
        top_exercises: List[ExercisePracticedStat] = []
        for name, data in sorted(exercise_stats_map.items(), key=lambda item: item[1]["total_reps"], reverse=True):
            ex_avg_form = round(sum(data["form_scores"]) / len(data["form_scores"]), 1) if data["form_scores"] else 0.0
            top_exercises.append(
                ExercisePracticedStat(
                    exercise_name=name,
                    total_reps=data["total_reps"],
                    total_sets=data["total_sets"],
                    avg_form_score=ex_avg_form,
                    muscle_group=data["muscle_group"],
                )
            )

        # 4. Gamification data
        streak_data = gamification_service.get_user_streak(db, user.id)
        current_streak = streak_data.current_streak if hasattr(streak_data, "current_streak") else getattr(streak_data, "current_streak", 0)
        longest_streak = streak_data.longest_streak if hasattr(streak_data, "longest_streak") else getattr(streak_data, "longest_streak", 0)

        achievements_list = gamification_service.get_user_achievements(db, user.id)
        earned_achievements = [
            a.title if hasattr(a, "title") else a.get("title", "")
            for a in achievements_list
            if (hasattr(a, "earned") and a.earned) or (isinstance(a, dict) and a.get("earned"))
        ]

        # Goals completed in period
        completed_goals_query = (
            db.query(UserGoalModel)
            .filter(
                UserGoalModel.user_id == user.id,
                UserGoalModel.is_completed == True,
                UserGoalModel.completed_at >= start_date,
                UserGoalModel.completed_at <= end_date,
            )
            .all()
        )
        completed_goals = [f"{g.goal_type} Goal: {g.target_value} target achieved" for g in completed_goals_query]

        # 5. Readiness & Training Load
        readiness_res = readiness_service.calculate_user_readiness(db, user.id)
        training_load_res = training_load_service.calculate_user_training_load(db, user.id)

        # 6. Nutrition data
        nut_profile = db.query(NutritionProfileModel).filter(NutritionProfileModel.user_id == user.id).first()
        meal_logs_count = (
            db.query(func.count(NutritionMealLogModel.id))
            .filter(
                NutritionMealLogModel.user_id == user.id,
                NutritionMealLogModel.logged_at >= start_date,
                NutritionMealLogModel.logged_at <= end_date,
            )
            .scalar()
        ) or 0

        # 7. What Changed Calculation (First half vs Second half)
        midpoint_date = start_date + timedelta(days=period_days / 2)
        first_half_workouts = [
            w for w in workouts
            if self._ensure_utc(w.started_at or start_date) < midpoint_date
        ]
        second_half_workouts = [
            w for w in workouts
            if self._ensure_utc(w.started_at or start_date) >= midpoint_date
        ]

        first_half_count = len(first_half_workouts)
        second_half_count = len(second_half_workouts)
        workout_count_change = second_half_count - first_half_count

        first_half_forms = [w.form_score for w in first_half_workouts if w.form_score and w.form_score > 0]
        second_half_forms = [w.form_score for w in second_half_workouts if w.form_score and w.form_score > 0]

        first_half_avg_form = round(sum(first_half_forms) / len(first_half_forms), 1) if first_half_forms else None
        second_half_avg_form = round(sum(second_half_forms) / len(second_half_forms), 1) if second_half_forms else None

        form_score_change = None
        if first_half_avg_form is not None and second_half_avg_form is not None:
            form_score_change = round(second_half_avg_form - first_half_avg_form, 1)

        has_comparison_data = (first_half_count > 0 or second_half_count > 0)

        if not has_comparison_data:
            comparison_summary = "Not enough workout data in this period to compare first-half vs second-half progression."
        elif form_score_change is not None and form_score_change > 0:
            comparison_summary = f"Your movement control improved by +{form_score_change}% in the second half of this period with {second_half_count} workouts completed."
        elif form_score_change is not None and form_score_change < 0:
            comparison_summary = f"Your second-half workouts averaged {second_half_avg_form}%, showing steady volume across {second_half_count} sessions."
        elif second_half_count > first_half_count:
            comparison_summary = f"Your workout consistency increased in the second half ({second_half_count} workouts vs {first_half_count} in the first half)."
        else:
            comparison_summary = f"You maintained steady workout consistency across both halves of this {period_days}-day period."

        # 8. Movement Progress
        strongest_areas = []
        focus_areas = []
        if top_exercises:
            sorted_by_form = sorted([e for e in top_exercises if e.avg_form_score > 0], key=lambda x: x.avg_form_score, reverse=True)
            if sorted_by_form:
                strongest_areas = [f"{e.exercise_name} ({e.avg_form_score}%)" for e in sorted_by_form[:2]]
                if len(sorted_by_form) > 2:
                    focus_areas = [f"{e.exercise_name} ({e.avg_form_score}%)" for e in sorted_by_form[-2:] if e.avg_form_score < 85]

        if not strongest_areas:
            strongest_areas = ["General movement control"]

        if avg_form_score and avg_form_score >= 85:
            control_summary = "Your movement quality is high, demonstrating strong posture and controlled execution."
        elif avg_form_score and avg_form_score >= 70:
            control_summary = "Your movement is steady and improving. Focus on maintaining a consistent tempo throughout each repetition."
        elif avg_form_score:
            control_summary = "You are building foundational control. Keep focusing on clean form and full range of motion."
        else:
            control_summary = "Complete more movement-tracked workouts to build your form score profile."

        # 9. Readiness observation
        readiness_status = readiness_res.status if hasattr(readiness_res, "status") else "READY_TO_TRAIN"
        readiness_score = readiness_res.readiness_score if hasattr(readiness_res, "readiness_score") else None
        recovery_score = training_load_res.recovery_score if hasattr(training_load_res, "recovery_score") else None
        recovery_status = training_load_res.recovery_status if hasattr(training_load_res, "recovery_status") else "MODERATELY_RECOVERED"
        training_load_zone = training_load_res.training_load_zone if hasattr(training_load_res, "training_load_zone") else "OPTIMAL"

        if readiness_score and readiness_score >= 80:
            readiness_obs = "Most of your training days showed high readiness and strong recovery."
        elif readiness_score and readiness_score >= 60:
            readiness_obs = "Your recovery patterns remained healthy with good balance between workout intensity and rest."
        else:
            readiness_obs = "Your readiness metrics suggest prioritizing restful sleep and active recovery between hard workout sessions."

        # 10. Nutrition summary
        if nut_profile:
            has_nut_prof = True
            cal_target = nut_profile.target_calories
            prot_target = round(nut_profile.target_protein_g) if nut_profile.target_protein_g else None
            carbs_target = round(nut_profile.target_carbs_g) if nut_profile.target_carbs_g else None
            fat_target = round(nut_profile.target_fat_g) if nut_profile.target_fat_g else None
            if meal_logs_count > 0:
                nut_summary = f"You logged {meal_logs_count} meal{'s' if meal_logs_count > 1 else ''} and stayed focused on your daily target of {cal_target} kcal."
            elif cal_target:
                nut_summary = f"Your nutrition profile is configured with a {cal_target} kcal daily target."
            else:
                nut_summary = "Your nutrition profile is active. Track daily meals to see nutrition adherence."
        else:
            has_nut_prof = False
            cal_target = None
            prot_target = None
            carbs_target = None
            fat_target = None
            nut_summary = "Nutrition tracking is available in the Nutrition section to help align meals with workout performance."

        # 11. Achievements summary
        if earned_achievements:
            ach_summary = f"You have unlocked {len(earned_achievements)} achievement badge{'s' if len(earned_achievements) > 1 else ''} and maintained a longest streak of {longest_streak} days."
        else:
            ach_summary = f"Stay consistent with your daily workouts to unlock milestone badges and streak achievements."

        # 12. Workout summary message
        if workouts_completed > 0:
            wo_summary_msg = f"You completed {workouts_completed} workout{'s' if workouts_completed > 1 else ''} across {total_active_days} active days ({total_reps} total repetitions)."
        else:
            wo_summary_msg = "No workout sessions recorded during this specific period."

        if total_active_days >= (period_days * 0.5):
            consistency_trend = "High Consistency"
        elif total_active_days >= (period_days * 0.25):
            consistency_trend = "Moderate Consistency"
        else:
            consistency_trend = "Building Habit"

        # 13. AI / Deterministic Summary & Next Steps
        ai_summary, ai_provider = self._generate_report_summary(
            user=user,
            period_days=period_days,
            workouts_completed=workouts_completed,
            total_active_days=total_active_days,
            total_reps=total_reps,
            avg_form_score=avg_form_score,
            form_score_change=form_score_change,
            longest_streak=longest_streak,
            readiness_status=readiness_status,
        )

        next_steps = self._generate_next_steps(
            workouts_completed=workouts_completed,
            total_active_days=total_active_days,
            period_days=period_days,
            avg_form_score=avg_form_score,
            focus_areas=focus_areas,
            readiness_score=readiness_score,
        )

        header = ReportHeader(
            report_title=f"{period_days}-Day FitQuest Progress Report",
            user_name=user.name,
            user_email=user.email,
            period_days=period_days,
            start_date=start_date,
            end_date=end_date,
            formatted_date_range=f"{start_date.strftime('%B %d, %Y')} – {end_date.strftime('%B %d, %Y')}",
            generated_at=now,
        )

        overview = ReportOverview(
            workouts_completed=workouts_completed,
            total_active_days=total_active_days,
            total_duration_min=total_duration_min,
            total_sets=total_sets,
            total_reps=total_reps,
            avg_form_score=avg_form_score,
            consistency_percentage=consistency_percentage,
            current_streak=current_streak,
            longest_streak=longest_streak,
        )

        workout_section = WorkoutProgressSection(
            workouts_completed=workouts_completed,
            total_active_days=total_active_days,
            total_duration_min=total_duration_min,
            total_sets=total_sets,
            total_reps=total_reps,
            top_exercises=top_exercises,
            consistency_trend=consistency_trend,
            summary_message=wo_summary_msg,
        )

        movement_section = MovementProgressSection(
            avg_form_score=avg_form_score,
            form_change_percentage=form_score_change,
            strongest_areas=strongest_areas,
            focus_areas=focus_areas,
            control_summary=control_summary,
        )

        readiness_section = ReadinessRecoverySection(
            readiness_score=readiness_score,
            readiness_status=readiness_status,
            recovery_score=recovery_score,
            recovery_status=recovery_status,
            training_load_zone=training_load_zone,
            observation=readiness_obs,
        )

        nutrition_section = NutritionProgressSection(
            has_nutrition_profile=has_nut_prof,
            daily_calories_target=cal_target,
            protein_g_target=prot_target,
            carbs_g_target=carbs_target,
            fat_g_target=fat_target,
            meals_logged_count=meal_logs_count,
            adherence_summary=nut_summary,
        )

        achievements_section = AchievementsSection(
            longest_streak=longest_streak,
            completed_goals_count=len(completed_goals),
            completed_goals=completed_goals,
            earned_achievements_count=len(earned_achievements),
            earned_achievements=earned_achievements,
            highlights_summary=ach_summary,
        )

        what_changed_section = WhatChangedSection(
            has_sufficient_comparison_data=has_comparison_data,
            first_half_workouts=first_half_count,
            second_half_workouts=second_half_count,
            first_half_avg_form=first_half_avg_form,
            second_half_avg_form=second_half_avg_form,
            form_score_change=form_score_change,
            workout_count_change=workout_count_change,
            comparison_summary=comparison_summary,
        )

        return FitQuestReportResponse(
            header=header,
            overview=overview,
            workout_progress=workout_section,
            movement_progress=movement_section,
            readiness_recovery=readiness_section,
            nutrition=nutrition_section,
            achievements=achievements_section,
            what_changed=what_changed_section,
            ai_summary=ai_summary,
            ai_provider=ai_provider,
            next_steps=next_steps,
        )

    def _generate_report_summary(
        self,
        user: UserModel,
        period_days: int,
        workouts_completed: int,
        total_active_days: int,
        total_reps: int,
        avg_form_score: Optional[float],
        form_score_change: Optional[float],
        longest_streak: int,
        readiness_status: str,
    ) -> Tuple[str, str]:
        """
        Generates a friendly personalized summary using Gemini AI with 100% deterministic fallback.
        """
        # Try Gemini API if client is available
        if self.genai_client:
            try:
                prompt = f"""
You are the FitQuest AI Fitness Coach. Write a short, encouraging, 2-3 sentence progress summary for {user.name}'s {period_days}-day progress report.
Key metrics:
- Workouts completed: {workouts_completed} (over {total_active_days} active days)
- Total repetitions: {total_reps}
- Average form score: {avg_form_score or 'N/A'}% (Change: {form_score_change or 0:+.1f}%)
- Longest streak: {longest_streak} days
- Readiness: {readiness_status}
- Fitness goal: {user.fitness_goal or 'General Fitness'}

Guidelines:
- Keep the language extremely simple, friendly, and non-technical.
- Do NOT use medical jargon.
- Highlight their consistency or form progress.
- Keep it under 60 words.
"""
                response = self.genai_client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                if response and response.text:
                    cleaned = response.text.strip()
                    if cleaned:
                        return cleaned, "FitQuest AI Coach"
            except Exception:
                pass

        # Deterministic Fallback Engine
        if workouts_completed > 0:
            form_text = f" with an average form quality of {avg_form_score}%" if avg_form_score else ""
            if form_score_change and form_score_change > 0:
                trend_text = f" Your movement control noticeably improved by +{form_score_change}% over this period."
            else:
                trend_text = " You maintained steady exercise control throughout your sessions."

            summary = (
                f"Great job on your {period_days}-day journey! You completed {workouts_completed} workouts ({total_reps} reps){form_text}.{trend_text} Keep building on this solid routine!"
            )
        else:
            summary = (
                f"You're set up for success on your {period_days}-day journey. As you complete more workouts, FitQuest will track your form progress, consistency, and strength gains."
            )

        return summary, "FitQuest Intelligence"

    def _generate_next_steps(
        self,
        workouts_completed: int,
        total_active_days: int,
        period_days: int,
        avg_form_score: Optional[float],
        focus_areas: List[str],
        readiness_score: Optional[int],
    ) -> List[str]:
        """
        Generates 2 to 4 data-grounded, easy-to-follow recommendations.
        """
        steps = []
        # Step 1: Frequency / consistency
        if total_active_days < (period_days * 0.2):
            steps.append("Aim for 2 to 3 workout sessions each week to build strong exercise habits.")
        else:
            steps.append("Maintain your current workout rhythm and stay active on regular training days.")

        # Step 2: Form & Movement
        if avg_form_score and avg_form_score < 80 and focus_areas:
            steps.append(f"Focus on smooth tempo and controlled reps during {focus_areas[0].split('(')[0].strip()}.")
        elif avg_form_score and avg_form_score >= 80:
            steps.append("Continue executing clean, controlled repetitions with full range of motion.")
        else:
            steps.append("Follow real-time audio and visual form cues during live workouts.")

        # Step 3: Recovery
        if readiness_score and readiness_score < 70:
            steps.append("Allow at least 1 full rest or light recovery day between higher-intensity workouts.")
        else:
            steps.append("Ensure balanced hydration and adequate sleep to support steady recovery.")

        return steps[:3]

    def render_pdf(self, report: FitQuestReportResponse) -> bytes:
        """
        Renders a clean, high-quality, professional PDF progress report using ReportLab.
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            HRFlowable,
            KeepTogether,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Custom FitQuest Palette
        c_primary = colors.HexColor("#0f172a") # Navy/Slate
        c_accent = colors.HexColor("#4d7c0f") # Forest/Lime accent
        c_accent_light = colors.HexColor("#ecfccb") # Soft lime background
        c_dark = colors.HexColor("#1e293b")
        c_muted = colors.HexColor("#64748b")
        c_bg_card = colors.HexColor("#f8fafc")
        c_border = colors.HexColor("#e2e8f0")
        c_white = colors.HexColor("#ffffff")

        # Typography Styles
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=c_primary,
            spaceAfter=2,
        )

        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=c_muted,
            spaceAfter=10,
        )

        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=c_primary,
            spaceBefore=12,
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=c_dark,
        )

        body_muted = ParagraphStyle(
            "ReportBodyMuted",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=c_muted,
        )

        stat_label_style = ParagraphStyle(
            "StatLabel",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=c_muted,
            alignment=1, # Center
        )

        stat_val_style = ParagraphStyle(
            "StatValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=c_primary,
            alignment=1, # Center
        )

        story = []

        # ----------------------------------------------------
        # 1. HEADER BANNER
        # ----------------------------------------------------
        header_data = [
            [
                Paragraph("<b>FITQUEST</b>", ParagraphStyle("Brand", fontName="Helvetica-Bold", fontSize=14, textColor=c_accent)),
                Paragraph(f"Generated: {report.header.generated_at.strftime('%b %d, %Y')}", ParagraphStyle("GenDate", fontName="Helvetica", fontSize=8.5, textColor=c_muted, alignment=2)),
            ],
            [
                Paragraph(f"{report.header.report_title}", title_style),
                Paragraph(f"<b>Athlete:</b> {report.header.user_name}<br/><b>Period:</b> {report.header.formatted_date_range}", subtitle_style),
            ]
        ]
        header_table = Table(header_data, colWidths=[3.8 * inch, 3.4 * inch])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1, color=c_border, spaceBefore=0, spaceAfter=10))

        # ----------------------------------------------------
        # 2. OVERVIEW METRICS GRID (6 Stat Boxes)
        # ----------------------------------------------------
        form_str = f"{report.overview.avg_form_score}%" if report.overview.avg_form_score else "--"
        overview_boxes = [
            [
                [Paragraph("Workouts", stat_label_style), Paragraph(f"{report.overview.workouts_completed}", stat_val_style)],
                [Paragraph("Active Days", stat_label_style), Paragraph(f"{report.overview.total_active_days}", stat_val_style)],
                [Paragraph("Training Time", stat_label_style), Paragraph(f"{report.overview.total_duration_min} min", stat_val_style)],
                [Paragraph("Total Reps", stat_label_style), Paragraph(f"{report.overview.total_reps}", stat_val_style)],
                [Paragraph("Avg Form Quality", stat_label_style), Paragraph(form_str, stat_val_style)],
                [Paragraph("Longest Streak", stat_label_style), Paragraph(f"{report.overview.longest_streak}d", stat_val_style)],
            ]
        ]
        
        box_width = 1.18 * inch
        overview_table = Table(overview_boxes, colWidths=[box_width] * 6)
        overview_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_bg_card),
            ("BOX", (0, 0), (-1, -1), 1, c_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, c_border),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(overview_table)
        story.append(Spacer(1, 12))

        # ----------------------------------------------------
        # 3. WORKOUT PROGRESS & EXERCISES
        # ----------------------------------------------------
        story.append(Paragraph("Workout Progress", section_heading))
        story.append(Paragraph(f"{report.workout_progress.summary_message} Consistency rating: <b>{report.workout_progress.consistency_trend}</b> ({report.overview.consistency_percentage}% of period active).", body_style))
        story.append(Spacer(1, 6))

        if report.workout_progress.top_exercises:
            ex_rows = [[
                Paragraph("<b>Exercise</b>", ParagraphStyle("ExH", fontName="Helvetica-Bold", fontSize=8.5, textColor=c_primary)),
                Paragraph("<b>Muscle Group</b>", ParagraphStyle("ExH", fontName="Helvetica-Bold", fontSize=8.5, textColor=c_primary)),
                Paragraph("<b>Total Sets</b>", ParagraphStyle("ExH", fontName="Helvetica-Bold", fontSize=8.5, textColor=c_primary, alignment=1)),
                Paragraph("<b>Total Reps</b>", ParagraphStyle("ExH", fontName="Helvetica-Bold", fontSize=8.5, textColor=c_primary, alignment=1)),
                Paragraph("<b>Avg Form</b>", ParagraphStyle("ExH", fontName="Helvetica-Bold", fontSize=8.5, textColor=c_primary, alignment=1)),
            ]]
            for ex in report.workout_progress.top_exercises[:4]:
                form_text = f"{ex.avg_form_score}%" if ex.avg_form_score > 0 else "--"
                ex_rows.append([
                    Paragraph(ex.exercise_name, body_style),
                    Paragraph(ex.muscle_group or "General", body_muted),
                    Paragraph(str(ex.total_sets), ParagraphStyle("C", parent=body_style, alignment=1)),
                    Paragraph(str(ex.total_reps), ParagraphStyle("C", parent=body_style, alignment=1)),
                    Paragraph(form_text, ParagraphStyle("C", parent=body_style, alignment=1)),
                ])
            ex_table = Table(ex_rows, colWidths=[2.2 * inch, 1.8 * inch, 1.0 * inch, 1.0 * inch, 1.2 * inch])
            ex_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), c_bg_card),
                ("BOX", (0, 0), (-1, -1), 0.5, c_border),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, c_border),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(ex_table)
            story.append(Spacer(1, 10))

        # ----------------------------------------------------
        # 4. TWO-COLUMN SECTION: MOVEMENT & READINESS
        # ----------------------------------------------------
        strong_str = ", ".join(report.movement_progress.strongest_areas) if report.movement_progress.strongest_areas else "General Movement"
        focus_str = ", ".join(report.movement_progress.focus_areas) if report.movement_progress.focus_areas else "Maintain steady reps"

        left_content = [
            Paragraph("Movement & Form Quality", section_heading),
            Paragraph(report.movement_progress.control_summary, body_style),
            Spacer(1, 4),
            Paragraph(f"<b>Strongest Areas:</b> {strong_str}", body_style),
            Paragraph(f"<b>Focus Areas:</b> {focus_str}", body_style),
        ]

        readiness_score_str = f"{report.readiness_recovery.readiness_score}/100" if report.readiness_recovery.readiness_score else "Optimal"
        right_content = [
            Paragraph("Readiness & Recovery", section_heading),
            Paragraph(report.readiness_recovery.observation, body_style),
            Spacer(1, 4),
            Paragraph(f"<b>Readiness:</b> {report.readiness_recovery.readiness_status.replace('_', ' ').title()} ({readiness_score_str})", body_style),
            Paragraph(f"<b>Training Load:</b> {report.readiness_recovery.training_load_zone.replace('_', ' ').title()} Zone", body_style),
        ]

        two_col_table = Table([[left_content, right_content]], colWidths=[3.5 * inch, 3.5 * inch])
        two_col_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, 0), 0),
            ("RIGHTPADDING", (0, 0), (0, 0), 10),
            ("LEFTPADDING", (1, 0), (1, 0), 10),
            ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(two_col_table)
        story.append(Spacer(1, 10))

        # ----------------------------------------------------
        # 5. WHAT CHANGED (FIRST HALF VS SECOND HALF)
        # ----------------------------------------------------
        story.append(Paragraph("What Changed This Period", section_heading))
        what_changed_box = [
            [
                Paragraph(f"<b>Period Progression:</b> {report.what_changed.comparison_summary}", body_style)
            ]
        ]
        if report.what_changed.has_sufficient_comparison_data:
            f_form = f"{report.what_changed.first_half_avg_form}%" if report.what_changed.first_half_avg_form else "--"
            s_form = f"{report.what_changed.second_half_avg_form}%" if report.what_changed.second_half_avg_form else "--"
            what_changed_box.append([
                Paragraph(
                    f"First Half: <b>{report.what_changed.first_half_workouts}</b> workouts (Avg Form: <b>{f_form}</b>) &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"Second Half: <b>{report.what_changed.second_half_workouts}</b> workouts (Avg Form: <b>{s_form}</b>)",
                    body_muted
                )
            ])
        wc_table = Table(what_changed_box, colWidths=[7.2 * inch])
        wc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_bg_card),
            ("BOX", (0, 0), (-1, -1), 1, c_border),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(wc_table)
        story.append(Spacer(1, 10))

        # ----------------------------------------------------
        # 6. AI COACH SUMMARY & NEXT STEPS
        # ----------------------------------------------------
        summary_box = [
            [
                Paragraph("<b>FitQuest AI Coach Summary</b>", ParagraphStyle("AISumTitle", fontName="Helvetica-Bold", fontSize=10, textColor=c_accent)),
            ],
            [
                Paragraph(f"\"{report.ai_summary}\"", ParagraphStyle("AISumBody", fontName="Helvetica-Oblique", fontSize=9.5, leading=13.5, textColor=c_dark)),
            ]
        ]
        ai_table = Table(summary_box, colWidths=[7.2 * inch])
        ai_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_accent_light),
            ("BOX", (0, 0), (-1, -1), 1, c_accent),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(ai_table)
        story.append(Spacer(1, 10))

        # Next Steps
        story.append(Paragraph("Your Next Steps", section_heading))
        for idx, step in enumerate(report.next_steps, start=1):
            story.append(Paragraph(f"<b>{idx}.</b> {step}", body_style))
            story.append(Spacer(1, 2))

        # Build Document
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes


report_service = ReportService()
