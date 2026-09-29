import sys

def verify():
    print("=== AI Fitness Environment Verification ===")
    print(f"Python Version: {sys.version}")

    try:
        import cv2
        print(f"[SUCCESS] OpenCV version: {cv2.__version__}")
    except ImportError as e:
        print(f"[FAIL] OpenCV import failed: {e}")

    try:
        import numpy as np
        print(f"[SUCCESS] NumPy version: {np.__version__}")
    except ImportError as e:
        print(f"[FAIL] NumPy import failed: {e}")

    try:
        from ultralytics import YOLO
        print("[SUCCESS] Ultralytics YOLO imported successfully")
    except ImportError as e:
        print(f"[FAIL] Ultralytics import failed: {e}")

    print("==========================================")

if __name__ == "__main__":
    verify()
