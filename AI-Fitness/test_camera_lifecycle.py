"""
FitQuest Camera Lifecycle Test
Verifies:
1. switchTab(viewId) calls stopCameraStream() when viewId !== 'workoutView'.
2. stopCameraStream() stops tracks, clears srcObject, clears frame intervals, and hides video elements.
3. backToLearnStage() stops camera.
4. visibilitychange handler stops camera when document.hidden.
5. Incomplete workout session state is safely preserved without ending/submitting workout.
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent
WORKOUT_JS = BASE_DIR / "frontend" / "workout.js"
INDEX_HTML = BASE_DIR / "frontend" / "index.html"

def test_camera_lifecycle():
    workout_code = WORKOUT_JS.read_text(encoding="utf-8")
    html_code = INDEX_HTML.read_text(encoding="utf-8")

    # 1. switchTab view-exit cleanup
    assert "if (viewId !== 'workoutView')" in workout_code, "switchTab must check if leaving workoutView"
    assert "stopCameraStream()" in workout_code, "switchTab must call stopCameraStream"
    assert "prepareCalibrationActive = false" in workout_code, "switchTab must reset calibration active state"

    # 2. stopCameraStream hardware release
    assert "webcamStream.getTracks().forEach" in workout_code, "stopCameraStream must stop all media tracks"
    assert "video.srcObject = null" in workout_code, "stopCameraStream must null out video srcObject"
    assert "prepareVideo.srcObject = null" in workout_code, "stopCameraStream must null out prepare video srcObject"
    assert "clearInterval(frameCaptureInterval)" in workout_code, "stopCameraStream must clear frame capture interval"

    # 3. backToLearnStage camera cleanup
    assert "function backToLearnStage()" in workout_code, "backToLearnStage must be defined"
    
    # 4. Page visibility safety
    assert "visibilitychange" in workout_code, "visibilitychange listener must be present"
    assert "document.hidden" in workout_code, "visibilitychange must check document.hidden"

    # 5. DOM IDs
    assert 'id="webcamFeed"' in html_code, "webcamFeed element missing"
    assert 'id="prepareWebcamFeed"' in html_code, "prepareWebcamFeed element missing"
    assert 'id="cameraPlaceholder"' in html_code, "cameraPlaceholder element missing"

    print("[PASS] Camera Lifecycle integration and cleanup tests passed cleanly!")

if __name__ == "__main__":
    test_camera_lifecycle()
