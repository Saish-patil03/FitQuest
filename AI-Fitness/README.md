# AI Fitness Engine — 20 Exercise Standalone CV System

A modular, real-time exercise tracking and posture analysis system built using Python, OpenCV, and Ultralytics YOLO Pose.

## 🚀 Supported Exercises (20 Total)

1. **Bicep Curl** (`exercises/bicep_curl.py`)
2. **Squat** (`exercises/squat.py`)
3. **Push-up** (`exercises/pushup.py`)
4. **Lunges** (`exercises/lunges.py`)
5. **Shoulder Press** (`exercises/shoulder_press.py`)
6. **Jumping Jacks** (`exercises/jumping_jacks.py`)
7. **High Knees** (`exercises/high_knees.py`)
8. **Mountain Climbers** (`exercises/mountain_climbers.py`)
9. **Plank** (`exercises/plank.py`)
10. **Glute Bridge** (`exercises/glute_bridge.py`)
11. **Sit-ups** (`exercises/situps.py`)
12. **Crunches** (`exercises/crunches.py`)
13. **Leg Raises** (`exercises/leg_raise.py`)
14. **Russian Twists** (`exercises/russian_twist.py`)
15. **Bicycle Crunches** (`exercises/bicycle_crunch.py`)
16. **Side Lunges** (`exercises/side_lunge.py`)
17. **Calf Raises** (`exercises/calf_raise.py`)
18. **Front Raises** (`exercises/front_raise.py`)
19. **Lateral Raises** (`exercises/lateral_raise.py`)
20. **Tricep Extensions** (`exercises/tricep_extension.py`)

---

## 📁 Modular Directory Architecture

```text
AI-Fitness/
│
├── models/
│   └── pose_model.pt       # Pretrained YOLOv8 Pose weights
├── utils/
│   ├── angles.py           # Angle math, inclination, EMA smoothing
│   ├── keypoints.py        # Landmark extraction & confidence validation
│   └── counter.py          # BaseExerciseTracker standard interface
├── exercises/
│   ├── registry.py         # Central ExerciseRegistry mapping
│   ├── bicep_curl.py
│   ├── squat.py
│   ├── pushup.py
│   ├── lunges.py
│   ├── shoulder_press.py
│   ├── jumping_jacks.py
│   ├── high_knees.py
│   ├── mountain_climbers.py
│   ├── plank.py
│   ├── glute_bridge.py
│   ├── situps.py
│   ├── crunches.py
│   ├── leg_raise.py
│   ├── russian_twist.py
│   ├── bicycle_crunch.py
│   ├── side_lunge.py
│   ├── calf_raise.py
│   ├── front_raise.py
│   ├── lateral_raise.py
│   └── tricep_extension.py
├── pose.py                  # PoseDetector & camera feed stream
├── exercise.py              # ExerciseController wrapper
├── main.py                  # CLI selector menu & camera loop runner
├── test_all_exercises.py    # Comprehensive test suite
├── requirements.txt
└── README.md
```

---

## ⚙️ How to Run

1. **Activate Virtual Environment**:
   ```bash
   cd AI-Fitness
   source .venv/bin/activate
   ```

2. **Run Test Suites**:
   ```bash
   python test_all_exercises.py
   python test_exercise.py
   ```

3. **Launch Engine**:
   ```bash
   python main.py
   ```

Select any exercise from **1 to 20** or type **Q** to exit and view your Workout Summary report.
