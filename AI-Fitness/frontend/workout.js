/**
 * FitQuest Workout Flow Engine & Multi-View Router
 * Manages Exercise Selection, Setup, Live Webcam + YOLO Pose Telemetry HUD, Results & History.
 */

// Global State
let allExercises = [];
let selectedExercise = null;
let workoutTimerInterval = null;
let workoutStartTime = null;
let workoutElapsedSeconds = 0;

// Live CV & Camera State
let webcamStream = null;
let frameCaptureInterval = null;
let frameCount = 0;
let isProcessingFrame = false;
let animationFrameId = null;
const FRAME_SKIP_RATIO = 2; // Process every 2nd frame (~15 FPS inference, cutting compute load in half)
let workoutSocket = null;
let activeSessionId = null;
let currentRepCount = 0;
let currentFormScore = 100.0;
let accumulatedFeedback = [];
let demoAvatarEngine = null;
let learnDemoAvatarEngine = null;

// Single-Exercise Workout Prescription & Multi-Set Progression State
let currentExercisePrescription = {
  sets: 3,
  reps: 10,
  restSeconds: 60,
  tempo: '2-0-2',
  focus: 'Controlled Movement',
  recommendation: 'Your current readiness supports 3 sets today.'
};

let activeWorkoutSetsState = {
  currentSetNumber: 1,
  targetSets: 3,
  targetReps: 10,
  restSeconds: 60,
  loggedSets: [],
  isSingleExerciseFlow: true,
  isSetCompleting: false
};

let cachedAdaptiveRecommendations = [];

// Exercise Default Prescriptions map matching backend EXERCISE_METADATA
const EXERCISE_DEFAULT_PRESCRIPTIONS = {
  1: { name: 'Bicep Curl', sets: 3, reps: 10, restSec: 60, tempo: '2-0-2', focus: 'Controlled Eccentric Lowering' },
  2: { name: 'Squat', sets: 3, reps: 12, restSec: 45, tempo: '2-1-2', focus: 'Depth & Knee Tracking' },
  3: { name: 'Push-up', sets: 3, reps: 10, restSec: 45, tempo: '2-1-2', focus: 'Elbow Position & Core Lock' },
  4: { name: 'Lunges', sets: 3, reps: 10, restSec: 45, tempo: '2-0-2', focus: 'Torso Upright & Stride Depth' },
  5: { name: 'Shoulder Press', sets: 3, reps: 10, restSec: 45, tempo: '2-1-2', focus: 'Vertical Lockout & Ribcage Down' },
  6: { name: 'Jumping Jacks', sets: 3, reps: 25, restSec: 30, tempo: '1-0-1', focus: 'Rhythm & Soft Landing' },
  7: { name: 'High Knees', sets: 3, reps: 20, restSec: 30, tempo: '1-0-1', focus: 'Knee Drive & Quick Cadence' },
  8: { name: 'Mountain Climbers', sets: 3, reps: 20, restSec: 30, tempo: '1-0-1', focus: 'Plank Stability & Piston Drive' },
  9: { name: 'Plank', sets: 3, reps: 30, restSec: 45, tempo: 'Static', focus: 'Rigid Core & Neutral Spine' },
  10: { name: 'Glute Bridge', sets: 3, reps: 15, restSec: 30, tempo: '2-1-2', focus: 'Glute Squeeze & Hip Drive' },
  11: { name: 'Sit-ups', sets: 3, reps: 15, restSec: 30, tempo: '2-0-2', focus: 'Full Range & Controlled Return' },
  12: { name: 'Crunches', sets: 3, reps: 15, restSec: 30, tempo: '2-1-2', focus: 'Upper Abdominal Contraction' },
  13: { name: 'Leg Raises', sets: 3, reps: 12, restSec: 30, tempo: '2-0-2', focus: 'Lower Back Contact & Hip Flexion' },
  14: { name: 'Russian Twists', sets: 3, reps: 16, restSec: 30, tempo: '1-1-1', focus: 'Torso Rotation & Oblique Tension' },
  15: { name: 'Bicycle Crunches', sets: 3, reps: 16, restSec: 30, tempo: '1-1-1', focus: 'Elbow-to-Knee Coordination' },
  16: { name: 'Side Lunges', sets: 3, reps: 10, restSec: 45, tempo: '2-0-2', focus: 'Lateral Hip Shift & Depth' },
  17: { name: 'Calf Raises', sets: 3, reps: 18, restSec: 30, tempo: '2-1-2', focus: 'Peak Ankle Extension' },
  18: { name: 'Front Raises', sets: 3, reps: 12, restSec: 30, tempo: '2-0-2', focus: 'Strict Shoulder Elevation' },
  19: { name: 'Lateral Raises', sets: 3, reps: 12, restSec: 30, tempo: '2-0-2', focus: 'Lead with Elbows & Neutral Grip' },
  20: { name: 'Tricep Extensions', sets: 3, reps: 12, restSec: 30, tempo: '2-0-2', focus: 'Elbow Pinned & Full Lockout' }
};

// API Endpoints
var API_BASE = window.getFitQuestApiBase ? window.getFitQuestApiBase() : (window.API_BASE || 'https://fitquest-backend-1brv.onrender.com/api/v1');
// Dedicated Computer Vision & Pose Telemetry Engine Base (Modal ML Microservice)
// Separated from main application backend to ensure heavy webcam frame streams route directly to Modal
const ML_API_BASE = window.getFitQuestMlBase ? window.getFitQuestMlBase() : (window.ML_API_BASE || 'https://nihartambe20--fitquest-ml-fastapi-app.modal.run');

document.addEventListener('DOMContentLoaded', () => {
  initTabNavigation();
  initSearchFilter();
  initWorkoutModeTabs();
  initDemoAvatarEngine();
  loadExerciseCatalogue();
  fetchAdaptiveExerciseRecommendations();
});

/**
 * Fetches user-specific adaptive exercise recommendations if authenticated
 */
async function fetchAdaptiveExerciseRecommendations() {
  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
  if (!token) return;
  try {
    const res = await fetch(`${API_BASE}/adaptive-training/recommendations`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Accept': 'application/json' }
    });
    if (res.ok) {
      cachedAdaptiveRecommendations = await res.json();
    }
  } catch (e) {
    // Non-blocking background fetch
  }
}

/**
 * Resolves the prescription for a specific exercise from adaptive AI or default catalogue
 */
function resolveExercisePrescription(exercise) {
  if (!exercise) return null;
  const exId = typeof exercise === 'object' ? exercise.id : exercise;
  const exName = typeof exercise === 'object' ? exercise.name : '';

  // 1. Check current adaptive plan or cached adaptive recommendations from backend
  const activePlan = (typeof currentAdaptivePlan !== 'undefined' && currentAdaptivePlan) 
    ? currentAdaptivePlan 
    : (window.currentAdaptivePlan || null);

  let adaptiveRec = null;
  if (activePlan && Array.isArray(activePlan.exercises)) {
    adaptiveRec = activePlan.exercises.find(r => (r.exercise_id === exId || r.id === exId || r.exercise_name === exName));
  }
  if (!adaptiveRec && Array.isArray(cachedAdaptiveRecommendations)) {
    adaptiveRec = cachedAdaptiveRecommendations.find(r => r.exercise_id === exId || r.exercise_name === exName);
  }
  
  // 2. Fallback to default catalog prescription
  const defaultMeta = EXERCISE_DEFAULT_PRESCRIPTIONS[exId] || {
    sets: 3,
    reps: 10,
    restSec: 60,
    tempo: '2-0-2',
    focus: 'Controlled Movement'
  };

  const sets = (adaptiveRec && adaptiveRec.target_sets) ? adaptiveRec.target_sets : defaultMeta.sets;
  const reps = (adaptiveRec && adaptiveRec.target_reps) ? adaptiveRec.target_reps : (defaultMeta.reps || 10);
  const restSec = (adaptiveRec && (adaptiveRec.rest_duration_sec || adaptiveRec.restSec)) ? (adaptiveRec.rest_duration_sec || adaptiveRec.restSec) : (defaultMeta.restSec || 60);
  const tempo = (adaptiveRec && adaptiveRec.target_tempo) ? adaptiveRec.target_tempo : (defaultMeta.tempo || '2-0-2');
  const focus = (adaptiveRec && adaptiveRec.focus) ? adaptiveRec.focus : (defaultMeta.focus || 'Controlled Pacing');

  // Generate deterministic AI recommendation
  const recommendation = generateDeterministicAIRecommendation(exId, sets, reps, adaptiveRec);

  return {
    exerciseId: exId,
    exerciseName: exName,
    sets: sets,
    reps: reps,
    restSeconds: restSec,
    tempo: tempo,
    focus: focus,
    recommendation: recommendation
  };
}

/**
 * Generates an explainable, deterministic AI recommendation based on real readiness & adaptive data
 */
function generateDeterministicAIRecommendation(exerciseId, sets, reps, adaptiveRec) {
  // Check global or window readiness if available
  const readinessData = window.currentReadinessData || null;
  const readinessScore = readinessData ? readinessData.readiness_score : null;

  if (adaptiveRec && (adaptiveRec.reason || adaptiveRec.selection_reason)) {
    const reasonText = adaptiveRec.reason || adaptiveRec.selection_reason;
    return `You're ready for ${sets} sets today. ${reasonText}`;
  }

  if (readinessScore !== null && readinessScore !== undefined) {
    if (readinessScore >= 80) {
      return `Your current readiness (${readinessScore}%) supports ${sets} sets at this intensity. Complete each set with strict form.`;
    } else if (readinessScore >= 65) {
      return `Your current readiness (${readinessScore}%) supports ${sets} sets today. Keep cadence steady and controlled.`;
    } else if (readinessScore >= 50) {
      return `Prioritize form stability over speed today. Focus on completing ${sets} controlled sets with clean technique.`;
    } else {
      return `Your readiness is in recovery mode. Keep volume at ${sets} lighter, controlled sets with full rest.`;
    }
  }

  // Fallback deterministic recommendations based on exercise type
  const exMeta = EXERCISE_DEFAULT_PRESCRIPTIONS[exerciseId];
  if (exMeta && exMeta.focus) {
    return `You're ready for ${sets} sets today. Keep each set controlled: focus on ${exMeta.focus.toLowerCase()}.`;
  }

  return `You're ready for ${sets} sets today. Complete one set at a time with full rest between sets.`;
}

/**
 * Initializes the 2D Kinematic Demo Avatar Engine (both Learn & Active stages)
 */
function initDemoAvatarEngine() {
  if (typeof DemoAvatarEngine === 'function') {
    if (!learnDemoAvatarEngine && document.getElementById('learnDemoAvatarCanvas')) {
      learnDemoAvatarEngine = new DemoAvatarEngine('learnDemoAvatarCanvas');
    }
    if (!demoAvatarEngine && document.getElementById('demoAvatarCanvas')) {
      demoAvatarEngine = new DemoAvatarEngine('demoAvatarCanvas');
    }
  }
}

/**
 * Toggles Demo Avatar Play / Pause state
 */
function toggleDemoPlayPause() {
  if (learnDemoAvatarEngine) {
    learnDemoAvatarEngine.togglePlayPause();
  }
  if (demoAvatarEngine) {
    demoAvatarEngine.togglePlayPause();
  }
}

/**
 * Resets Demo Avatar animation to beginning of cycle
 */
function resetDemoAvatar() {
  if (learnDemoAvatarEngine) {
    learnDemoAvatarEngine.reset();
  }
  if (demoAvatarEngine) {
    demoAvatarEngine.reset();
  }
}

/**
 * Adjusts Demo Avatar animation playback speed
 */
function setDemoSpeed(speed) {
  if (learnDemoAvatarEngine) {
    learnDemoAvatarEngine.setSpeed(speed);
  }
  if (demoAvatarEngine) {
    demoAvatarEngine.setSpeed(speed);
  }
  document.querySelectorAll('.demo-speed-btn').forEach(btn => {
    if (parseFloat(btn.dataset.speed) === speed) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
}

/**
 * Toggles mobile viewports (Split View, Demo Only, Camera Only)
 */
function switchWorkoutViewport(mode) {
  const grid = document.getElementById('workoutViewportsGrid');
  const buttons = document.querySelectorAll('.vp-switch-btn');
  if (!grid) return;

  grid.classList.remove('view-demo-only', 'view-camera-only');
  if (mode === 'demo') {
    grid.classList.add('view-demo-only');
  } else if (mode === 'camera') {
    grid.classList.add('view-camera-only');
  }

  buttons.forEach((btn) => {
    if (btn.getAttribute('data-view') === mode) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  if (demoAvatarEngine && mode !== 'camera') {
    setTimeout(() => demoAvatarEngine.resizeCanvas(), 50);
  }
}

/**
 * Initializes Workout Mode Tab Buttons (Quick vs Structured)
 */
function initWorkoutModeTabs() {
  const quickBtn = document.getElementById('modeQuickBtn');
  const structBtn = document.getElementById('modeStructuredBtn');

  if (quickBtn) {
    quickBtn.addEventListener('click', () => switchWorkoutMode('quick'));
  }
  if (structBtn) {
    structBtn.addEventListener('click', () => switchWorkoutMode('structured'));
  }
}

/**
 * Initializes Top Navigation Bar tab switching
 */
function initTabNavigation() {
  const navTabs = document.querySelectorAll('.nav-tab');
  navTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const viewId = tab.getAttribute('data-view');
      switchTab(viewId);
    });
  });
}

/**
 * Switches active view panel
 */
function switchTab(viewId) {
  // If navigating away from Workout view, safely stop camera & frame loops without modifying workout state
  if (viewId !== 'workoutView') {
    if (webcamStream || frameCaptureInterval || animationFrameId) {
      stopCameraStream();
    }
    prepareCalibrationActive = false;
    if (countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
      const overlay = document.getElementById('workoutCountdownOverlay');
      if (overlay) overlay.style.display = 'none';
      const startBtn = document.getElementById('prepareStartBtn');
      if (startBtn) startBtn.disabled = false;
    }
    if (demoAvatarEngine) {
      demoAvatarEngine.pause();
    }
  }

  const navTabs = document.querySelectorAll('.nav-tab');
  const viewPanels = document.querySelectorAll('.view-panel');

  navTabs.forEach((tab) => {
    if (tab.getAttribute('data-view') === viewId) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });

  viewPanels.forEach((panel) => {
    if (panel.id === viewId) {
      panel.classList.add('active');
    } else {
      panel.classList.remove('active');
    }
  });

  if (viewId === 'homeView') {
    if (typeof loadTrainingReadiness === 'function') loadTrainingReadiness();
    if (typeof loadTrainingLoad === 'function') loadTrainingLoad();
    if (typeof loadPersonalizedGoals === 'function') loadPersonalizedGoals();
    if (typeof loadGamificationData === 'function') loadGamificationData();
    if (typeof loadNutritionView === 'function') loadNutritionView();
  } else if (viewId === 'nutritionView') {
    if (typeof loadNutritionView === 'function') {
      loadNutritionView();
    }
  } else if (viewId === 'workoutView' && allExercises.length === 0) {
    loadExerciseCatalogue();
  } else if (viewId === 'progressView') {
    if (typeof loadProgressAnalytics === 'function') {
      loadProgressAnalytics(typeof activeAnalyticsTimeRange !== 'undefined' ? activeAnalyticsTimeRange : 'all');
    }
  } else if (viewId === 'historyView') {
    loadWorkoutHistory();
  } else if (viewId === 'evolutionView') {
    if (typeof loadMovementEvolution === 'function') {
      loadMovementEvolution();
    }
  } else if (viewId === 'adaptiveTrainingView') {
    if (typeof loadAdaptiveProfile === 'function') {
      loadAdaptiveProfile();
    }
  } else if (viewId === 'movementDnaView') {
    if (typeof loadMovementDNA === 'function') {
      loadMovementDNA();
    }
    if (typeof refreshMovementDNACanvases === 'function') {
      requestAnimationFrame(() => refreshMovementDNACanvases());
    }
  } else if (viewId === 'leaderboardView') {
    if (typeof loadLeaderboardView === 'function') {
      loadLeaderboardView();
    }
  }
}

/**
 * Switches sub-step views inside Workout Experience
 */
function goToStep(stepId) {
  const workoutSteps = document.querySelectorAll('.workout-step');
  workoutSteps.forEach((step) => {
    if (step.id === stepId) {
      step.classList.add('active');
    } else {
      step.classList.remove('active');
    }
  });
}

/**
 * Fetches all 20 seeded exercises from backend API GET /api/v1/exercises
 */
async function loadExerciseCatalogue() {
  const grid = document.getElementById('exerciseGrid');
  if (!grid) return;

  try {
    const response = await fetch(`${API_BASE}/exercises`);
    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}`);
    }

    allExercises = await response.json();
    renderExerciseGrid(allExercises);
  } catch (error) {
    console.error('[FitQuest Error]: Failed to fetch exercises from backend:', error);
    grid.innerHTML = `
      <div class="loading-spinner" style="color: #ef4444;">
        <i class="fa-solid fa-triangle-exclamation"></i> Could not connect to backend server. Make sure FastAPI server is accessible at ${escapeHTML(API_BASE)}.
      </div>
    `;
  }
}

/**
 * Renders exercise cards into selection grid
 */
function renderExerciseGrid(exercises) {
  const grid = document.getElementById('exerciseGrid');
  if (!grid) return;

  if (exercises.length === 0) {
    grid.innerHTML = `<div class="loading-spinner">No matching exercises found.</div>`;
    return;
  }

  grid.innerHTML = exercises.map((ex) => `
    <div class="exercise-card">
      <div>
        <div class="ex-card-header">
          <div class="ex-icon-badge">
            <i class="fa-solid ${getExerciseIcon(ex.name)}"></i>
          </div>
          <span class="ex-difficulty-badge">${ex.difficulty || 'Intermediate'}</span>
        </div>
        <h3 class="ex-title">${escapeHTML(ex.name)}</h3>
        <p class="ex-desc">${escapeHTML(ex.description || 'YOLO Pose Tracker')}</p>
      </div>
      <button class="btn btn-primary" onclick="selectExercise(${ex.id})">
        <i class="fa-solid fa-play"></i> Select Exercise
      </button>
    </div>
  `).join('');
}

/**
 * Exercise search filter
 */
function initSearchFilter() {
  const input = document.getElementById('exerciseSearch');
  if (!input) return;

  input.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    const filtered = allExercises.filter((ex) => 
      ex.name.toLowerCase().includes(query) || 
      (ex.description && ex.description.toLowerCase().includes(query))
    );
    renderExerciseGrid(filtered);
  });
}

/**
 * Comprehensive Exercise Learning Guides (All 20 Seeded Exercises)
 * Structured personal-trainer guidance: Steps, Start/End Positions, Movement Path, Key Cues, Common Mistakes, Camera Setup Tips.
 */
const EXERCISE_LEARNING_GUIDES = {
  1: {
    summary: 'Build upper-arm strength and joint stability with strict elbow control and controlled eccentric lowering.',
    steps: [
      'Stand tall with feet shoulder-width apart, holding weights with palms facing forward.',
      'Keep your elbows pinned close to your torso throughout the entire movement.',
      'Curl the weights upward toward your shoulders by flexing your elbows.',
      'Lower slowly under control for 2–3 seconds until your arms are fully extended.'
    ],
    startPosition: 'Arms fully extended at sides, chest proud, elbows close to torso.',
    endPosition: 'Forearms curled near shoulders without elbows drifting forward.',
    movementPath: ['START: Extended', 'CURL UP: Concentric', 'SQUEEZE: Peak Hold', 'LOWER: Controlled Return'],
    keyCues: ['Keep elbows pinned to your sides', 'Keep your spine tall and torso steady', 'Lower slowly with full extension'],
    mistakes: ['Don\'t swing your torso or hips', 'Don\'t let elbows flare out or drift forward', 'Don\'t rush the lowering phase'],
    cameraTip: 'Place camera at chest height, 6–8 feet away, so your torso and arms are clearly in frame.'
  },
  2: {
    summary: 'A fundamental lower-body movement building quad, glute, and core strength while reinforcing knee and hip mobility.',
    steps: [
      'Stand with feet shoulder-width apart, toes pointing slightly outward (5–15°).',
      'Initiate movement by sending hips back and bending knees simultaneously.',
      'Descend until your thighs are at least parallel to the floor with chest upright.',
      'Drive through your midfoot and heels to return to a full standing posture.'
    ],
    startPosition: 'Standing upright with neutral spine, feet shoulder-width apart.',
    endPosition: 'Thighs parallel to floor, knees tracking over toes, chest proud.',
    movementPath: ['START: Standing', 'DESCENT: Hips Back', 'PARALLEL: Depth Hold', 'DRIVE: Push Through Heels'],
    keyCues: ['Keep knees tracking in line with toes', 'Keep chest proud and back flat', 'Drive weight through midfoot and heels'],
    mistakes: ['Don\'t let knees cave inward', 'Don\'t round your lower back or drop chest', 'Don\'t lift heels off the floor'],
    cameraTip: 'Place camera at waist height, 8–10 feet away, so your entire body from head to feet is visible.'
  },
  3: {
    summary: 'A premier bodyweight compound exercise targeting chest, triceps, anterior shoulders, and core stability.',
    steps: [
      'Set hands slightly wider than shoulder-width apart in a high plank.',
      'Brace core and glutes to keep your body in a rigid line from head to heels.',
      'Lower chest toward the floor by bending elbows back at a 45-degree angle.',
      'Press firmly through your palms to return to full arm extension.'
    ],
    startPosition: 'High plank position, arms extended under shoulders, core braced.',
    endPosition: 'Chest hovering 1–2 inches off floor, elbows at 45° angle.',
    movementPath: ['START: High Plank', 'LOWER: Inhale Down', 'HOVER: Chest Near Floor', 'PRESS: Exhale Lockout'],
    keyCues: ['Maintain straight line from head to heels', 'Tuck elbows at 45° (don\'t flare out at 90°)', 'Lock out arms fully at the top'],
    mistakes: ['Don\'t let hips sag or hike upward', 'Don\'t flare elbows wide like a \'T\'', 'Don\'t crane your neck forward'],
    cameraTip: 'Place camera on the floor or a low riser, 6–8 feet away from your side profile.'
  },
  4: {
    summary: 'Unilateral leg exercise strengthening quads, glutes, and hamstrings while improving balance and hip symmetry.',
    steps: [
      'Stand upright with feet hip-width apart and hands on hips or at chest.',
      'Step forward 2–3 feet with one leg, landing smoothly through your heel.',
      'Lower your back knee toward the floor until both knees form 90-degree angles.',
      'Push through your front heel to step back to the starting upright position.'
    ],
    startPosition: 'Standing upright with feet together, shoulders back and core engaged.',
    endPosition: 'Front thigh parallel to floor, back knee hovering just above floor.',
    movementPath: ['START: Feet Together', 'STEP: Stride Forward', 'LOWER: 90° Knee Angle', 'PUSH: Return to Stand'],
    keyCues: ['Keep torso upright and shoulders back', 'Front knee stays behind or over toes', 'Drive through front heel to return'],
    mistakes: ['Don\'t let front knee collapse inward', 'Don\'t lean torso heavily forward', 'Don\'t slam back knee into the ground'],
    cameraTip: 'Place camera at hip level, 7–9 feet away, capturing your full body in side or diagonal view.'
  },
  5: {
    summary: 'Vertical pressing movement targeting deltoids, upper traps, and triceps with core stabilization.',
    steps: [
      'Stand tall holding weights at shoulder level with palms facing forward.',
      'Brace your core and glutes to avoid overarching your lower back.',
      'Press weights overhead in a smooth path until your arms are fully extended.',
      'Lower slowly back to ear/shoulder level and repeat.'
    ],
    startPosition: 'Hands at shoulder height, elbows slightly in front of body.',
    endPosition: 'Arms fully extended overhead, biceps in line with ears.',
    movementPath: ['START: Shoulder Rack', 'PRESS: Drive Overhead', 'LOCKOUT: Arms Extended', 'LOWER: Control to Shoulders'],
    keyCues: ['Keep ribcage down and core tight', 'Press in a straight vertical path overhead', 'Full lockout at the top without shrugging'],
    mistakes: ['Don\'t arch your lower back excessively', 'Don\'t press weights forward out of line', 'Don\'t bounce or use leg drive for strict press'],
    cameraTip: 'Place camera at chest height, 6–8 feet away, showing head and full arm extension overhead.'
  },
  6: {
    summary: 'Dynamic full-body cardiovascular exercise enhancing heart rate, coordination, and calf/shoulder endurance.',
    steps: [
      'Stand upright with feet together and arms resting at your sides.',
      'Jump feet out to slightly wider than shoulder-width while raising arms overhead.',
      'Clap or bring hands together at top with elbows slightly soft.',
      'Jump feet back together while lowering arms smoothly back to sides.'
    ],
    startPosition: 'Standing upright, feet together, arms resting at sides.',
    endPosition: 'Feet wide apart, arms extended overhead in \'X\' shape.',
    movementPath: ['START: Narrow Stance', 'JUMP OUT: Arms Overhead', 'PEAK: Wide X-Shape', 'JUMP IN: Return to Center'],
    keyCues: ['Land softly on the balls of your feet', 'Keep movement rhythmic and bouncy', 'Reach arms fully overhead on each rep'],
    mistakes: ['Don\'t land with locked, stiff knees', 'Don\'t perform half arm swings', 'Don\'t slouch your upper body'],
    cameraTip: 'Place camera at waist height, 8–10 feet away, showing full body width during wide jumps.'
  },
  7: {
    summary: 'High-intensity aerobic drill targeting hip flexors, quads, calves, and sprint mechanics.',
    steps: [
      'Stand tall with feet hip-width apart and arms in a sprinter position.',
      'Drive right knee up toward chest level while pumping left arm forward.',
      'Land softly on the ball of right foot and immediately drive left knee upward.',
      'Continue alternating legs in a rapid, continuous running cadence.'
    ],
    startPosition: 'Standing upright, weight balanced on the balls of feet.',
    endPosition: 'Thigh lifted parallel to floor (90° hip angle) with upright torso.',
    movementPath: ['DRIVE: Right Knee Up', 'SWITCH: Rapid Transfer', 'DRIVE: Left Knee Up', 'REPEAT: Quick Cadence'],
    keyCues: ['Drive knees up to hip height', 'Stay light on the balls of your feet', 'Pump arms synchronously with legs'],
    mistakes: ['Don\'t lean backward to lift knees', 'Don\'t let knees stay low below waist', 'Don\'t land flat-footed or on heels'],
    cameraTip: 'Place camera at hip level, 7–9 feet away, framing full standing height.'
  },
  8: {
    summary: 'Cardio-core hybrid movement building shoulder stability, core strength, and aerobic capacity.',
    steps: [
      'Begin in a solid high plank with wrists directly beneath shoulders.',
      'Drive right knee forward toward chest without letting hips rise.',
      'Quickly switch legs, extending right leg back while driving left knee forward.',
      'Maintain a steady, rhythmic piston motion while keeping back flat.'
    ],
    startPosition: 'High plank position, hands under shoulders, body straight.',
    endPosition: 'One knee driven near chest while opposite leg remains straight.',
    movementPath: ['PLANK: Stable Base', 'DRIVE: Right Knee In', 'SWITCH: Fluid Transition', 'DRIVE: Left Knee In'],
    keyCues: ['Keep hips level with shoulders (don\'t hike up)', 'Keep wrists stacked directly under shoulders', 'Drive knees straight toward chest'],
    mistakes: ['Don\'t bounce hips up and down', 'Don\'t let shoulders drift behind hands', 'Don\'t hold your breath'],
    cameraTip: 'Place camera on floor or low surface, 6–8 feet away from your side profile.'
  },
  9: {
    summary: 'Isometric core pillar strengthening the entire abdominal wall, lower back, and shoulder girdle.',
    steps: [
      'Place forearms on the floor with elbows directly under shoulders.',
      'Extend legs back and balance on toes with feet hip-width apart.',
      'Brace abdominals as if preparing for a punch and squeeze glutes tight.',
      'Hold this rigid straight-line posture while breathing steadily.'
    ],
    startPosition: 'Forearms and toes on floor, body elevated in neutral line.',
    endPosition: 'Continuous rigid isometric hold from crown of head to heels.',
    movementPath: ['SET: Forearms Under Shoulders', 'BRACE: Core & Glutes Tight', 'HOLD: Flat Spine Line', 'BREATHE: Steady Cadence'],
    keyCues: ['Maintain straight line from head to heels', 'Tuck pelvis slightly (avoid arched low back)', 'Keep neck neutral looking at floor'],
    mistakes: ['Don\'t let hips sag toward the floor', 'Don\'t hike hips up into a tent shape', 'Don\'t hold your breath'],
    cameraTip: 'Place camera 6–8 feet away at floor height, capturing your complete horizontal body profile.'
  },
  10: {
    summary: 'Posterior chain movement activating glutes, hamstrings, and lower back stability.',
    steps: [
      'Lie on your back with knees bent, feet flat on the floor hip-width apart.',
      'Rest arms at your sides with palms pressing lightly into the floor.',
      'Drive through your heels to lift hips upward until thighs and torso align.',
      'Squeeze glutes hard at top for 1–2 seconds, then lower under control.'
    ],
    startPosition: 'Lying supine on back, knees bent at 90°, feet flat on floor.',
    endPosition: 'Hips fully extended in straight line from shoulders to knees.',
    movementPath: ['START: Back on Floor', 'BRIDGE: Drive Through Heels', 'SQUEEZE: Peak Glute Tension', 'LOWER: Tap Floor & Repeat'],
    keyCues: ['Drive through heels (not toes)', 'Squeeze glutes at top without hyperextending back', 'Keep knees tracking hip-width'],
    mistakes: ['Don\'t overarch lower back at the top', 'Don\'t let knees flare outward or collapse in', 'Don\'t lift with your neck or shoulders'],
    cameraTip: 'Place camera at floor height, 6–8 feet away, in side profile.'
  },
  11: {
    summary: 'Full-range abdominal exercise strengthening rectus abdominis, hip flexors, and core stamina.',
    steps: [
      'Lie on your back with knees bent at 90° and feet anchored flat on floor.',
      'Cross arms over chest or lightly touch fingertips to your temples.',
      'Engage abs and curl your torso up smoothly until chest is near thighs.',
      'Lower your spine bone-by-bone back to the floor under control.'
    ],
    startPosition: 'Supine on back, knees bent, lower back resting on floor.',
    endPosition: 'Torso fully upright with chest near knees.',
    movementPath: ['START: Floor', 'CURL UP: Abdominal Flexion', 'TOP: Upright Posture', 'LOWER: Controlled Return'],
    keyCues: ['Lead with your chest and abdominals', 'Keep feet grounded throughout the movement', 'Lower down smoothly (don\'t slam down)'],
    mistakes: ['Don\'t yank your neck with your hands', 'Don\'t use momentum or swing arms', 'Don\'t let feet lift off the ground'],
    cameraTip: 'Place camera on the floor or low surface, 6–8 feet away from your side profile.'
  },
  12: {
    summary: 'Targeted upper abdominal exercise isolating the rectus abdominis with controlled spinal flexion.',
    steps: [
      'Lie on your back with knees bent at 90° and feet flat on floor.',
      'Place fingertips lightly behind ears with elbows open wide.',
      'Contract abdominals to lift shoulder blades 3–4 inches off the floor.',
      'Pause at the peak for 1 second, then lower back slowly without resting.'
    ],
    startPosition: 'Lying on back, lower back pressed into floor, knees bent.',
    endPosition: 'Shoulder blades lifted 3–4 inches off floor, abs contracted.',
    movementPath: ['START: Back on Mat', 'CRUNCH: Lift Shoulders', 'SQUEEZE: Top Contraction', 'LOWER: Control to Floor'],
    keyCues: ['Press lower back firmly into the floor', 'Keep elbows wide and chin off chest', 'Exhale as you crunch upward'],
    mistakes: ['Don\'t pull on your neck or tuck chin into chest', 'Don\'t lift lower back off the floor', 'Don\'t flap elbows forward'],
    cameraTip: 'Place camera at floor height, 5–7 feet away in side profile.'
  },
  13: {
    summary: 'Lower abdominal and hip flexor movement building deep core strength and pelvic control.',
    steps: [
      'Lie flat on your back with legs straight and hands under lower back or at sides.',
      'Press lower back firmly into the floor and point toes slightly.',
      'Raise legs smoothly until they form a 90-degree angle with your torso.',
      'Lower legs slowly back down, stopping 1–2 inches before touching floor.'
    ],
    startPosition: 'Lying flat on back, legs extended straight together.',
    endPosition: 'Legs raised perpendicular to torso (90° vertical angle).',
    movementPath: ['START: Legs Hovering', 'LIFT: Straight Leg Raise', 'VERTICAL: 90° Peak', 'LOWER: Slow Resistance'],
    keyCues: ['Keep lower back pressed flat into the floor', 'Keep legs straight throughout the lift', 'Control the descent without arching back'],
    mistakes: ['Don\'t arch your lower back off the floor', 'Don\'t bend knees excessively to cheat', 'Don\'t let feet slam onto the ground'],
    cameraTip: 'Place camera at floor height, 6–8 feet away in side profile.'
  },
  14: {
    summary: 'Rotational core exercise strengthening obliques, transverse abdominis, and rotational power.',
    steps: [
      'Sit on the floor with knees bent, feet slightly elevated, and lean back 45°.',
      'Hold hands together in front of your chest with core braced tightly.',
      'Rotate your torso smoothly to the right, tapping hands near right hip.',
      'Rotate across center to the left hip in a controlled, rhythmic motion.'
    ],
    startPosition: 'V-sit seated position, torso angled back at 45°, core braced.',
    endPosition: 'Torso rotated fully to side with shoulders following movement.',
    movementPath: ['CENTER: V-Sit Balance', 'TWIST RIGHT: Oblique Contraction', 'PASS CENTER: Control', 'TWIST LEFT: Full Rotation'],
    keyCues: ['Rotate from ribcage and torso (not just arms)', 'Keep spine tall (don\'t slouch back)', 'Keep breathing steadily as you twist'],
    mistakes: ['Don\'t just wave your arms without turning torso', 'Don\'t round your lower spine', 'Don\'t let feet swing uncontrollably'],
    cameraTip: 'Place camera at waist/chest height, 6–8 feet away in front or 45° angle.'
  },
  15: {
    summary: 'High-activation rotational core exercise engaging upper abs, lower abs, and obliques simultaneously.',
    steps: [
      'Lie on your back, hands behind head, knees lifted at 90° table-top.',
      'Bring right elbow toward left knee while extending right leg straight out.',
      'Switch smoothly, bringing left elbow to right knee while extending left leg.',
      'Continue in a fluid pedaling motion with deliberate tempo.'
    ],
    startPosition: 'Supine on back, hands behind head, knees bent at 90°.',
    endPosition: 'Opposite elbow and knee meeting across center, other leg straight.',
    movementPath: ['START: Tabletop', 'CRUNCH: Right to Left', 'SWITCH: Pedal Legs', 'CRUNCH: Left to Right'],
    keyCues: ['Rotate shoulder toward opposite knee (not just elbow)', 'Keep extended leg hovering 6 inches off floor', 'Move with control (2 seconds per side)'],
    mistakes: ['Don\'t yank your neck with your hands', 'Don\'t rush through reps with sloppy form', 'Don\'t let lower back arch off the floor'],
    cameraTip: 'Place camera at floor height, 6–8 feet away in side profile.'
  },
  16: {
    summary: 'Frontal plane leg movement targeting inner thighs (adductors), glutes, and lateral hip mobility.',
    steps: [
      'Stand tall with feet together, hands at chest or hips.',
      'Take a wide step to the right, bending right knee and pushing hips back.',
      'Keep left leg completely straight and both feet flat on the floor.',
      'Push firmly off the right foot to return to the center starting position.'
    ],
    startPosition: 'Standing upright, feet together, core engaged.',
    endPosition: 'Right thigh parallel to floor, left leg extended straight, chest up.',
    movementPath: ['START: Centered', 'STEP OUT: Wide Lateral Stride', 'SIT BACK: Hip Hinge', 'PUSH: Return to Center'],
    keyCues: ['Keep trailing leg completely straight', 'Sit hips back into the lunging heel', 'Keep chest proud and both feet flat'],
    mistakes: ['Don\'t let lunging knee collapse inward', 'Don\'t lift the heel of the lunging foot', 'Don\'t round your spine forward'],
    cameraTip: 'Place camera at waist height, 8–10 feet away in front view to capture full lateral width.'
  },
  17: {
    summary: 'Lower-leg isolation movement strengthening gastrocnemius, soleus, and ankle stability.',
    steps: [
      'Stand tall with feet hip-width apart and hands at sides or on hips.',
      'Press down through balls of feet to raise heels as high as possible.',
      'Hold the peak contraction at the top for 1 full second.',
      'Lower your heels slowly under control until they tap the floor.'
    ],
    startPosition: 'Standing flat-footed, feet hip-width apart, knees soft.',
    endPosition: 'Heels elevated to maximum height, balancing on balls of feet.',
    movementPath: ['START: Flat-Footed', 'DRIVE UP: Triple Extension', 'HOLD: Peak Calf Contraction', 'LOWER: Slow Return'],
    keyCues: ['Drive straight up through the big toes', 'Pause at the very top for maximum squeeze', 'Lower down with 2-second control'],
    mistakes: ['Don\'t roll ankles outward to the sides', 'Don\'t bounce quickly at the bottom', 'Don\'t bend knees to cheat the movement'],
    cameraTip: 'Place camera at knee-to-waist height, 6–8 feet away, showing full lower body.'
  },
  18: {
    summary: 'Shoulder isolation exercise targeting anterior deltoids and upper chest stability.',
    steps: [
      'Stand tall with feet shoulder-width apart holding weights in front of thighs.',
      'Keep arms straight with a very slight, soft bend in your elbows.',
      'Raise weights smoothly in front of you until they reach shoulder height.',
      'Lower slowly back to your thighs under strict control.'
    ],
    startPosition: 'Standing upright, weights resting against front of thighs.',
    endPosition: 'Weights raised directly in front to shoulder height (parallel to floor).',
    movementPath: ['START: Thighs', 'RAISE: Smooth Front Lift', 'PARALLEL: Shoulder Height', 'LOWER: 2-Second Control'],
    keyCues: ['Lift strictly with front shoulders (no body swing)', 'Keep core tight and shoulders down', 'Stop at shoulder height (avoid lifting overhead)'],
    mistakes: ['Don\'t swing your torso or lean back', 'Don\'t shrug shoulders up toward ears', 'Don\'t drop the weights without resistance'],
    cameraTip: 'Place camera at chest height, 6–8 feet away in front or 45° angle.'
  },
  19: {
    summary: 'Shoulder sculpting exercise isolating the lateral deltoids to build shoulder width and posture.',
    steps: [
      'Stand upright with feet hip-width apart, holding weights at your sides.',
      'Maintain a slight forward torso lean and soft bend in your elbows.',
      'Raise arms out to the sides in a wide arc until parallel to the floor.',
      'Lower weights slowly under control back to your sides.'
    ],
    startPosition: 'Standing upright, arms at sides, elbows slightly unlocked.',
    endPosition: 'Arms extended out to sides at shoulder height in \'T\' shape.',
    movementPath: ['START: Sides', 'RAISE: Wide Lateral Arc', 'PARALLEL: \'T\' Shape', 'LOWER: Controlled Descent'],
    keyCues: ['Lead with your elbows as you lift outward', 'Keep shoulders depressed away from your ears', 'Control the lowering phase completely'],
    mistakes: ['Don\'t use momentum or bounce knees', 'Don\'t lift hands above shoulder height', 'Don\'t shrug your traps'],
    cameraTip: 'Place camera at chest height, 6–8 feet away in front view to capture full arm span.'
  },
  20: {
    summary: 'Arm isolation exercise strengthening all three heads of the triceps with full elbow extension.',
    steps: [
      'Stand tall or sit upright holding weight overhead with both hands.',
      'Tuck elbows in close to your ears, pointing forward.',
      'Lower weight behind your head by bending elbows until forearms touch biceps.',
      'Extend arms upward to drive weight back overhead.'
    ],
    startPosition: 'Arms fully extended overhead, elbows close to ears.',
    endPosition: 'Elbows bent at 90° behind head, triceps fully stretched.',
    movementPath: ['START: Overhead Lockout', 'LOWER: Bend Behind Head', 'STRETCH: Deep Extension', 'PRESS: Lockout Overhead'],
    keyCues: ['Keep elbows pinned pointing forward (don\'t flare out)', 'Full extension at the top with tricep squeeze', 'Keep core engaged to protect lower back'],
    mistakes: ['Don\'t flare elbows wide to the sides', 'Don\'t arch your lower back excessively', 'Don\'t move your upper arms back and forth'],
    cameraTip: 'Place camera at chest height, 6–8 feet away in front or profile view.'
  }
};

/**
 * State for Stage 2 (PREPARE) Calibration & Countdown
 */
let prepareCalibrationActive = false;
let isCalibrationReady = false;
let countdownTimer = null;

/**
 * Populates comprehensive Exercise Learning Guide (Stage 1: LEARN)
 */
function populateExerciseLearningGuide(ex) {
  if (!ex) return;

  const guide = EXERCISE_LEARNING_GUIDES[ex.id] || {
    summary: ex.description || 'Practice controlled repetitions with strict form and posture alignment.',
    steps: [
      'Set your base position with balanced posture and core braced.',
      'Initiate movement with steady cadence through primary joint action.',
      'Reach target range of motion at peak position.',
      'Lower under control to complete repetition.'
    ],
    startPosition: 'Balanced starting posture with neutral spine.',
    endPosition: 'Full target range of motion position.',
    movementPath: ['START: Setup', 'CONCENTRIC: Drive', 'PEAK: Hold', 'ECCENTRIC: Return'],
    keyCues: ['Maintain steady tempo', 'Keep core braced', 'Control full range of motion'],
    mistakes: ['Don\'t rush the movement', 'Don\'t compromise posture', 'Don\'t use excessive momentum'],
    cameraTip: 'Position camera at waist-to-chest height, 6–8 feet away in full view.'
  };

  // Header & Badges
  const titleEl = document.getElementById('setupExerciseName');
  if (titleEl) titleEl.innerText = ex.name;

  const descEl = document.getElementById('setupExerciseDesc');
  if (descEl) descEl.innerText = guide.summary;

  const diffEl = document.getElementById('setupDifficulty');
  if (diffEl) diffEl.innerText = ex.difficulty || 'Intermediate';

  const muscleEl = document.getElementById('setupMuscleGroup');
  if (muscleEl) muscleEl.innerText = getExerciseMuscleGroup(ex.name);

  // How to Perform (Steps)
  const stepsList = document.getElementById('learnStepsList');
  if (stepsList) {
    stepsList.innerHTML = guide.steps.map((step, idx) => `
      <div class="learn-step-item">
        <span class="step-num">${idx + 1}</span>
        <span class="step-text">${escapeHTML(step)}</span>
      </div>
    `).join('');
  }

  // Start & Finish Positions
  const startEl = document.getElementById('learnStartPosition');
  if (startEl) startEl.innerText = guide.startPosition;

  const endEl = document.getElementById('learnEndPosition');
  if (endEl) endEl.innerText = guide.endPosition;

  // Movement Path Track
  const pathTrack = document.getElementById('learnMovementPath');
  if (pathTrack) {
    pathTrack.innerHTML = guide.movementPath.map((node, idx) => `
      <span class="path-node">${escapeHTML(node)}</span>
      ${idx < guide.movementPath.length - 1 ? '<span class="path-arrow"><i class="fa-solid fa-arrow-right"></i></span>' : ''}
    `).join('');
  }

  // Key Cues
  const cuesList = document.getElementById('learnKeyCuesList');
  if (cuesList) {
    cuesList.innerHTML = guide.keyCues.map((cue) => `
      <li class="cue-item"><i class="fa-solid fa-check"></i> <span>${escapeHTML(cue)}</span></li>
    `).join('');
  }

  // Common Mistakes
  const mistakesList = document.getElementById('learnMistakesList');
  if (mistakesList) {
    mistakesList.innerHTML = guide.mistakes.map((mistake) => `
      <li class="mistake-item"><i class="fa-solid fa-xmark"></i> <span>${escapeHTML(mistake)}</span></li>
    `).join('');
  }

  // Camera Tip
  const tipEl = document.getElementById('learnCameraTip');
  if (tipEl) tipEl.innerText = guide.cameraTip;

  // Populate Workout Plan Prescription & AI Recommendation
  currentExercisePrescription = resolveExercisePrescription(ex);
  if (currentExercisePrescription) {
    const setsEl = document.getElementById('learnPrescriptionSets');
    const repsEl = document.getElementById('learnPrescriptionReps');
    const restEl = document.getElementById('learnPrescriptionRest');
    const tempoEl = document.getElementById('learnPrescriptionTempo');
    const recTextEl = document.getElementById('learnAiRecommendationText');

    if (setsEl) setsEl.innerText = currentExercisePrescription.sets;
    if (repsEl) repsEl.innerText = currentExercisePrescription.reps;
    if (restEl) restEl.innerText = `${currentExercisePrescription.restSeconds}s`;
    if (tempoEl) tempoEl.innerHTML = `<i class="fa-solid fa-stopwatch"></i> TEMPO ${currentExercisePrescription.tempo}`;
    if (recTextEl) recTextEl.innerText = currentExercisePrescription.recommendation;
  }
}

/**
 * Selects an exercise and transitions to Stage 1 (LEARN Screen)
 */
function selectExercise(exerciseId) {
  selectedExercise = allExercises.find((ex) => ex.id === exerciseId);
  if (!selectedExercise) return;

  // Reset single workout state
  activeSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  currentRepCount = 0;
  currentFormScore = 100.0;
  accumulatedFeedback = [];
  workoutElapsedSeconds = 0;
  prepareCalibrationActive = false;
  isCalibrationReady = false;

  activeWorkoutSetsState = {
    currentSetNumber: 1,
    targetSets: 3,
    targetReps: 10,
    restSeconds: 60,
    loggedSets: [],
    isSingleExerciseFlow: true,
    isSetCompleting: false
  };

  // Populate rich exercise learning breakdown (including sets, reps, rest & AI recommendation)
  populateExerciseLearningGuide(selectedExercise);

  // Clear previous AI coaching text
  const aiCoachEl = document.getElementById('resAICoaching');
  if (aiCoachEl) {
    aiCoachEl.innerHTML = 'Loading personalized AI coaching analysis...';
  }

  // Pre-load and start demo avatar in Learn view
  if (!learnDemoAvatarEngine && typeof DemoAvatarEngine === 'function') {
    initDemoAvatarEngine();
  }
  if (learnDemoAvatarEngine) {
    learnDemoAvatarEngine.loadExercise(selectedExercise.id);
    learnDemoAvatarEngine.start();
  }
  if (demoAvatarEngine) {
    demoAvatarEngine.loadExercise(selectedExercise.id);
  }

  goToStep('workoutSetupStep');
}

/**
 * Transitions from Stage 1 (LEARN) to Stage 2 (PREPARE / Calibration)
 */
async function goToPrepareStage() {
  if (!selectedExercise) return;

  prepareCalibrationActive = true;
  isCalibrationReady = false;

  // Update Prepare Stage Plan Indicator
  const planTextEl = document.getElementById('preparePlanText');
  if (planTextEl && currentExercisePrescription) {
    planTextEl.innerText = `Set 1 of ${currentExercisePrescription.sets} · ${currentExercisePrescription.reps} reps · ${currentExercisePrescription.restSeconds}s rest`;
  }

  // Reset prepare UI
  const icon = document.getElementById('prepareStatusIcon');
  const title = document.getElementById('prepareStatusTitle');
  const desc = document.getElementById('prepareStatusDesc');
  const frameInst = document.getElementById('prepareFramingInstruction');
  const startBtn = document.getElementById('prepareStartBtn');
  const overlay = document.getElementById('workoutCountdownOverlay');

  if (overlay) overlay.style.display = 'none';
  if (icon) icon.className = 'status-indicator-icon icon-calibrating';
  if (title) title.innerText = 'Checking Camera & Position...';
  if (desc) desc.innerText = 'Move into view so your upper body and joints are visible inside the frame.';
  if (frameInst) frameInst.innerText = 'Keep your body centered inside the frame';
  if (startBtn) {
    startBtn.disabled = false;
    startBtn.classList.remove('btn-pulse-ready');
  }

  goToStep('workoutPrepareStep');

  // Activate live camera feed for position calibration
  await startCameraStream();
}

/**
 * Transitions from Stage 2 (PREPARE) back to Stage 1 (LEARN)
 */
function backToLearnStage() {
  prepareCalibrationActive = false;
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
  const overlay = document.getElementById('workoutCountdownOverlay');
  if (overlay) overlay.style.display = 'none';

  stopCameraStream();
  goToStep('workoutSetupStep');
}

/**
 * Countdown Trigger: 3 -> 2 -> 1 -> GO -> Stage 3 (PERFORM)
 */
function startCountdownAndPerform() {
  const overlay = document.getElementById('workoutCountdownOverlay');
  const countNum = document.getElementById('countdownNumber');
  const startBtn = document.getElementById('prepareStartBtn');

  if (startBtn) startBtn.disabled = true;
  if (overlay) overlay.style.display = 'flex';

  let count = 3;
  if (countNum) countNum.innerText = count;

  if (countdownTimer) clearInterval(countdownTimer);

  countdownTimer = setInterval(() => {
    count--;
    if (count > 0) {
      if (countNum) {
        countNum.innerText = count;
        countNum.classList.remove('count-tick');
        void countNum.offsetWidth;
        countNum.classList.add('count-tick');
      }
    } else if (count === 0) {
      if (countNum) countNum.innerText = 'GO!';
    } else {
      clearInterval(countdownTimer);
      countdownTimer = null;
      if (overlay) overlay.style.display = 'none';
      if (startBtn) startBtn.disabled = false;
      prepareCalibrationActive = false;

      // Start active workout session (PERFORM stage)
      startWorkoutSession();
    }
  }, 650);
}

/**
 * Starts active workout session in Stage 3 (PERFORM)
 */
async function startWorkoutSession() {
  if (!selectedExercise) return;

  activeSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  currentRepCount = 0;
  currentFormScore = 100.0;
  accumulatedFeedback = [];
  prepareCalibrationActive = false;

  // Initialize Active Workout Sets State if starting single-exercise flow
  if (!activeStructuredSession) {
    const rx = currentExercisePrescription || resolveExercisePrescription(selectedExercise);
    activeWorkoutSetsState = {
      currentSetNumber: 1,
      targetSets: rx ? rx.sets : 3,
      targetReps: rx ? rx.reps : 10,
      restSeconds: rx ? rx.restSeconds : 60,
      loggedSets: [],
      isSingleExerciseFlow: true,
      isSetCompleting: false
    };
    window.currentStructuredSetTarget = activeWorkoutSetsState.targetReps;
  }

  const targetReps = activeStructuredSession 
    ? (window.currentStructuredSetTarget || 10) 
    : (activeWorkoutSetsState ? activeWorkoutSetsState.targetReps : 10);

  const exTitleEl = document.getElementById('activeExerciseTitle');
  if (exTitleEl) exTitleEl.innerText = selectedExercise.name;

  // Update HUD Set Badge
  const setPillEl = document.getElementById('hudSetProgress');
  if (setPillEl) {
    const currentSet = activeStructuredSession ? activeStructuredSession.currentSetNumber : activeWorkoutSetsState.currentSetNumber;
    const maxSets = activeStructuredSession ? activeStructuredSession.plan.exercises[activeStructuredSession.currentExIndex].target_sets : activeWorkoutSetsState.targetSets;
    setPillEl.innerText = `SET ${currentSet} / ${maxSets}`;
  }

  const repCountEl = document.getElementById('hudRepCount');
  if (repCountEl) repCountEl.innerText = '0';

  const repTargetEl = document.getElementById('hudRepTarget');
  if (repTargetEl) repTargetEl.innerText = `/ ${targetReps} REPS`;

  const repProgressEl = document.getElementById('hudRepProgressFill');
  if (repProgressEl) repProgressEl.style.width = '0%';

  const formScoreEl = document.getElementById('hudFormScore');
  if (formScoreEl) formScoreEl.innerText = 'Calibrating';

  const formPillEl = document.getElementById('hudFormScorePill');
  if (formPillEl) formPillEl.className = 'trainer-form-pill pill-neutral';

  const hudDurationEl = document.getElementById('hudDuration');
  if (hudDurationEl) hudDurationEl.innerText = '00:00';

  const feedbackContainer = document.getElementById('hudFeedback');
  if (feedbackContainer) feedbackContainer.innerText = 'Position yourself in camera view to begin.';

  // Clear result screen DOM elements
  document.getElementById('resRepCount').innerText = '--';
  document.getElementById('resDuration').innerText = '00:00';
  document.getElementById('resFormScore').innerText = 'N/A';
  document.getElementById('resAICoaching').innerHTML = 'Loading personalized AI coaching analysis...';
  const mqEl = document.getElementById('resMovementQuality');
  if (mqEl) mqEl.innerText = '--';
  const mmList = document.getElementById('movementMetricsList');
  if (mmList) mmList.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem; text-align: center; padding: 20px;">Computing movement profile...</div>';

  // Call start-session backend API
  try {
    await fetch(`${ML_API_BASE}/workouts/live/start-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: activeSessionId,
        exercise_choice: String(selectedExercise.id)
      })
    });
  } catch (e) {
    console.warn('[FitQuest Warning]: Live session start endpoint call failed:', e);
  }

  // Reset duration timer
  workoutElapsedSeconds = 0;
  workoutStartTime = Date.now();
  if (workoutTimerInterval) clearInterval(workoutTimerInterval);

  workoutTimerInterval = setInterval(() => {
    workoutElapsedSeconds = Math.floor((Date.now() - workoutStartTime) / 1000);
    const durEl = document.getElementById('hudDuration');
    if (durEl) durEl.innerText = formatDuration(workoutElapsedSeconds);
  }, 1000);

  goToStep('workoutActiveStep');

  // Default active workout to clean Camera Focus Mode
  switchWorkoutViewport('camera');

  // Start demo avatar animation for the exercise
  if (demoAvatarEngine && selectedExercise) {
    demoAvatarEngine.loadExercise(selectedExercise.id);
    demoAvatarEngine.start();
  }

  // Start Movement Copilot Engine
  if (typeof startCopilot === 'function' && selectedExercise) {
    startCopilot(activeSessionId, selectedExercise, {
      dnaLimiter: window.activeDnaLimiter || null,
      adaptiveTempo: window.activeAdaptiveTempo || null
    });
  }

  // Ensure webcam and live stream are running
  await startCameraStream();
}

/**
 * Initializes browser webcam feed and binds stream to viewport elements
 * Dynamically adjusts container aspect-ratio to match natural camera stream (zero crop / zero distortion)
 */
async function startCameraStream() {
  const video = document.getElementById('webcamFeed');
  const prepareVideo = document.getElementById('prepareWebcamFeed');
  const overlay = document.getElementById('overlayImage');
  const placeholder = document.getElementById('cameraPlaceholder');
  const notice = document.getElementById('cameraNoticeText');

  // If a synthetic video file is already loaded, stream it directly without requesting hardware webcam
  if (video && !video.srcObject && video.src) {
    if (overlay) overlay.style.display = 'block';
    if (placeholder) placeholder.style.display = 'none';
    video.style.display = 'block';
    if (video.paused) {
      video.play().catch(e => console.warn(e));
    }
    startFrameTransmission();
    return;
  }

  try {
    if (!webcamStream || !webcamStream.active) {
      // 1. Explicitly cap webcam resolution to 640x480 (480p) to eliminate resizing & memory bandwidth waste
      const constraints = {
        video: {
          width: { ideal: 640, max: 640 },
          height: { ideal: 480, max: 480 },
          facingMode: 'user',
          frameRate: { ideal: 30, max: 30 }
        },
        audio: false
      };
      webcamStream = await navigator.mediaDevices.getUserMedia(constraints);
    }

    const applyAspect = (vEl) => {
      if (!vEl || !vEl.videoWidth || !vEl.videoHeight) return;
      document.querySelectorAll('.camera-container').forEach(c => {
        c.style.aspectRatio = `${vEl.videoWidth} / ${vEl.videoHeight}`;
      });
    };

    if (video) {
      video.srcObject = webcamStream;
      video.style.display = 'block';
      video.onloadedmetadata = () => applyAspect(video);
    }
    if (prepareVideo) {
      prepareVideo.srcObject = webcamStream;
      prepareVideo.style.display = 'block';
      prepareVideo.onloadedmetadata = () => applyAspect(prepareVideo);
    }

    if (overlay) overlay.style.display = 'block';
    if (placeholder) placeholder.style.display = 'none';

    // Start frame streaming to backend
    startFrameTransmission();

  } catch (err) {
    console.warn('[FitQuest Camera Warning]: Webcam access denied or unavailable:', err);
    if (placeholder) placeholder.style.display = 'block';
    if (video) video.style.display = 'none';
    if (prepareVideo) prepareVideo.style.display = 'none';
    if (overlay) overlay.style.display = 'none';
    if (notice) {
      notice.innerHTML = `
        <span style="color: #ef4444;">
          <i class="fa-solid fa-triangle-exclamation"></i> Camera Access Denied / Unavailable.
        </span><br>
        Please allow webcam permissions in your browser. (Telemetry simulation mode active).
      `;
    }
  }
}

/**
 * Transmits video frames to backend CV Engine via HTTP / WebSocket
 * Features frame skipping (~15 FPS inference), concurrency throttling, and optimized canvas rendering
 */
function startFrameTransmission() {
  const video = document.getElementById('webcamFeed');
  const canvas = document.getElementById('frameCanvas');
  const overlay = document.getElementById('overlayImage');
  const ctx = canvas ? canvas.getContext('2d', { willReadFrequently: true }) : null;

  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
    animationFrameId = null;
  }
  if (frameCaptureInterval) {
    clearInterval(frameCaptureInterval);
    frameCaptureInterval = null;
  }

  frameCount = 0;
  isProcessingFrame = false;

  // Enable performance mode on demo avatar to lower canvas overhead during active workouts
  if (demoAvatarEngine && typeof demoAvatarEngine.setPerformanceMode === 'function') {
    demoAvatarEngine.setPerformanceMode(true);
  }

  // 2. Optimized video processing loop with frame skipping (process every 2nd frame ~15 FPS)
  function processVideoLoop() {
    const hasStream = webcamStream && webcamStream.active;
    const hasVideo = video && !video.paused && !video.ended && (video.srcObject || video.src);
    if (!hasStream && !hasVideo) return;

    frameCount++;

    // Run inference only on even frames (cutting compute and network load in half)
    if (frameCount % FRAME_SKIP_RATIO === 0) {
      if (!isProcessingFrame && video && !video.paused && !video.ended && video.videoWidth) {
        runYoloInference(video, canvas, ctx, overlay);
      }
    }

    animationFrameId = requestAnimationFrame(processVideoLoop);
  }

  animationFrameId = requestAnimationFrame(processVideoLoop);
}

/**
 * Loads a local video file (MP4, WebM, MOV) as a synthetic camera feed
 * Allows seamless testing on desktop machines that do not have physical webcams
 */
function handleWorkoutVideoUpload(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  const video = document.getElementById('webcamFeed');
  const overlay = document.getElementById('overlayImage');
  const placeholder = document.getElementById('cameraPlaceholder');

  // Stop any active hardware webcam stream
  if (webcamStream) {
    webcamStream.getTracks().forEach((track) => {
      try { track.stop(); } catch (e) {}
    });
    webcamStream = null;
  }

  video.srcObject = null;
  video.src = URL.createObjectURL(file);
  video.loop = true;
  video.muted = true;
  video.style.display = 'block';
  if (overlay) overlay.style.display = 'block';
  if (placeholder) placeholder.style.display = 'none';

  video.onloadeddata = () => {
    video.play().then(() => {
      startFrameTransmission();
    }).catch(e => console.warn('[FitQuest Video Autoplay Warning]:', e));
  };
}
window.handleWorkoutVideoUpload = handleWorkoutVideoUpload;

/**
 * Executes a single throttled YOLO pose estimation inference call
 * Guarded against overlapping requests and optimized to eliminate canvas GC pressure
 */
async function runYoloInference(video, canvas, ctx, overlay) {
  if (isProcessingFrame) return; // Concurrency guard: never pile up requests if backend takes > frame interval
  isProcessingFrame = true;

  try {
    const targetW = 640;
    const targetH = 480;

    // 3. Canvas size optimization: only resize if dimensions changed to eliminate GC pressure
    if (canvas.width !== targetW || canvas.height !== targetH) {
      canvas.width = targetW;
      canvas.height = targetH;
    }

    // Turn off expensive shadow/blur effects on canvas context during active workouts
    ctx.shadowBlur = 0;
    ctx.shadowColor = 'transparent';
    ctx.drawImage(video, 0, 0, targetW, targetH);

    const base64Frame = canvas.toDataURL('image/jpeg', 0.55);

    const payload = {
      session_id: activeSessionId,
      exercise_choice: String(selectedExercise.id),
      frame_data: base64Frame,
      include_annotated_image: true
    };

    const liveMlBase = typeof ML_API_BASE !== 'undefined' ? ML_API_BASE : (typeof API_BASE !== 'undefined' ? API_BASE : 'http://127.0.0.1:8000/api/v1');

    const res = await fetch(`${liveMlBase}/workouts/live/process-frame`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) return;

    const telemetry = await res.json();
    updateHUDTelemetry(telemetry, overlay);

  } catch (err) {
    console.error('[FitQuest Frame Processing Error]:', err);
  } finally {
    isProcessingFrame = false;
  }
}

/**
 * Updates Live Workout HUD with authoritative CV Engine telemetry
 * Formatted cleanly like a Personal Trainer ("Show the Action, Not the Algorithm")
 */
// Feedback Stabilization State (prevents rapid per-frame UI flicker)
let activeFeedbackCode = 'GOOD_FORM';
let activeFeedbackDetail = 'Position yourself in front of camera.';
let activeFeedbackPriority = 7;
let lastFeedbackUpdateTime = 0;
const FEEDBACK_HOLD_MS = 450;

function formatTrainerCue(code, rawDetail) {
  const codeMap = {
    'LANDMARKS_MISSING': 'Step back so your full body is visible.',
    'ELBOW_FLARING': 'Keep your elbows closer to your sides.',
    'KNEE_VALGUS': 'Keep knees pushed outward inline with toes.',
    'INSUFFICIENT_DEPTH': 'Go slightly deeper on the descent.',
    'BACK_ROUNDING': 'Keep your chest proud and spine neutral.',
    'FAST_TEMPO': 'Move a little slower for maximum control.',
    'ASYMMETRICAL_MOVEMENT': 'Drive evenly through both sides.',
    'UNEVEN_EXT': 'Extend both arms fully and symmetrically.',
    'TRUNK_LEAN': 'Keep your torso upright and core engaged.',
    'FORWARD_LEAN': 'Keep weight balanced through your midfoot.',
    'KNEE_CAVE': 'Push your knees out as you stand.',
    'GOOD_FORM': 'Great form · Keep going ✓'
  };

  if (codeMap[code]) return codeMap[code];
  if (rawDetail && typeof rawDetail === 'string' && rawDetail.trim().length > 0) {
    return rawDetail.replace(/^(error|warning|issue|alert):\s*/i, '').trim();
  }
  return 'Maintain steady cadence and control.';
}

function updateHUDTelemetry(telemetry, overlayElement) {
  if (!telemetry || telemetry.status === 'error') return;

  // 0. PREPARE STAGE CALIBRATION & FRAMING GUIDANCE
  if (prepareCalibrationActive) {
    const icon = document.getElementById('prepareStatusIcon');
    const title = document.getElementById('prepareStatusTitle');
    const desc = document.getElementById('prepareStatusDesc');
    const frameInst = document.getElementById('prepareFramingInstruction');
    const startBtn = document.getElementById('prepareStartBtn');

    if (telemetry.feedback_code === 'LANDMARKS_MISSING') {
      if (icon) icon.className = 'status-indicator-icon icon-calibrating';
      if (title) title.innerText = 'Move into Camera View';
      if (desc) desc.innerText = 'Step back so your upper body and active joints are clearly visible inside the frame.';
      if (frameInst) frameInst.innerText = 'Step back so your body fits inside the frame';
      if (startBtn) startBtn.classList.remove('btn-pulse-ready');
    } else {
      isCalibrationReady = true;
      if (icon) icon.className = 'status-indicator-icon icon-ready';
      if (title) title.innerText = '✓ Body Detected · In Position!';
      if (desc) desc.innerText = 'You are in optimal position. Click Start Workout when you are ready to begin.';
      if (frameInst) frameInst.innerText = '✓ Perfect position! Ready to start.';
      if (startBtn) startBtn.classList.add('btn-pulse-ready');
    }
  }

  const targetReps = activeStructuredSession 
    ? (window.currentStructuredSetTarget || 10) 
    : (activeWorkoutSetsState ? activeWorkoutSetsState.targetReps : 10);

  // 1. HERO REPETITIONS & PROGRESS
  if (telemetry.rep_count !== undefined) {
    const prevRep = currentRepCount;
    currentRepCount = telemetry.rep_count;

    const repCountEl = document.getElementById('hudRepCount');
    if (repCountEl) {
      repCountEl.innerText = currentRepCount;
      if (currentRepCount > prevRep) {
        // Trigger celebratory rep pulse animation
        const repDisplay = document.getElementById('heroRepDisplay');
        if (repDisplay) {
          repDisplay.classList.add('rep-bump-pulse');
          setTimeout(() => repDisplay.classList.remove('rep-bump-pulse'), 600);
        }
      }
    }

    const progressFill = document.getElementById('hudRepProgressFill');
    if (progressFill) {
      const pct = Math.min(100, Math.round((currentRepCount / Math.max(1, targetReps)) * 100));
      progressFill.style.width = `${pct}%`;
    }

    // Auto trigger set completion when target reps reached in single-exercise workout
    if (!activeStructuredSession && activeWorkoutSetsState && activeWorkoutSetsState.isSingleExerciseFlow && !activeWorkoutSetsState.isSetCompleting) {
      if (currentRepCount >= targetReps && targetReps > 0) {
        activeWorkoutSetsState.isSetCompleting = true;
        setTimeout(() => {
          handleSingleExerciseSetComplete();
        }, 450);
      }
    }
  }

  // 2. FORM QUALITY PILL (Concise & Unobtrusive)
  if (telemetry.form_score !== undefined) {
    currentFormScore = telemetry.form_score;
    const formScoreEl = document.getElementById('hudFormScore');
    const formPillEl = document.getElementById('hudFormScorePill');

    if (formScoreEl && formPillEl) {
      if (currentRepCount === 0 || currentFormScore === 0.0) {
        formScoreEl.innerText = 'Calibrating';
        formPillEl.className = 'trainer-form-pill pill-neutral';
      } else {
        const score = Math.round(currentFormScore);
        formScoreEl.innerText = `${score}% Form`;
        if (score >= 85) {
          formPillEl.className = 'trainer-form-pill pill-good';
        } else if (score >= 70) {
          formPillEl.className = 'trainer-form-pill pill-warn';
        } else {
          formPillEl.className = 'trainer-form-pill pill-alert';
        }
      }
    }
  }

  // 3. STABILIZED CONTEXTUAL PERSONAL TRAINER COACHING
  const now = Date.now();
  const newCode = telemetry.feedback_code || 'GOOD_FORM';
  const newDetail = telemetry.feedback_detail || (telemetry.feedback && telemetry.feedback.length > 0 ? telemetry.feedback[0] : 'Good Form');
  const newPriority = telemetry.feedback_priority !== undefined ? telemetry.feedback_priority : 7;

  if (newPriority < activeFeedbackPriority || (now - lastFeedbackUpdateTime) >= FEEDBACK_HOLD_MS) {
    activeFeedbackCode = newCode;
    activeFeedbackDetail = newDetail;
    activeFeedbackPriority = newPriority;
    lastFeedbackUpdateTime = now;
  }

  const feedbackContainer = document.getElementById('hudFeedback');
  const coachIcon = document.getElementById('trainerCoachIcon');
  const coachBanner = document.getElementById('trainerCoachingBanner');

  if (feedbackContainer) {
    const trainerMessage = formatTrainerCue(activeFeedbackCode, activeFeedbackDetail);
    feedbackContainer.innerText = trainerMessage;

    if (coachBanner && coachIcon) {
      if (!telemetry.valid || activeFeedbackCode === 'LANDMARKS_MISSING') {
        coachBanner.className = 'trainer-coaching-banner banner-guidance';
        coachIcon.innerHTML = '<i class="fa-solid fa-person-circle-question"></i>';
      } else if (activeFeedbackCode === 'GOOD_FORM') {
        coachBanner.className = 'trainer-coaching-banner banner-good';
        coachIcon.innerHTML = '<i class="fa-solid fa-circle-check"></i>';
      } else {
        coachBanner.className = 'trainer-coaching-banner banner-warn';
        coachIcon.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i>';
      }
    }
  }

  if (telemetry.feedback && telemetry.feedback.length > 0) {
    const feedbackStr = telemetry.feedback.join(' | ');
    if (!accumulatedFeedback.includes(feedbackStr)) {
      accumulatedFeedback.push(feedbackStr);
    }
  }

  if (telemetry.annotated_frame && overlayElement) {
    overlayElement.src = telemetry.annotated_frame;
    overlayElement.style.display = 'block';
  }

  // Feed real-time telemetry into Movement Copilot (Phase 5)
  if (typeof processCopilotTelemetry === 'function') {
    processCopilotTelemetry(telemetry);
  }
}


/**
 * Stops camera stream cleanly and releases webcam hardware
 */
function stopCameraStream() {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
    animationFrameId = null;
  }
  if (frameCaptureInterval) {
    clearInterval(frameCaptureInterval);
    frameCaptureInterval = null;
  }
  isProcessingFrame = false;
  frameCount = 0;

  // Restore demo avatar glow when camera/workout is idle
  if (demoAvatarEngine && typeof demoAvatarEngine.setPerformanceMode === 'function') {
    demoAvatarEngine.setPerformanceMode(false);
  }

  if (webcamStream) {
    webcamStream.getTracks().forEach((track) => {
      try {
        track.stop();
      } catch (e) {}
    });
    webcamStream = null;
  }

  const video = document.getElementById('webcamFeed');
  const prepareVideo = document.getElementById('prepareWebcamFeed');
  const overlay = document.getElementById('overlayImage');
  const placeholder = document.getElementById('cameraPlaceholder');

  if (video) {
    video.srcObject = null;
    video.style.display = 'none';
  }
  if (prepareVideo) {
    prepareVideo.srcObject = null;
    prepareVideo.style.display = 'none';
  }
  if (overlay) overlay.style.display = 'none';
  if (placeholder) placeholder.style.display = 'block';
}

/**
 * Ends active workout session, stops camera, and posts session to backend
 */
async function endWorkoutSession() {
  if (workoutTimerInterval) clearInterval(workoutTimerInterval);

  // Stop camera & frame capture
  stopCameraStream();

  // Stop Movement Copilot (Phase 5)
  if (typeof stopCopilot === 'function') {
    stopCopilot();
  }

  // Pause demo avatar animation
  if (demoAvatarEngine) {
    demoAvatarEngine.pause();
  }

  let movementData = null;

  // Call stop-session backend API to retrieve final CV summary & movement intelligence
  try {
    const stopRes = await fetch(`${ML_API_BASE}/workouts/live/stop-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: activeSessionId })
    });
    if (stopRes.ok) {
      const stopSummary = await stopRes.json();
      if (stopSummary && stopSummary.status === 'success') {
        currentRepCount = stopSummary.total_reps;
        currentFormScore = stopSummary.total_reps === 0 ? 0.0 : stopSummary.form_score;
        if (stopSummary.duration_sec !== undefined) {
          workoutElapsedSeconds = stopSummary.duration_sec;
        }
        if (stopSummary.movement_intelligence) {
          movementData = stopSummary.movement_intelligence;
        }
      }
    }
  } catch (e) {
    console.warn('[FitQuest Warning]: Live session stop endpoint call failed:', e);
  }

  // Handle multi-set aggregation if single-exercise multi-set workout was performed
  if (activeWorkoutSetsState && activeWorkoutSetsState.isSingleExerciseFlow && activeWorkoutSetsState.loggedSets && activeWorkoutSetsState.loggedSets.length > 0) {
    if (currentRepCount > 0 && !activeWorkoutSetsState.isSetCompleting) {
      activeWorkoutSetsState.loggedSets.push({
        setNumber: activeWorkoutSetsState.currentSetNumber,
        actualReps: currentRepCount,
        targetReps: activeWorkoutSetsState.targetReps,
        formScore: currentRepCount === 0 ? 0.0 : currentFormScore,
        durationSec: workoutElapsedSeconds,
        feedback: [...accumulatedFeedback]
      });
    }

    const totalRepsCompleted = activeWorkoutSetsState.loggedSets.reduce((sum, s) => sum + (s.actualReps || 0), 0);
    const totalTargetReps = activeWorkoutSetsState.loggedSets.length * activeWorkoutSetsState.targetReps;
    const totalSetsCompleted = activeWorkoutSetsState.loggedSets.length;
    const totalDurationSec = activeWorkoutSetsState.loggedSets.reduce((sum, s) => sum + (s.durationSec || 0), 0);
    const validScores = activeWorkoutSetsState.loggedSets.map(s => s.formScore).filter(s => s > 0);
    const avgFormScore = validScores.length > 0 ? (validScores.reduce((a, b) => a + b, 0) / validScores.length) : currentFormScore;

    currentRepCount = totalRepsCompleted;
    currentFormScore = avgFormScore;
    workoutElapsedSeconds = totalDurationSec;

    // Show workout plan summary in review stage
    const summaryCard = document.getElementById('workoutPlanSummaryCard');
    const setsSumEl = document.getElementById('resSetsSummary');
    const repsSumEl = document.getElementById('resTargetRepsSummary');
    const restSumEl = document.getElementById('resRestSummary');

    if (summaryCard) {
      summaryCard.style.display = 'flex';
      if (setsSumEl) setsSumEl.innerText = `${totalSetsCompleted} / ${activeWorkoutSetsState.targetSets} SETS`;
      if (repsSumEl) repsSumEl.innerText = `${totalRepsCompleted} / ${totalTargetReps} TARGET REPS`;
      if (restSumEl) restSumEl.innerText = 'RESTED AS PLANNED';
    }
  } else {
    const summaryCard = document.getElementById('workoutPlanSummaryCard');
    if (summaryCard) summaryCard.style.display = 'none';
  }

  // Transition to results step
  goToStep('workoutResultStep');
  const isInitialZero = (currentRepCount === 0);
  document.getElementById('resRepCount').innerText = currentRepCount;
  document.getElementById('resDuration').innerText = formatDuration(workoutElapsedSeconds);
  document.getElementById('resFormScore').innerText = isInitialZero ? 'N/A (No Reps)' : `${currentFormScore.toFixed(1)}%`;

  // Render Movement Intelligence & Fingerprint visualization
  renderMovementIntelligence(movementData || {
    exercise_id: selectedExercise ? selectedExercise.id : 1,
    exercise_name: selectedExercise ? selectedExercise.name : 'Exercise',
    total_reps: currentRepCount,
    duration_sec: workoutElapsedSeconds,
    form_score: currentFormScore,
    movement_signature: {
      rom_score: currentRepCount === 0 ? 0 : Math.round(currentFormScore * 0.9),
      stability_score: currentRepCount === 0 ? 0 : 80,
      tempo_score: currentRepCount === 0 ? 0 : 82,
      consistency_score: currentRepCount === 0 ? 0 : 85,
      symmetry_score: currentRepCount === 0 ? 0 : 78,
      movement_quality_score: currentRepCount === 0 ? 0 : Math.round(currentFormScore * 0.88)
    },
    metrics_summary: [
      { key: 'rom', label: 'Range of Motion', score: currentRepCount === 0 ? 0 : Math.round(currentFormScore * 0.9), available: currentRepCount > 0 },
      { key: 'stability', label: 'Movement Stability', score: currentRepCount === 0 ? 0 : 80, available: currentRepCount > 0 },
      { key: 'tempo', label: 'Tempo Control', score: currentRepCount === 0 ? 0 : 82, available: currentRepCount > 0 },
      { key: 'consistency', label: 'Consistency', score: currentRepCount === 0 ? 0 : 85, available: currentRepCount > 0 },
      { key: 'symmetry', label: 'Symmetry', score: currentRepCount === 0 ? 0 : 78, available: currentRepCount > 0 }
    ]
  });
  
  const zeroRepMessage = "No valid repetitions were detected in this session, so there isn't enough workout data to generate performance insights. Complete an exercise and try again.";

  if (isInitialZero) {
    document.getElementById('resAICoaching').innerHTML = formatMarkdownText(zeroRepMessage);
  } else {
    document.getElementById('resAICoaching').innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Generating personalized AI coaching feedback...`;
  }

  try {
    const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
    const userId = typeof getAuthenticatedUserId === 'function' ? getAuthenticatedUserId() : null;
    const exerciseId = (selectedExercise && selectedExercise.id) ? selectedExercise.id : 1;
    const exerciseName = (selectedExercise && selectedExercise.name) ? selectedExercise.name : 'Exercise';

    if (!token || !userId) {
      console.warn('[FitQuest Auth]: Unauthenticated session save attempt.');
      if (typeof showUnauthenticatedState === 'function') {
        showUnauthenticatedState();
      }
      return;
    }

    // Post completed workout telemetry payload to POST /api/v1/workouts
    const payload = {
      session_data: {
        user_id: userId,
        exercise_id: exerciseId,
        repetitions: currentRepCount,
        duration_sec: workoutElapsedSeconds,
        form_score: currentRepCount === 0 ? 0.0 : currentFormScore
      },
      form_scores_history: currentRepCount > 0 ? Array(currentRepCount).fill(1) : [],
      feedback_events: accumulatedFeedback.length > 0 ? accumulatedFeedback : (currentRepCount === 0 ? ["No valid repetitions detected"] : [`Completed set for ${exerciseName}`]),
      movement_intelligence: movementData
    };

    const response = await fetch(`${API_BASE}/workouts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Server status ${response.status}`);
    }

    const resultData = await response.json();

    const isFinalZero = (resultData.repetitions === 0 || currentRepCount === 0);

    // Render returned results & AI coaching insights
    document.getElementById('resRepCount').innerText = resultData.repetitions;
    document.getElementById('resDuration').innerText = formatDuration(resultData.duration_sec);
    document.getElementById('resFormScore').innerText = isFinalZero ? 'N/A (No Reps)' : `${resultData.form_score}%`;

    const aiText = isFinalZero
      ? zeroRepMessage
      : (resultData.ai_coaching_logs && resultData.ai_coaching_logs.length > 0 
          ? resultData.ai_coaching_logs[0].response 
          : "Great workout set!");

    document.getElementById('resAICoaching').innerHTML = formatMarkdownText(aiText);

    // Fetch and render historical movement comparison if valid reps completed
    const compCard = document.getElementById('historyComparisonCard');
    if (!isFinalZero && compCard && movementData && movementData.movement_signature) {
      try {
        const qScore = movementData.movement_signature.movement_quality_score || (currentFormScore * 0.88);
        const compRes = await fetch(`${API_BASE}/workouts/movement-intelligence/comparison?exercise_id=${exerciseId}&quality_score=${qScore}&session_id=${resultData.id}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json'
          }
        });
        if (compRes.ok) {
          const compData = await compRes.json();
          compCard.style.display = 'block';
          document.getElementById('resCompThisSession').innerText = `${compData.this_session}`;
          document.getElementById('resCompPrevAvg').innerText = `${compData.previous_avg}`;
          document.getElementById('resCompChange').innerText = `${compData.change >= 0 ? '+' : ''}${compData.change}`;
          
          const trendBadge = document.getElementById('resComparisonTrendBadge');
          if (trendBadge) {
            trendBadge.className = `comparison-trend-badge trend-${compData.trend}`;
            let tIcon = '<i class="fa-solid fa-minus"></i>';
            if (compData.trend === 'improving') tIcon = '<i class="fa-solid fa-arrow-trend-up"></i>';
            else if (compData.trend === 'declining') tIcon = '<i class="fa-solid fa-arrow-trend-down"></i>';
            trendBadge.innerHTML = `${tIcon} ${compData.trend.toUpperCase()}`;
          }

          const msgEl = document.getElementById('resComparisonMessage');
          if (msgEl) msgEl.innerText = compData.message;
        }
      } catch (compErr) {
        console.warn('[FitQuest Warning]: Failed to fetch history comparison:', compErr);
      }
    } else if (compCard) {
      compCard.style.display = 'none';
    }

    // Fetch and render Movement DNA Impact Card (Phase 4)
    const dnaImpactCard = document.getElementById('resMovementDnaCard');
    if (!isFinalZero && dnaImpactCard) {
      try {
        const dnaRes = await fetch(`${API_BASE}/movement-intelligence/dna?exercise_id=${exerciseId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json'
          }
        });
        if (dnaRes.ok) {
          const dnaData = await dnaRes.json();
          dnaImpactCard.style.display = 'flex';
          const qScore = (movementData && movementData.movement_signature && movementData.movement_signature.movement_quality_score) || (currentFormScore * 0.88);
          
          const qEl = document.getElementById('resDnaSessionQuality');
          if (qEl) qEl.innerText = qScore.toFixed(1);

          const chgEl = document.getElementById('resDnaChangeVal');
          if (chgEl && dnaData.trend) {
            const sign = dnaData.trend.delta >= 0 ? '+' : '';
            chgEl.innerText = `${sign}${dnaData.trend.pct_change.toFixed(1)}%`;
          }

          const strEl = document.getElementById('resDnaStrongestVal');
          if (strEl && dnaData.strongest_dimension) {
            strEl.innerText = dnaData.strongest_dimension.label;
          }

          const limEl = document.getElementById('resDnaLimiterVal');
          if (limEl && dnaData.primary_limiter) {
            limEl.innerText = dnaData.primary_limiter.label;
          }

          const msgEl = document.getElementById('resDnaImpactMsg');
          if (msgEl && dnaData.ai_report) {
            msgEl.innerText = dnaData.ai_report.what_changed;
          }
        }
      } catch (dnaErr) {
        console.warn('[FitQuest DNA Warning]: Failed to fetch Movement DNA impact:', dnaErr);
      }
    } else if (dnaImpactCard) {
      dnaImpactCard.style.display = 'none';
    }

    // Fetch and render Movement Copilot Session Intelligence Summary (Phase 5)
    if (typeof loadPostWorkoutCopilotSummary === 'function' && activeSessionId) {
      loadPostWorkoutCopilotSummary(activeSessionId);
    }

    // Refresh gamification streaks & achievements for valid workouts (reps >= 1)
    if (currentRepCount >= 1 && typeof loadGamificationData === 'function') {
      loadGamificationData();
      if (typeof showGamificationNotification === 'function') {
        showGamificationNotification('🔥 Workout Saved!', 'Your workout set was recorded towards your streak!', 'fa-fire');
      }
    }

  } catch (error) {
    console.error('[FitQuest Error]: Failed to record session to backend:', error);
    if (currentRepCount === 0) {
      document.getElementById('resAICoaching').innerHTML = formatMarkdownText(zeroRepMessage);
    } else {
      document.getElementById('resAICoaching').innerHTML = `
        <div style="color: #ef4444;">
          <i class="fa-solid fa-triangle-exclamation"></i> Session recorded locally. (Backend server error).
        </div>
      `;
    }
  }
}

/**
 * Renders the Movement Intelligence section including Canvas Radar Movement Fingerprint
 * and Movement Profile telemetry breakdown bars.
 */
function renderMovementIntelligence(data) {
  const container = document.getElementById('movementIntelligenceSection');
  if (!container) return;

  const qualityEl = document.getElementById('resMovementQuality');
  const metricsListEl = document.getElementById('movementMetricsList');
  const footnoteEl = document.getElementById('movementFootnoteText');
  const canvas = document.getElementById('movementFingerprintCanvas');

  if (!data || !data.movement_signature) {
    if (qualityEl) qualityEl.innerText = currentRepCount === 0 ? '0' : '--';
    if (metricsListEl) {
      metricsListEl.innerHTML = `
        <div style="color: var(--text-muted); font-size: 0.8rem; text-align: center; padding: 16px;">
          ${currentRepCount === 0 ? 'Complete at least 1 rep to generate a Movement Fingerprint.' : 'Biomechanical telemetry processing...'}
        </div>
      `;
    }
    drawMovementFingerprintRadar(canvas, null);
    return;
  }

  const sig = data.movement_signature;
  const isZero = data.total_reps === 0;

  // 1. Overall Quality Score
  if (qualityEl) {
    qualityEl.innerText = isZero ? '0' : sig.movement_quality_score;
    const badge = document.getElementById('movementQualityBadge');
    if (badge) {
      if (sig.movement_quality_score >= 80) {
        badge.style.borderColor = 'rgba(16, 185, 129, 0.4)';
      } else if (sig.movement_quality_score >= 60) {
        badge.style.borderColor = 'rgba(0, 242, 254, 0.4)';
      } else {
        badge.style.borderColor = 'rgba(245, 158, 11, 0.4)';
      }
    }
  }

  // 2. Metrics Progress Bars List
  if (metricsListEl && data.metrics_summary) {
    metricsListEl.innerHTML = data.metrics_summary.map((m) => {
      const isAvail = m.available && !isZero;
      const scoreVal = isAvail ? `${m.score}%` : (m.score === null ? 'N/A (Single-axis)' : '0%');
      const widthVal = isAvail ? `${Math.max(4, Math.min(100, m.score))}%` : '0%';
      
      let fillClass = '';
      if (m.key === 'tempo') fillClass = 'fill-purple';
      else if (m.key === 'consistency') fillClass = 'fill-orange';

      let icon = 'fa-gauge';
      if (m.key === 'rom') icon = 'fa-arrows-up-down';
      else if (m.key === 'stability') icon = 'fa-crosshairs';
      else if (m.key === 'tempo') icon = 'fa-stopwatch';
      else if (m.key === 'consistency') icon = 'fa-wave-square';
      else if (m.key === 'symmetry') icon = 'fa-scale-balanced';

      return `
        <div class="metric-bar-row">
          <div class="metric-header">
            <span class="metric-name">
              <i class="fa-solid ${icon}" style="font-size: 0.75rem; color: var(--accent-cyan);"></i>
              ${escapeHTML(m.label)}
            </span>
            <span class="metric-score-val ${!isAvail ? 'unavail' : ''}">${scoreVal}</span>
          </div>
          <div class="metric-track">
            <div class="metric-fill ${fillClass}" style="width: ${widthVal};"></div>
          </div>
        </div>
      `;
    }).join('');
  }

  // 3. Update Biomechanical Footnote
  if (footnoteEl && data.movement_features) {
    const feat = data.movement_features;
    let detailParts = [];
    if (feat.range_of_motion && feat.range_of_motion.average_rom_deg !== undefined) {
      detailParts.push(`ROM: ${feat.range_of_motion.average_rom_deg}°`);
    }
    if (feat.tempo && feat.tempo.average_rep_duration_sec > 0) {
      detailParts.push(`Pacing: ${feat.tempo.average_rep_duration_sec}s/rep`);
    }
    if (feat.symmetry && feat.symmetry.mean_disparity_deg !== undefined) {
      detailParts.push(`Disparity: ${feat.symmetry.mean_disparity_deg}°`);
    }

    if (detailParts.length > 0) {
      footnoteEl.innerHTML = `<i class="fa-solid fa-circle-info"></i> ${detailParts.join(' • ')} (${escapeHTML(data.exercise_name || 'Biometrics')})`;
    }
  }

  // 4. Render Canvas Radar Chart
  drawMovementFingerprintRadar(canvas, isZero ? null : data);
}

/**
 * Draws the custom 5-axis or 4-axis Movement Fingerprint Radar on HTML5 Canvas
 */
function drawMovementFingerprintRadar(canvas, data) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const w = 280;
  const h = 280;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = `${w}px`;
  canvas.style.height = `${h}px`;
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, w, h);

  const cx = w / 2;
  const cy = h / 2;
  const maxRadius = 90;

  // Determine axes
  let axes = [
    { key: 'rom_score', label: 'ROM' },
    { key: 'stability_score', label: 'STABILITY' },
    { key: 'tempo_score', label: 'TEMPO' },
    { key: 'consistency_score', label: 'CONSIST' }
  ];

  if (data && data.movement_signature && data.movement_signature.symmetry_score !== null) {
    axes.push({ key: 'symmetry_score', label: 'SYMMETRY' });
  }

  const numAxes = axes.length;
  const angleStep = (Math.PI * 2) / numAxes;
  const startAngle = -Math.PI / 2; // Top vertex

  // Draw concentric radar web rings (20%, 40%, 60%, 80%, 100%)
  const rings = [0.2, 0.4, 0.6, 0.8, 1.0];
  rings.forEach((rRatio) => {
    const ringRadius = maxRadius * rRatio;
    ctx.beginPath();
    for (let i = 0; i < numAxes; i++) {
      const angle = startAngle + i * angleStep;
      const x = cx + ringRadius * Math.cos(angle);
      const y = cy + ringRadius * Math.sin(angle);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = rRatio === 1.0 ? 'rgba(0, 242, 254, 0.22)' : 'rgba(255, 255, 255, 0.07)';
    ctx.lineWidth = 1;
    ctx.stroke();
  });

  // Draw spoke axes and labels
  axes.forEach((axis, i) => {
    const angle = startAngle + i * angleStep;
    const x = cx + maxRadius * Math.cos(angle);
    const y = cy + maxRadius * Math.sin(angle);

    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(x, y);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Axis Labels
    const labelDistance = maxRadius + 22;
    const lx = cx + labelDistance * Math.cos(angle);
    const ly = cy + labelDistance * Math.sin(angle);

    ctx.font = '700 9px "Outfit", "Inter", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
    ctx.fillText(axis.label, lx, ly);
  });

  if (!data || !data.movement_signature || data.total_reps === 0) {
    // Render inactive empty state polygon (baseline center dot)
    ctx.beginPath();
    ctx.arc(cx, cy, 6, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.fill();
    return;
  }

  // Calculate polygon vertex coordinates from scores
  const sig = data.movement_signature;
  const polyPoints = axes.map((axis, i) => {
    const score = Math.max(8, Math.min(100, sig[axis.key] || 0));
    const pointRadius = maxRadius * (score / 100);
    const angle = startAngle + i * angleStep;
    return {
      x: cx + pointRadius * Math.cos(angle),
      y: cy + pointRadius * Math.sin(angle),
      score: sig[axis.key] || 0
    };
  });

  // Draw Fingerprint Neon Polygon Fill & Stroke
  ctx.beginPath();
  polyPoints.forEach((pt, i) => {
    if (i === 0) ctx.moveTo(pt.x, pt.y);
    else ctx.lineTo(pt.x, pt.y);
  });
  ctx.closePath();

  // Glassmorphic Gradient Fill
  const grad = ctx.createRadialGradient(cx, cy, 10, cx, cy, maxRadius);
  grad.addColorStop(0, 'rgba(0, 242, 254, 0.35)');
  grad.addColorStop(0.7, 'rgba(16, 185, 129, 0.22)');
  grad.addColorStop(1, 'rgba(0, 242, 254, 0.08)');
  ctx.fillStyle = grad;
  ctx.fill();

  ctx.strokeStyle = '#00f2fe';
  ctx.lineWidth = 2.5;
  ctx.shadowColor = 'rgba(0, 242, 254, 0.8)';
  ctx.shadowBlur = 10;
  ctx.stroke();
  ctx.shadowBlur = 0; // reset

  // Draw Glowing Vertices
  polyPoints.forEach((pt) => {
    ctx.beginPath();
    ctx.arc(pt.x, pt.y, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();

    ctx.beginPath();
    ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#10b981';
    ctx.fill();
  });
}

/**
 * Fetches and renders historical workouts from GET /api/v1/workouts/user/{userId}
 */
async function loadWorkoutHistory() {
  const container = document.getElementById('historyList');
  if (!container) return;

  try {
    const userId = typeof getAuthenticatedUserId === 'function' ? getAuthenticatedUserId() : null;
    const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');

    if (!userId || !token) {
      container.innerHTML = `<div class="loading-spinner">Please log in to view your workout history.</div>`;
      return;
    }

    const response = await fetch(`${API_BASE}/workouts/user/${userId}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}`);
    }

    const historyData = await response.json();

    if (historyData.length === 0) {
      container.innerHTML = `<div class="loading-spinner">No workout history recorded yet. Complete a workout session to see your stats here!</div>`;
      return;
    }

    container.innerHTML = historyData.map((item) => `
      <div class="history-card">
        <div class="history-info">
          <h3>${escapeHTML(item.exercise ? item.exercise.name : 'Exercise Session')}</h3>
          <div class="history-meta">
            <i class="fa-solid fa-calendar"></i> ${new Date(item.started_at).toLocaleString()}
          </div>
        </div>
        <div class="history-metrics">
          <span class="metric-pill">${item.repetitions} Reps</span>
          <span class="metric-pill">${formatDuration(item.duration_sec)}</span>
          <span class="metric-pill score">${item.repetitions === 0 ? 'N/A Form' : item.form_score + '% Form'}</span>
        </div>
      </div>
    `).join('');

  } catch (error) {
    console.error('[FitQuest Error]: Failed to fetch history:', error);
    container.innerHTML = `

      <div class="loading-spinner" style="color: #ef4444;">
        <i class="fa-solid fa-triangle-exclamation"></i> Could not fetch history from backend. Ensure FastAPI server is running.
      </div>
    `;
  }
}

/* --- Helpers --- */
function formatDuration(totalSeconds) {
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function getExerciseIcon(name) {
  const n = name.toLowerCase();
  if (n.includes('curl') || n.includes('raise')) return 'fa-dumbbell';
  if (n.includes('squat') || n.includes('lunge')) return 'fa-person-running';
  if (n.includes('push') || n.includes('press') || n.includes('plank')) return 'fa-child-reaching';
  return 'fa-person';
}

function getExerciseMuscleGroup(name) {
  const n = name.toLowerCase();
  if (n.includes('curl') || n.includes('tricep') || n.includes('raise') || n.includes('press')) return 'Upper Body (Arms & Shoulders)';
  if (n.includes('squat') || n.includes('lunge') || n.includes('calf')) return 'Lower Body (Legs & Glutes)';
  if (n.includes('crunch') || n.includes('situp') || n.includes('twist') || n.includes('plank')) return 'Core & Abs';
  return 'Full Body & Cardiovascular';
}

function escapeHTML(str) {
  if (!str) return '';
  return String(str).replace(/[&<>'"]/g, tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
}

function formatMarkdownText(text) {
  if (!text) return '';

  const lines = text.split(/\r?\n/);
  let htmlResult = [];
  let inList = null;

  function closeList() {
    if (inList) {
      htmlResult.push(`</${inList}>`);
      inList = null;
    }
  }

  for (let line of lines) {
    let trimmed = line.trim();

    const h3Match = trimmed.match(/^###\s+(.*)/);
    if (h3Match) {
      closeList();
      let content = processInlineMarkdown(escapeHTML(h3Match[1]));
      htmlResult.push(`<h3>${content}</h3>`);
      continue;
    }

    const h2Match = trimmed.match(/^##\s+(.*)/);
    if (h2Match) {
      closeList();
      let content = processInlineMarkdown(escapeHTML(h2Match[1]));
      htmlResult.push(`<h2>${content}</h2>`);
      continue;
    }

    const h1Match = trimmed.match(/^#\s+(.*)/);
    if (h1Match) {
      closeList();
      let content = processInlineMarkdown(escapeHTML(h1Match[1]));
      htmlResult.push(`<h1>${content}</h1>`);
      continue;
    }

    const bqMatch = trimmed.match(/^>\s+(.*)/);
    if (bqMatch) {
      closeList();
      let content = processInlineMarkdown(escapeHTML(bqMatch[1]));
      htmlResult.push(`<blockquote>${content}</blockquote>`);
      continue;
    }

    const unorderedMatch = trimmed.match(/^[-*]\s+(.*)/);
    if (unorderedMatch) {
      if (inList !== 'ul') {
        closeList();
        htmlResult.push('<ul class="markdown-list">');
        inList = 'ul';
      }
      let content = processInlineMarkdown(escapeHTML(unorderedMatch[1]));
      htmlResult.push(`<li>${content}</li>`);
      continue;
    }

    const orderedMatch = trimmed.match(/^\d+\.\s+(.*)/);
    if (orderedMatch) {
      if (inList !== 'ol') {
        closeList();
        htmlResult.push('<ol class="markdown-list">');
        inList = 'ol';
      }
      let content = processInlineMarkdown(escapeHTML(orderedMatch[1]));
      htmlResult.push(`<li>${content}</li>`);
      continue;
    }

    if (trimmed === '') {
      closeList();
      continue;
    }

    closeList();
    let content = processInlineMarkdown(escapeHTML(trimmed));
    htmlResult.push(`<p>${content}</p>`);
  }

  closeList();
  return htmlResult.join('');
}

function processInlineMarkdown(escapedStr) {
  let res = escapedStr.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  res = res.replace(/\*(.*?)\*/g, '<em>$1</em>');
  return res;
}


/* ==========================================================================
   STRUCTURED WORKOUT SESSIONS — ORCHESTRATION ENGINE
   ========================================================================== */

let activeWorkoutMode = 'quick'; // 'quick' or 'structured'
let structuredPlans = [];
let activeStructuredSession = null;
let restTimerInterval = null;
let restTimeRemaining = 0;

/**
 * Toggles workout selection view mode ('quick' vs 'structured')
 */
function switchWorkoutMode(mode) {
  activeWorkoutMode = mode;
  const quickBtn = document.getElementById('modeQuickBtn');
  const structBtn = document.getElementById('modeStructuredBtn');
  const exGrid = document.getElementById('exerciseGrid');
  const structGrid = document.getElementById('structuredPlanGrid');

  if (!quickBtn || !structBtn || !exGrid || !structGrid) return;

  if (mode === 'quick') {
    quickBtn.classList.add('active-mode');
    structBtn.classList.remove('active-mode');
    quickBtn.style.background = '';
    quickBtn.style.borderColor = '';
    structBtn.style.background = '';
    structBtn.style.borderColor = '';

    exGrid.style.display = 'grid';
    structGrid.style.display = 'none';
  } else {
    structBtn.classList.add('active-mode');
    quickBtn.classList.remove('active-mode');
    structBtn.style.background = '';
    structBtn.style.borderColor = '';
    quickBtn.style.background = '';
    quickBtn.style.borderColor = '';

    exGrid.style.display = 'none';
    structGrid.style.display = 'grid';

    if (structuredPlans.length === 0) {
      loadStructuredPlans();
    }
  }
}

/**
 * Fetches structured workout preset templates from GET /api/v1/structured-workouts/templates
 */
async function loadStructuredPlans() {
  const container = document.getElementById('structuredPlanGrid');
  if (!container) return;

  container.innerHTML = `<div class="loading-spinner"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading workout routines...</div>`;

  try {
    const response = await fetch(`${API_BASE}/structured-workouts/templates`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    structuredPlans = await response.json();

    if (!structuredPlans || structuredPlans.length === 0) {
      container.innerHTML = `<div class="loading-spinner">No structured workout plans available.</div>`;
      return;
    }

    container.innerHTML = structuredPlans.map((plan) => `
      <div class="exercise-card" onclick="openStructuredPlanModal(${plan.id})" style="border-top: 2px solid var(--accent-lime); cursor: pointer;">
        <div>
          <div class="ex-card-header">
            <div class="ex-icon-badge">
              <i class="fa-solid fa-layer-group"></i>
            </div>
            <span class="ex-difficulty-badge">${escapeHTML(plan.category)}</span>
          </div>
          <h3 class="ex-title">${escapeHTML(plan.title)}</h3>
          <p class="ex-desc">${escapeHTML(plan.description)}</p>
          <div style="display: flex; gap: 12px; font-size: 0.82rem; color: var(--text-secondary); margin-top: 12px;">
            <span><i class="fa-solid fa-dumbbell"></i> ${plan.exercises ? plan.exercises.length : 0} Exercises</span>
            <span><i class="fa-solid fa-clock"></i> ~${plan.estimated_duration_min} min</span>
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="openStructuredPlanModal(${plan.id})" style="margin-top: 14px; width: 100%; text-align: center;">
          Preview Routine <i class="fa-solid fa-arrow-right"></i>
        </button>
      </div>
    `).join('');

  } catch (error) {
    console.error('[FitQuest Error]: Failed to fetch structured plans:', error);
    container.innerHTML = `<div class="loading-spinner" style="color: #ef4444;"><i class="fa-solid fa-triangle-exclamation"></i> Could not load workout routines.</div>`;
  }
}

/**
 * Opens Structured Routine Preview Modal
 */
function openStructuredPlanModal(planId) {
  const plan = structuredPlans.find(p => p.id === planId);
  if (!plan) return;

  document.getElementById('planModalCategory').innerText = plan.category;
  document.getElementById('planModalTitle').innerText = plan.title;
  document.getElementById('planModalDesc').innerText = plan.description;

  const exList = document.getElementById('planModalExerciseList');
  exList.innerHTML = plan.exercises.map((item, idx) => `
    <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-surface-secondary); border: 1px solid var(--border-color); padding: 12px 16px; border-radius: var(--radius-sm);">
      <div>
        <span style="font-weight: 700; color: var(--text-primary); font-size: 0.92rem;">${idx + 1}. ${escapeHTML(item.exercise_name)}</span>
        <span style="font-size: 0.78rem; color: var(--text-muted); display: block;">Target: ${item.target_sets} sets × ${item.target_reps} reps</span>
      </div>
      <span class="setup-badge">${item.target_sets * item.target_reps} reps</span>
    </div>
  `).join('');

  const startBtn = document.getElementById('startStructuredPlanBtn');
  startBtn.onclick = () => {
    closeStructuredPlanModal();
    startStructuredWorkoutSession(plan);
  };

  document.getElementById('structuredPlanModal').style.display = 'flex';
}

function closeStructuredPlanModal() {
  document.getElementById('structuredPlanModal').style.display = 'none';
}

/**
 * Starts a structured workout routine session
 */
async function startStructuredWorkoutSession(plan) {
  try {
    const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
    const userId = typeof getAuthenticatedUserId === 'function' ? getAuthenticatedUserId() : null;

    if (!token || !userId) {
      alert('Please log in to start a structured workout routine.');
      if (typeof showUnauthenticatedState === 'function') {
        showUnauthenticatedState();
      }
      return;
    }

    const response = await fetch(`${API_BASE}/structured-workouts/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ user_id: userId, plan_id: plan.id })
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const sessionData = await response.json();

    activeStructuredSession = {
      id: sessionData.id,
      plan: plan,
      currentExIndex: 0,
      currentSetNumber: 1,
      loggedSets: []
    };

    // Show Structured HUD Banner
    document.getElementById('structuredHudBanner').style.display = 'flex';
    document.getElementById('structuredRoutineTitle').innerText = plan.title;

    // Launch first exercise
    launchStructuredExercise();

  } catch (error) {
    console.error('[FitQuest Error]: Failed to start structured workout session:', error);
    alert('Failed to start structured workout. Ensure backend server is running.');
  }
}

/**
 * Prepares and launches the currently active exercise in the structured sequence
 */
async function launchStructuredExercise() {
  if (!activeStructuredSession) return;

  const currentEx = activeStructuredSession.plan.exercises[activeStructuredSession.currentExIndex];
  if (!currentEx) {
    finishStructuredWorkout();
    return;
  }

  selectedExercise = {
    id: currentEx.exercise_id,
    name: currentEx.exercise_name
  };

  // Update HUD progress text
  document.getElementById('structuredExProgress').innerText = `Exercise ${activeStructuredSession.currentExIndex + 1} of ${activeStructuredSession.plan.exercises.length}: ${currentEx.exercise_name}`;
  document.getElementById('structuredSetProgress').innerText = `Set ${activeStructuredSession.currentSetNumber} of ${currentEx.target_sets} (Target: ${currentEx.target_reps} Reps)`;

  // Reset CV telemetry state & timer
  resetCVExerciseState();

  // Reset Copilot for new structured exercise (Phase 5)
  if (typeof resetCopilot === 'function' && selectedExercise) {
    resetCopilot(selectedExercise);
  }

  // Call start-session backend API to guarantee clean controller initialization
  try {
    await fetch(`${ML_API_BASE}/workouts/live/start-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: activeSessionId,
        exercise_choice: String(selectedExercise.id)
      })
    });
  } catch (e) {
    console.warn('[FitQuest Warning]: Live session start endpoint call failed:', e);
  }

  // Update title & transition directly to active step
  document.getElementById('activeExerciseTitle').innerText = `${currentEx.exercise_name} (Set ${activeStructuredSession.currentSetNumber})`;
  goToStep('workoutActiveStep');

  // Start demo avatar animation for current structured exercise
  if (demoAvatarEngine && selectedExercise) {
    demoAvatarEngine.loadExercise(selectedExercise.id);
    demoAvatarEngine.start();
  }

  // Connect webcam feed & start live CV stream
  await startCameraStream();
}

/**
 * Resets CV exercise tracker telemetry state cleanly before starting next set/exercise
 */
function resetCVExerciseState() {
  activeSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  currentRepCount = 0;
  currentFormScore = 0.0;
  accumulatedFeedback = [];
  workoutElapsedSeconds = 0;

  document.getElementById('hudRepCount').innerText = '0';
  document.getElementById('hudFormScore').innerText = 'N/A';
  document.getElementById('hudDuration').innerText = '00:00';
  document.getElementById('hudFeedback').innerText = 'Get ready... Position yourself in front of camera.';

  if (workoutTimerInterval) clearInterval(workoutTimerInterval);
  workoutStartTime = Date.now();
  workoutTimerInterval = setInterval(() => {
    workoutElapsedSeconds = Math.floor((Date.now() - workoutStartTime) / 1000);
    document.getElementById('hudDuration').innerText = formatDuration(workoutElapsedSeconds);
  }, 1000);
}

/**
 * Handles completion of the current set in a structured workout
 */
async function completeCurrentSet() {
  if (!activeStructuredSession) {
    endWorkoutSession();
    return;
  }

  stopCameraStream();

  const currentEx = activeStructuredSession.plan.exercises[activeStructuredSession.currentExIndex];
  const setNum = activeStructuredSession.currentSetNumber;

  const setPayload = {
    structured_session_id: activeStructuredSession.id,
    exercise_id: currentEx.exercise_id,
    set_number: setNum,
    target_reps: currentEx.target_reps,
    actual_reps: currentRepCount,
    duration_sec: workoutElapsedSeconds,
    form_score: currentRepCount === 0 ? 0.0 : currentFormScore,
    feedback_events: accumulatedFeedback
  };

  try {
    const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}/structured-workouts/log-set`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(setPayload)
    });

    if (res.ok) {
      const setLog = await res.json();
      activeStructuredSession.loggedSets.push(setLog);
    }
  } catch (err) {
    console.error('[FitQuest Error]: Failed to log set result:', err);
  }

  // Advance set or exercise
  if (setNum < currentEx.target_sets) {
    activeStructuredSession.currentSetNumber += 1;
    startRestTimer(45, `${currentEx.exercise_name} — Set ${activeStructuredSession.currentSetNumber} (${currentEx.target_reps} Reps)`);
  } else if (activeStructuredSession.currentExIndex < activeStructuredSession.plan.exercises.length - 1) {
    activeStructuredSession.currentExIndex += 1;
    activeStructuredSession.currentSetNumber = 1;
    const nextEx = activeStructuredSession.plan.exercises[activeStructuredSession.currentExIndex];
    startRestTimer(45, `${nextEx.exercise_name} — Set 1 (${nextEx.target_reps} Reps)`);
  } else {
    finishStructuredWorkout();
  }
}

/**
 * Handles completion of a set in a single-exercise workout session
 */
async function handleSingleExerciseSetComplete() {
  if (!activeWorkoutSetsState || !selectedExercise) {
    endWorkoutSession();
    return;
  }

  // 1. Pause frame transmission during rest/transition
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
    animationFrameId = null;
  }
  if (frameCaptureInterval) {
    clearInterval(frameCaptureInterval);
    frameCaptureInterval = null;
  }
  isProcessingFrame = false;

  // 2. Log completed set in local state
  const completedSetNum = activeWorkoutSetsState.currentSetNumber;
  const loggedSet = {
    setNumber: completedSetNum,
    actualReps: currentRepCount,
    targetReps: activeWorkoutSetsState.targetReps,
    formScore: currentRepCount === 0 ? 0.0 : currentFormScore,
    durationSec: workoutElapsedSeconds,
    feedback: [...accumulatedFeedback]
  };
  activeWorkoutSetsState.loggedSets.push(loggedSet);

  // 3. Stop active backend CV session cleanly for this set
  try {
    await fetch(`${ML_API_BASE}/workouts/live/stop-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: activeSessionId })
    });
  } catch (e) {
    console.warn('[FitQuest Warning]: Error stopping single exercise set session:', e);
  }

  // 4. Check if more sets remain
  if (completedSetNum < activeWorkoutSetsState.targetSets) {
    activeWorkoutSetsState.currentSetNumber += 1;
    const nextSetNum = activeWorkoutSetsState.currentSetNumber;
    const restSec = activeWorkoutSetsState.restSeconds || 60;
    const nextLabel = `NEXT: SET ${nextSetNum} / ${activeWorkoutSetsState.targetSets} · ${activeWorkoutSetsState.targetReps} REPS`;

    // Configure and open Rest Timer Modal
    startSingleExerciseRestTimer(restSec, completedSetNum, nextLabel);
  } else {
    // All planned sets complete -> proceed to REVIEW stage
    activeWorkoutSetsState.isSetCompleting = false;
    endWorkoutSession();
  }
}

/**
 * Handles manual click on "Complete Set" button during active workout
 */
function handleManualSetComplete() {
  if (activeStructuredSession) {
    completeCurrentSet();
  } else {
    if (activeWorkoutSetsState) {
      activeWorkoutSetsState.isSetCompleting = true;
    }
    handleSingleExerciseSetComplete();
  }
}

/**
 * Starts rest timer modal configured for single-exercise set progression
 */
function startSingleExerciseRestTimer(seconds, completedSetNum, nextLabel) {
  // Pause frame transmission
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
    animationFrameId = null;
  }
  if (frameCaptureInterval) {
    clearInterval(frameCaptureInterval);
    frameCaptureInterval = null;
  }
  isProcessingFrame = false;

  restTimeRemaining = seconds;

  // Update modal texts
  const badgeEl = document.getElementById('restModalHeaderBadge');
  if (badgeEl) badgeEl.innerText = `SET ${completedSetNum} COMPLETE ✓`;

  const compTextEl = document.getElementById('restModalSetCompleteText');
  if (compTextEl) compTextEl.innerText = `Set ${completedSetNum} Complete`;

  const nextLabelEl = document.getElementById('restNextExerciseLabel');
  if (nextLabelEl) nextLabelEl.innerText = nextLabel;

  const nextBtn = document.getElementById('restSkipBtn');
  if (nextBtn && activeWorkoutSetsState) {
    nextBtn.innerHTML = `<i class="fa-solid fa-forward-step"></i> Start Set ${activeWorkoutSetsState.currentSetNumber}`;
  }

  const dispEl = document.getElementById('restTimerDisplay');
  if (dispEl) dispEl.innerText = formatDuration(restTimeRemaining);

  const modalEl = document.getElementById('restTimerModal');
  if (modalEl) modalEl.style.display = 'flex';

  if (restTimerInterval) clearInterval(restTimerInterval);

  restTimerInterval = setInterval(() => {
    restTimeRemaining -= 1;
    if (dispEl) dispEl.innerText = formatDuration(restTimeRemaining);

    if (restTimeRemaining <= 0) {
      skipRestTimer();
    }
  }, 1000);
}

/**
 * Launches next set in single-exercise workout session
 */
async function launchNextSingleExerciseSet() {
  if (!selectedExercise || !activeWorkoutSetsState) return;

  activeWorkoutSetsState.isSetCompleting = false;

  // Generate new session ID for next set's CV session
  activeSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  currentRepCount = 0;
  currentFormScore = 100.0;
  accumulatedFeedback = [];

  // Update HUD
  const setPillEl = document.getElementById('hudSetProgress');
  if (setPillEl) {
    setPillEl.innerText = `SET ${activeWorkoutSetsState.currentSetNumber} / ${activeWorkoutSetsState.targetSets}`;
  }

  const repCountEl = document.getElementById('hudRepCount');
  if (repCountEl) repCountEl.innerText = '0';

  const repTargetEl = document.getElementById('hudRepTarget');
  if (repTargetEl) repTargetEl.innerText = `/ ${activeWorkoutSetsState.targetReps} REPS`;

  const progressFill = document.getElementById('hudRepProgressFill');
  if (progressFill) progressFill.style.width = '0%';

  const formScoreEl = document.getElementById('hudFormScore');
  if (formScoreEl) formScoreEl.innerText = 'Calibrating';

  const formPillEl = document.getElementById('hudFormScorePill');
  if (formPillEl) formPillEl.className = 'trainer-form-pill pill-neutral';

  const feedbackContainer = document.getElementById('hudFeedback');
  if (feedbackContainer) feedbackContainer.innerText = `Set ${activeWorkoutSetsState.currentSetNumber} Started · Maintain steady cadence!`;

  // Start new backend CV session for this set
  try {
    await fetch(`${ML_API_BASE}/workouts/live/start-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: activeSessionId,
        exercise_choice: String(selectedExercise.id)
      })
    });
  } catch (e) {
    console.warn('[FitQuest Warning]: Error starting next set session:', e);
  }

  // Resume frame transmission
  startFrameTransmission();
}

/**
 * Starts the rest countdown timer between sets
 */
function startRestTimer(seconds, nextLabel) {
  // Pause frame transmission during rest
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
    animationFrameId = null;
  }
  if (frameCaptureInterval) {
    clearInterval(frameCaptureInterval);
    frameCaptureInterval = null;
  }
  isProcessingFrame = false;

  restTimeRemaining = seconds;
  document.getElementById('restNextExerciseLabel').innerText = nextLabel;
  document.getElementById('restTimerDisplay').innerText = formatDuration(restTimeRemaining);
  document.getElementById('restTimerModal').style.display = 'flex';

  if (restTimerInterval) clearInterval(restTimerInterval);

  restTimerInterval = setInterval(() => {
    restTimeRemaining -= 1;
    document.getElementById('restTimerDisplay').innerText = formatDuration(restTimeRemaining);

    if (restTimeRemaining <= 0) {
      skipRestTimer();
    }
  }, 1000);
}

function addRestTime(sec) {
  restTimeRemaining += sec;
  document.getElementById('restTimerDisplay').innerText = formatDuration(restTimeRemaining);
}

function skipRestTimer() {
  if (restTimerInterval) {
    clearInterval(restTimerInterval);
    restTimerInterval = null;
  }
  const modalEl = document.getElementById('restTimerModal');
  if (modalEl) modalEl.style.display = 'none';

  // Resume next set/exercise based on workout mode
  if (activeStructuredSession) {
    launchStructuredExercise();
  } else if (activeWorkoutSetsState && activeWorkoutSetsState.isSingleExerciseFlow) {
    launchNextSingleExerciseSet();
  }
}

/**
 * Completes the entire structured workout routine and renders combined summary
 */
async function finishStructuredWorkout() {
  if (!activeStructuredSession) return;

  // Stop camera stream & background timer
  stopCameraStream();
  if (workoutTimerInterval) clearInterval(workoutTimerInterval);
  document.getElementById('structuredHudBanner').style.display = 'none';

  try {
    const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}/structured-workouts/complete/${activeStructuredSession.id}`, {
      method: 'POST',
      headers: headers
    });

    let summaryData = null;
    if (res.ok) {
      summaryData = await res.json();
    }

    renderStructuredSummaryView(summaryData);

  } catch (err) {
    console.error('[FitQuest Error]: Failed to complete structured workout:', err);
    goToStep('workoutSelectionStep');
  } finally {
    activeStructuredSession = null;
  }
}

/**
 * Renders the combined workout summary breakdown in workoutResultStep
 */
function renderStructuredSummaryView(summary) {
  goToStep('workoutResultStep');

  if (summary) {
    const totalDurationSec = summary.sets ? summary.sets.reduce((acc, s) => acc + (s.duration_sec || 0), 0) : 0;
    document.getElementById('resRepCount').innerText = `${summary.total_actual_reps} / ${summary.total_target_reps}`;
    document.getElementById('resDuration').innerText = formatDuration(totalDurationSec);
    document.getElementById('resFormScore').innerText = summary.completed_sets > 0 ? `${summary.average_form_score}%` : 'N/A';

    const aiMessage = `
      <strong>🏆 Structured Routine Completed!</strong><br>
      You completed <strong>${summary.completed_sets} sets</strong> across <strong>${summary.total_exercises} exercises</strong> with an average form accuracy of <strong>${summary.average_form_score}%</strong>.
    `;
    document.getElementById('resAICoaching').innerHTML = formatMarkdownText(aiMessage);
  }

  // Refresh gamification streaks
  if (typeof loadGamificationData === 'function') {
    loadGamificationData();
  }
}

/**
 * 5. Hardware-Accelerated WebGL/WebGPU ONNX Runtime Web Session Initializer
 * Enables client GPU execution provider to offload tensor math from CPU.
 */
async function createHardwareAcceleratedSession(modelPath = 'models/yolov8n-pose.onnx') {
  if (typeof ort === 'undefined') {
    return null;
  }
  try {
    const executionProviders = [];
    if (typeof navigator !== 'undefined' && 'gpu' in navigator) {
      executionProviders.push('webgpu');
    }
    executionProviders.push('webgl');
    executionProviders.push('wasm');

    const session = await ort.InferenceSession.create(modelPath, {
      executionProviders: executionProviders,
      graphOptimizationLevel: 'all'
    });
    console.log('[FitQuest WebGL Acceleration] Active execution providers:', session.executionProviders || executionProviders);
    return session;
  } catch (err) {
    console.warn('[FitQuest WebGL Acceleration Warning]: WebGL session initialization failed:', err);
    return null;
  }
}

// Export UI functions to window object
window.switchTab = switchTab;
window.switchWorkoutMode = switchWorkoutMode;
window.openStructuredPlanModal = openStructuredPlanModal;
window.closeStructuredPlanModal = closeStructuredPlanModal;
window.completeCurrentSet = completeCurrentSet;
window.handleManualSetComplete = handleManualSetComplete;
window.skipRestTimer = skipRestTimer;
window.addRestTime = addRestTime;
window.handleSingleExerciseSetComplete = handleSingleExerciseSetComplete;
window.resolveExercisePrescription = resolveExercisePrescription;
window.stopCameraStream = stopCameraStream;
window.createHardwareAcceleratedSession = createHardwareAcceleratedSession;

// Page Visibility Safety: Stop active camera tracks if browser tab/window is hidden
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    if (webcamStream || frameCaptureInterval || animationFrameId) {
      stopCameraStream();
    }
  }
});


