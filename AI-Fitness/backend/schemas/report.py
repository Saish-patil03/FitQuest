from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ExercisePracticedStat(BaseModel):
    exercise_name: str
    total_reps: int
    total_sets: int
    avg_form_score: float
    muscle_group: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReportAvailabilityItem(BaseModel):
    period_days: int
    title: str
    subtitle: str
    is_available: bool
    required_days: int
    user_history_days: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    formatted_date_range: Optional[str] = None
    status_message: str

    model_config = ConfigDict(from_attributes=True)


class ReportAvailabilityResponse(BaseModel):
    user_id: int
    user_name: str
    user_history_days: int
    reports: List[ReportAvailabilityItem]

    model_config = ConfigDict(from_attributes=True)


class ReportHeader(BaseModel):
    report_title: str
    user_name: str
    user_email: str
    period_days: int
    start_date: datetime
    end_date: datetime
    formatted_date_range: str
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportOverview(BaseModel):
    workouts_completed: int
    total_active_days: int
    total_duration_min: int
    total_sets: int
    total_reps: int
    avg_form_score: Optional[float] = None
    consistency_percentage: float
    current_streak: int
    longest_streak: int

    model_config = ConfigDict(from_attributes=True)


class WorkoutProgressSection(BaseModel):
    workouts_completed: int
    total_active_days: int
    total_duration_min: int
    total_sets: int
    total_reps: int
    top_exercises: List[ExercisePracticedStat] = []
    consistency_trend: str
    summary_message: str

    model_config = ConfigDict(from_attributes=True)


class MovementProgressSection(BaseModel):
    avg_form_score: Optional[float] = None
    form_change_percentage: Optional[float] = None
    strongest_areas: List[str] = []
    focus_areas: List[str] = []
    control_summary: str

    model_config = ConfigDict(from_attributes=True)


class ReadinessRecoverySection(BaseModel):
    readiness_score: Optional[int] = None
    readiness_status: str
    recovery_score: Optional[int] = None
    recovery_status: str
    training_load_zone: str
    observation: str

    model_config = ConfigDict(from_attributes=True)


class NutritionProgressSection(BaseModel):
    has_nutrition_profile: bool = False
    daily_calories_target: Optional[int] = None
    protein_g_target: Optional[int] = None
    carbs_g_target: Optional[int] = None
    fat_g_target: Optional[int] = None
    meals_logged_count: int = 0
    adherence_summary: str

    model_config = ConfigDict(from_attributes=True)


class AchievementsSection(BaseModel):
    longest_streak: int = 0
    completed_goals_count: int = 0
    completed_goals: List[str] = []
    earned_achievements_count: int = 0
    earned_achievements: List[str] = []
    highlights_summary: str

    model_config = ConfigDict(from_attributes=True)


class WhatChangedSection(BaseModel):
    has_sufficient_comparison_data: bool
    first_half_workouts: int = 0
    second_half_workouts: int = 0
    first_half_avg_form: Optional[float] = None
    second_half_avg_form: Optional[float] = None
    form_score_change: Optional[float] = None
    workout_count_change: int = 0
    comparison_summary: str

    model_config = ConfigDict(from_attributes=True)


class FitQuestReportResponse(BaseModel):
    header: ReportHeader
    overview: ReportOverview
    workout_progress: WorkoutProgressSection
    movement_progress: MovementProgressSection
    readiness_recovery: ReadinessRecoverySection
    nutrition: NutritionProgressSection
    achievements: AchievementsSection
    what_changed: WhatChangedSection
    ai_summary: str
    ai_provider: str
    next_steps: List[str]

    model_config = ConfigDict(from_attributes=True)
