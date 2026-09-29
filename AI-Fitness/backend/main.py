import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import init_db_with_retry
from backend.api.users import router as users_router
from backend.api.exercises import router as exercises_router
from backend.api.workouts import router as workouts_router
from backend.api.ai import router as ai_router
from backend.api.auth import router as auth_router
from backend.api.streaks import router as streaks_router
from backend.api.achievements import router as achievements_router
from backend.api.analytics import router as analytics_router
from backend.api.goals import router as goals_router
from backend.api.readiness import router as readiness_router
from backend.api.training_load import router as training_load_router
from backend.api.structured_workouts import router as structured_workouts_router
from backend.api.adaptive_training import router as adaptive_training_router
from backend.api.movement_dna import router as movement_dna_router
from backend.api.movement_copilot import router as movement_copilot_router
from backend.api.body_sim import router as body_sim_router
from backend.api.guide import router as guide_router
from backend.api.nutrition import router as nutrition_router
from backend.api.reports import router as reports_router
from backend.api.leaderboard import router as leaderboard_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables and seed exercises on startup with bounded retry
    init_db_with_retry()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI Backend Foundation for FitQuest / AI-Fitness Platform",
    lifespan=lifespan
)

# Configure CORS for development & frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.APP_NAME
    }

# API metadata endpoint
@app.get("/api")
def read_api_metadata():
    return {
        "status": "running",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "api_v1_prefix": "/api/v1"
    }

# Mount API v1 Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(streaks_router, prefix="/api/v1")
app.include_router(achievements_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(exercises_router, prefix="/api/v1")
app.include_router(workouts_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(goals_router, prefix="/api/v1")
app.include_router(readiness_router, prefix="/api/v1")
app.include_router(training_load_router, prefix="/api/v1")
app.include_router(structured_workouts_router, prefix="/api/v1")
app.include_router(adaptive_training_router, prefix="/api/v1")
app.include_router(movement_dna_router, prefix="/api/v1")
app.include_router(movement_copilot_router, prefix="/api/v1")
app.include_router(body_sim_router, prefix="/api/v1")
app.include_router(guide_router, prefix="/api/v1")
app.include_router(nutrition_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(leaderboard_router, prefix="/api/v1")

# Mount frontend static files directory for unified single-server deployment
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
