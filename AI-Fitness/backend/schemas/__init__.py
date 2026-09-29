from backend.schemas.user import (
    UserCreate,
    UserResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordResponse
)
from backend.schemas.exercise import ExerciseResponse
from backend.schemas.workout import WorkoutSessionCreate, WorkoutSessionResponse, FormLogCreate, FormLogResponse
from backend.schemas.coaching import AICoachingLogCreate, AICoachingLogResponse
from backend.schemas.achievement import StreakResponse, AchievementResponse
from backend.schemas.nutrition import (
    NutritionProfileUpdate,
    NutritionProfileResponse,
    MealItemSchema,
    DayMealPlanSchema,
    NutritionPlanResponse,
    MealRegenerateRequest,
    MealLogCreate,
    MealLogResponse,
    TodayNutritionSummaryResponse,
    FoodAnalysisRequest,
    FoodAnalysisResponse,
)

from backend.schemas.report import (
    ReportAvailabilityItem,
    ReportAvailabilityResponse,
    FitQuestReportResponse,
)
from backend.schemas.leaderboard import (
    LeaderboardBadge,
    LeaderboardEntry,
    CurrentUserLeaderboardStatus,
    LeaderboardResponse,
)

__all__ = [
    "UserCreate",
    "UserResponse",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "ForgotPasswordResponse",
    "ResetPasswordResponse",
    "ExerciseResponse",
    "WorkoutSessionCreate",
    "WorkoutSessionResponse",
    "FormLogCreate",
    "FormLogResponse",
    "AICoachingLogCreate",
    "AICoachingLogResponse",
    "StreakResponse",
    "AchievementResponse",
    "NutritionProfileUpdate",
    "NutritionProfileResponse",
    "MealItemSchema",
    "DayMealPlanSchema",
    "NutritionPlanResponse",
    "MealRegenerateRequest",
    "MealLogCreate",
    "MealLogResponse",
    "TodayNutritionSummaryResponse",
    "FoodAnalysisRequest",
    "FoodAnalysisResponse",
    "ReportAvailabilityItem",
    "ReportAvailabilityResponse",
    "FitQuestReportResponse",
    "LeaderboardBadge",
    "LeaderboardEntry",
    "CurrentUserLeaderboardStatus",
    "LeaderboardResponse",
]


