import sys
import time
# pyrefly: ignore [missing-import]
import cv2
from pose import PoseDetector
from exercise import ExerciseController
from exercises import ExerciseRegistry

def display_menu():
    print("""
================================================================
               AI FITNESS ENGINE — 20 EXERCISES
================================================================
  [1]  Bicep Curl         [2]  Squat               [3]  Push-up
  [4]  Lunges             [5]  Shoulder Press      [6]  Jumping Jacks
  [7]  High Knees         [8]  Mountain Climbers   [9]  Plank
  [10] Glute Bridge       [11] Sit-ups             [12] Crunches
  [13] Leg Raises         [14] Russian Twists      [15] Bicycle Crunches
  [16] Side Lunges        [17] Calf Raises         [18] Front Raises
  [19] Lateral Raises     [20] Tricep Extensions   [Q]  Exit Program
================================================================
""")

def run_app():
    display_menu()
    choice = input("Enter exercise choice (1-20 or Q): ").strip().upper()

    if choice == 'Q':
        print("[INFO] Exiting AI Fitness Engine. Goodbye!")
        sys.exit(0)

    valid_choices = [str(i) for i in range(1, 21)]
    if choice not in valid_choices:
        print("[WARNING] Invalid selection. Defaulting to [1] Bicep Curl.")
        choice = '1'

    # Instantiate Controller & Detector with conf_threshold=0.25
    controller = ExerciseController(choice)
    detector = PoseDetector(model_path="models/pose_model.pt", conf_threshold=0.25)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Could not open webcam device (Index 0). Please check camera permissions.")
        return

    print(f"\n[INFO] Starting workout session for: {controller.tracker.name}")
    print("[INFO] Position yourself in front of the camera.")
    print("[INFO] Press 'q' on the video window to end your workout.\n")

    window_name = f"AI Fitness Engine - {controller.tracker.name}"
    prev_time = time.time()

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("[WARNING] Frame capture failed. Exiting camera loop.")
                break

            # Process frame: YOLO Pose -> keypoint extraction -> tracker update -> HUD overlay
            annotated_frame, keypoints, tracker_info = detector.process_frame(
                frame, tracker=controller.tracker, draw_debug_hud=True, clean_overlay=False
            )

            # Calculate & overlay FPS
            curr_time = time.time()
            fps = 1.0 / (curr_time - prev_time + 1e-6)
            prev_time = curr_time
            cv2.putText(annotated_frame, f"FPS: {int(fps)}", (frame.shape[1] - 110, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

            cv2.imshow(window_name, annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n[INFO] User ended workout session.")
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

        # Print Final Workout Summary Report
        summary = controller.finish_session()
        print(summary)


if __name__ == "__main__":
    run_app()
