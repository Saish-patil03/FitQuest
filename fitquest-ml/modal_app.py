import sys
from pathlib import Path
import modal

# ---------------------------------------------------------------------------
# 1. Modal Application Definition
# ---------------------------------------------------------------------------
app = modal.App("fitquest-ml")

# Resolve local directories relative to this file
FITQUEST_ML_DIR = Path(__file__).resolve().parent
REQUIREMENTS_PATH = FITQUEST_ML_DIR / "requirements-ml.txt"
APP_DIR = FITQUEST_ML_DIR / "app"
MODELS_DIR = FITQUEST_ML_DIR / "models"

# ---------------------------------------------------------------------------
# 2. Container Image Specification
# - Debian slim with Python 3.10
# - Required OS libraries for OpenCV (libgl1, libglib2.0-0)
# - Python packages from requirements-ml.txt
# - Packaged application code and model weights (under /root/fitquest-ml)
# ---------------------------------------------------------------------------
image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install_from_requirements(str(REQUIREMENTS_PATH))
    .add_local_dir(str(MODELS_DIR), remote_path="/root/fitquest-ml/models")
    .add_local_dir(str(APP_DIR), remote_path="/root/fitquest-ml/app")
)

# ---------------------------------------------------------------------------
# 3. Serverless ASGI Function
# - CPU only (cpu=2.0)
# - Memory: 2048 MB
# - Idle timeout: 300 seconds
# - Concurrency limit: 1 (maintains in-memory session stickiness for workouts)
# ---------------------------------------------------------------------------
@app.function(
    image=image,
    cpu=2.0,
    memory=2048,
    scaledown_window=300,
    max_containers=1,
)
@modal.asgi_app()
def fastapi_app():
    """
    Exposes the existing FitQuest ML FastAPI application via Modal ASGI.
    Loads existing routes, schemas, and CV algorithms from app/main.py.
    Preserves all routes:
      - GET  /health
      - POST /live/start-session
      - POST /live/process-frame
      - POST /live/stop-session
      - POST /workouts/live/start-session
      - POST /workouts/live/process-frame
      - POST /workouts/live/stop-session
    """
    app_remote_dir = "/root/fitquest-ml/app"
    if Path(app_remote_dir).exists():
        if app_remote_dir not in sys.path:
            sys.path.insert(0, app_remote_dir)
    else:
        # Fallback for local testing environments
        app_local_dir = str(APP_DIR)
        if app_local_dir not in sys.path:
            sys.path.insert(0, app_local_dir)

    from main import app as existing_app
    return existing_app
