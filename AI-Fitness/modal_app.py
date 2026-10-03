import sys
from pathlib import Path
import modal

ROOT_DIR = Path(__file__).resolve().parent
REQUIREMENTS_PATH = ROOT_DIR / "requirements.txt"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install_from_requirements(str(REQUIREMENTS_PATH))
    .add_local_dir(str(ROOT_DIR / "backend"), remote_path="/root/backend")
    .add_local_dir(str(ROOT_DIR / "assistant"), remote_path="/root/assistant")
    .add_local_dir(str(ROOT_DIR / "assistant"), remote_path="/root/backend/assistant")
    .add_local_dir(str(ROOT_DIR / "exercises"), remote_path="/root/exercises")
    .add_local_dir(str(ROOT_DIR / "utils"), remote_path="/root/utils")
    .add_local_dir(str(ROOT_DIR / "models"), remote_path="/root/models")
    .add_local_file(str(ROOT_DIR / "pose.py"), remote_path="/root/pose.py")
    .add_local_file(str(ROOT_DIR / "exercise.py"), remote_path="/root/exercise.py")
)

app = modal.App("fitquest-backend")
data_volume = modal.Volume.from_name("fitquest-data", create_if_missing=True)

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("fitquest-secrets")],
    volumes={"/data": data_volume},
    cpu=2.0,
    memory=2048,
    scaledown_window=300
)
@modal.asgi_app()
def serve():
    import sys
    root_path = "/root"
    if root_path not in sys.path:
        sys.path.insert(0, root_path)

    from backend.main import app as web_app
    return web_app