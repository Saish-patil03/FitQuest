"""
FitQuest ONNX Model Export Utility
Exports Ultralytics YOLOv8n-Pose to ONNX format with 480p dynamic image dimensions
for hardware-accelerated WebGL / WebGPU in-browser inference with ONNX Runtime Web.
"""

import sys
import os

def export_model():
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] Ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    weights_path = "models/pose_model.pt"
    if not os.path.exists(weights_path):
        weights_path = "yolov8n-pose.pt"

    print(f"[INFO] Loading YOLOv8n-pose model from '{weights_path}'...")
    model = YOLO(weights_path)

    print("[INFO] Exporting to ONNX format (imgsz=480, dynamic=True)...")
    try:
        exported_path = model.export(
            format="onnx",
            imgsz=480,
            dynamic=True,
            simplify=True
        )
        print(f"[SUCCESS] Model successfully exported to: {exported_path}")
        print("Copy this file to 'frontend/models/yolov8n-pose.onnx' or host it on your CDN.")
    except Exception as e:
        print(f"[ERROR] Failed to export ONNX model: {e}")
        print("Note: Exporting to ONNX requires 'onnx' and 'onnxslim'. Run: pip install onnx onnxslim")

if __name__ == "__main__":
    export_model()
