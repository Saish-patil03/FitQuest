import sys
from pathlib import Path

# Ensure app package directory is on sys.path so utils and exercises resolve cleanly
_app_dir = str(Path(__file__).resolve().parent)
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)
