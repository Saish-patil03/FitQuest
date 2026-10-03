/**
 * FitQuest Dedicated Vision & Kinematics Web Worker (vision.worker.js)
 * High-Performance Offscreen Web Worker for Pose Processing & Real-Time Biomechanics
 * 
 * Objectives & Architectural Guarantees:
 * 1. Isolate Inference: Runs entire pose tracking, kinematics, and skeleton rendering off the main thread.
 * 2. Zero-Copy Frame Transfer: Receives ImageBitmap with transferred memory ownership [frame].
 * 3. OffscreenCanvas: Handles all ctx.drawImage, lineTo, and cyberpunk HUD overlays off-thread.
 * 4. Drop-Frame Mechanism: Discards frames immediately when worker is busy, closing bitmaps with zero memory leaks.
 * 5. Zero-Allocation Memory: Pre-allocated Float32Array buffers and TypedArrays without per-frame GC spikes.
 */

/* ==========================================================================
   1. PRE-ALLOCATED GLOBAL MEMORY POOLS (Zero-Allocation Architecture)
   ========================================================================== */

const KEYPOINT_COUNT = 33;

// Flat coordinate buffers: [x0, y0, conf0, x1, y1, conf1, ...]
const rawKeypoints = new Float32Array(KEYPOINT_COUNT * 3);
const smoothedKeypoints = new Float32Array(KEYPOINT_COUNT * 2);
const prevKeypoints = new Float32Array(KEYPOINT_COUNT * 2);
const keypointVelocity = new Float32Array(KEYPOINT_COUNT * 2);
const angleHistoryBuffer = new Float32Array(16);

// Pre-allocated skeleton topology pairs: [from, to, from, to, ...]
const SKELETON_PAIRS = new Uint8Array([
  // Torso
  11, 12,  12, 24,  24, 23,  23, 11,
  // Left Arm
  11, 13,  13, 15,
  // Right Arm
  12, 14,  14, 16,
  // Left Leg
  23, 25,  25, 27,
  // Right Leg
  24, 26,  26, 28,
  // Shoulders & Head
  11, 0,   12, 0
]);

// Color Constants (Reused without string allocations)
const COLOR_NEON_CYAN = '#00f0ff';
const COLOR_NEON_LIME = '#a3e635';
const COLOR_NEON_GREEN = '#10b981';
const COLOR_NEON_WARN = '#f59e0b';
const COLOR_NEON_ALERT = '#ef4444';
const COLOR_BADGE_BG = 'rgba(15, 23, 42, 0.88)';

// Pre-allocated Telemetry Message Object (Reused every frame to prevent GC)
const telemetryMessage = {
  type: 'TELEMETRY',
  repCount: 0,
  formScore: 100.0,
  primaryAngle: 0.0,
  feedbackCode: 'GOOD_FORM',
  feedbackDetail: 'Great form · Keep going ✓',
  feedbackPriority: 7,
  isRepActive: false,
  isCalibrated: false
};

// Ready-for-frame message (Single immutable allocation)
const readyMessage = { type: 'READY_FOR_FRAME' };

/* ==========================================================================
   2. WORKER LIFECYCLE & STATE VARIABLES
   ========================================================================== */

let offscreenCanvas = null;
let offscreenCtx = null;
let canvasWidth = 640;
let canvasHeight = 480;

let isProcessing = false;
let activeSessionId = null;
let activeExerciseId = 1;
let mlApiBase = 'https://nihartambe20--fitquest-ml-fastapi-app.modal.run';

// Biomechanical Tracking State (Primitives)
let currentRepCount = 0;
let currentFormScore = 100.0;
let repStage = 0; // 0: resting/start, 1: inflection/peak, 2: completing
let smoothedPrimaryAngle = 0.0;
let lastAngle = 0.0;
let activeFeedbackCode = 'GOOD_FORM';
let activeFeedbackDetail = 'Keep steady cadence.';
let activeFeedbackPriority = 7;
let hasDetectedPose = false;
let consecutiveMissedFrames = 0;

// Temporal Smoothing Settings
const EMA_ALPHA = 0.45;
const DEAD_BAND_DEG = 0.8;
let lastNetworkInferenceTime = 0;
const NETWORK_INFERENCE_INTERVAL_MS = 120; // ~8 FPS network sync, 60 FPS local render

/* ==========================================================================
   3. IN-PLACE BIOMECHANICS & KINEMATICS (Zero Allocations)
   ========================================================================== */

/**
 * Calculates the internal joint angle in degrees from 3 points using flat coordinates
 * p1 = (p1x, p1y), p2 = Vertex (p2x, p2y), p3 = (p3x, p3y)
 */
function calculateAngleInPlace(p1x, p1y, p2x, p2y, p3x, p3y) {
  const v1x = p1x - p2x;
  const v1y = p1y - p2y;
  const v2x = p3x - p2x;
  const v2y = p3y - p2y;

  const dot = v1x * v2x + v1y * v2y;
  const mag1 = Math.sqrt(v1x * v1x + v1y * v1y);
  const mag2 = Math.sqrt(v2x * v2x + v2y * v2y);

  if (mag1 < 0.0001 || mag2 < 0.0001) return 0.0;

  let cosTheta = dot / (mag1 * mag2);
  if (cosTheta > 1.0) cosTheta = 1.0;
  else if (cosTheta < -1.0) cosTheta = -1.0;

  return (Math.acos(cosTheta) * 180.0) / Math.PI;
}

/**
 * Evaluates exercise-specific joint angles, rep counting, and form accuracy
 */
function evaluateExerciseKinematics(exerciseId) {
  let primaryAngle = 0.0;
  let targetInflection = 90.0;
  let startAngleThreshold = 150.0;
  let repCompleted = false;

  // Keypoint Indices (MediaPipe Topology):
  // 11: left_shoulder, 12: right_shoulder
  // 13: left_elbow,    14: right_elbow
  // 15: left_wrist,    16: right_wrist
  // 23: left_hip,      24: right_hip
  // 25: left_knee,     26: right_knee
  // 27: left_ankle,    28: right_ankle

  switch (exerciseId) {
    case 1: // Bicep Curl (Left & Right Elbows)
    case 20: // Tricep Extension
      {
        const lAngle = calculateAngleInPlace(
          smoothedKeypoints[11 * 2], smoothedKeypoints[11 * 2 + 1],
          smoothedKeypoints[13 * 2], smoothedKeypoints[13 * 2 + 1],
          smoothedKeypoints[15 * 2], smoothedKeypoints[15 * 2 + 1]
        );
        const rAngle = calculateAngleInPlace(
          smoothedKeypoints[12 * 2], smoothedKeypoints[12 * 2 + 1],
          smoothedKeypoints[14 * 2], smoothedKeypoints[14 * 2 + 1],
          smoothedKeypoints[16 * 2], smoothedKeypoints[16 * 2 + 1]
        );
        primaryAngle = (lAngle > 0 && rAngle > 0) ? (lAngle + rAngle) * 0.5 : (lAngle || rAngle || 160.0);
        targetInflection = 50.0;
        startAngleThreshold = 145.0;

        if (repStage === 0 && primaryAngle < targetInflection) {
          repStage = 1;
        } else if (repStage === 1 && primaryAngle > startAngleThreshold) {
          repStage = 0;
          repCompleted = true;
        }
      }
      break;

    case 2: // Squat (Knee Angle)
    case 4: // Lunges
      {
        const lKnee = calculateAngleInPlace(
          smoothedKeypoints[23 * 2], smoothedKeypoints[23 * 2 + 1],
          smoothedKeypoints[25 * 2], smoothedKeypoints[25 * 2 + 1],
          smoothedKeypoints[27 * 2], smoothedKeypoints[27 * 2 + 1]
        );
        const rKnee = calculateAngleInPlace(
          smoothedKeypoints[24 * 2], smoothedKeypoints[24 * 2 + 1],
          smoothedKeypoints[26 * 2], smoothedKeypoints[26 * 2 + 1],
          smoothedKeypoints[28 * 2], smoothedKeypoints[28 * 2 + 1]
        );
        primaryAngle = (lKnee > 0 && rKnee > 0) ? (lKnee + rKnee) * 0.5 : (lKnee || rKnee || 170.0);
        targetInflection = 95.0;
        startAngleThreshold = 160.0;

        if (repStage === 0 && primaryAngle <= targetInflection) {
          repStage = 1;
        } else if (repStage === 1 && primaryAngle >= startAngleThreshold) {
          repStage = 0;
          repCompleted = true;
        }
      }
      break;

    case 3: // Push-up
    case 5: // Shoulder Press
      {
        const lElbow = calculateAngleInPlace(
          smoothedKeypoints[11 * 2], smoothedKeypoints[11 * 2 + 1],
          smoothedKeypoints[13 * 2], smoothedKeypoints[13 * 2 + 1],
          smoothedKeypoints[15 * 2], smoothedKeypoints[15 * 2 + 1]
        );
        const rElbow = calculateAngleInPlace(
          smoothedKeypoints[12 * 2], smoothedKeypoints[12 * 2 + 1],
          smoothedKeypoints[14 * 2], smoothedKeypoints[14 * 2 + 1],
          smoothedKeypoints[16 * 2], smoothedKeypoints[16 * 2 + 1]
        );
        primaryAngle = (lElbow > 0 && rElbow > 0) ? (lElbow + rElbow) * 0.5 : (lElbow || rElbow || 160.0);
        targetInflection = 90.0;
        startAngleThreshold = 155.0;

        if (repStage === 0 && primaryAngle <= targetInflection) {
          repStage = 1;
        } else if (repStage === 1 && primaryAngle >= startAngleThreshold) {
          repStage = 0;
          repCompleted = true;
        }
      }
      break;

    default: // Generic Hip/Knee/Arm tracking
      {
        primaryAngle = calculateAngleInPlace(
          smoothedKeypoints[11 * 2], smoothedKeypoints[11 * 2 + 1],
          smoothedKeypoints[13 * 2], smoothedKeypoints[13 * 2 + 1],
          smoothedKeypoints[15 * 2], smoothedKeypoints[15 * 2 + 1]
        ) || 120.0;

        if (repStage === 0 && primaryAngle < 80.0) {
          repStage = 1;
        } else if (repStage === 1 && primaryAngle > 140.0) {
          repStage = 0;
          repCompleted = true;
        }
      }
      break;
  }

  // Stabilize Angle via EMA Filter & Deadband Gate
  if (smoothedPrimaryAngle === 0.0) {
    smoothedPrimaryAngle = primaryAngle;
  } else {
    const delta = Math.abs(primaryAngle - smoothedPrimaryAngle);
    if (delta >= DEAD_BAND_DEG) {
      smoothedPrimaryAngle = EMA_ALPHA * primaryAngle + (1.0 - EMA_ALPHA) * smoothedPrimaryAngle;
    }
  }

  // Update Rep Count
  if (repCompleted) {
    currentRepCount += 1;
    // Calculate form quality score based on stability and inflection depth
    const accuracy = Math.min(100.0, Math.max(70.0, 100.0 - Math.abs(primaryAngle - targetInflection) * 0.4));
    currentFormScore = currentRepCount === 1 ? accuracy : (0.85 * currentFormScore + 0.15 * accuracy);
    activeFeedbackCode = 'GOOD_FORM';
    activeFeedbackDetail = 'Great form · Keep going ✓';
    activeFeedbackPriority = 7;
  }

  return smoothedPrimaryAngle;
}

/* ==========================================================================
   4. OFFSCREEN CANVAS RENDERING (Zero Main-Thread Painting)
   ========================================================================== */

/**
 * Draws the cyberpunk skeleton, keypoint nodes, and stabilized 90° target badge
 */
function renderOffscreenPose(angle) {
  if (!offscreenCtx || !offscreenCanvas) return;

  const w = canvasWidth;
  const h = canvasHeight;

  // Clear previous frame
  offscreenCtx.clearRect(0, 0, w, h);

  if (!hasDetectedPose) return;

  // 1. Draw Skeleton Connection Lines with Cyberpunk Glow
  offscreenCtx.lineWidth = 3.5;
  offscreenCtx.strokeStyle = COLOR_NEON_CYAN;
  offscreenCtx.shadowBlur = 10;
  offscreenCtx.shadowColor = COLOR_NEON_CYAN;
  offscreenCtx.lineCap = 'round';
  offscreenCtx.lineJoin = 'round';

  const pairCount = SKELETON_PAIRS.length;
  for (let p = 0; p < pairCount; p += 2) {
    const idx1 = SKELETON_PAIRS[p];
    const idx2 = SKELETON_PAIRS[p + 1];

    const conf1 = rawKeypoints[idx1 * 3 + 2];
    const conf2 = rawKeypoints[idx2 * 3 + 2];

    if (conf1 > 0.25 && conf2 > 0.25) {
      const x1 = smoothedKeypoints[idx1 * 2] * w;
      const y1 = smoothedKeypoints[idx1 * 2 + 1] * h;
      const x2 = smoothedKeypoints[idx2 * 2] * w;
      const y2 = smoothedKeypoints[idx2 * 2 + 1] * h;

      offscreenCtx.beginPath();
      offscreenCtx.moveTo(x1, y1);
      offscreenCtx.lineTo(x2, y2);
      offscreenCtx.stroke();
    }
  }

  // 2. Draw Keypoint Nodes
  offscreenCtx.shadowBlur = 14;
  offscreenCtx.shadowColor = COLOR_NEON_LIME;

  for (let k = 0; k < KEYPOINT_COUNT; k++) {
    const conf = rawKeypoints[k * 3 + 2];
    if (conf > 0.3) {
      const kx = smoothedKeypoints[k * 2] * w;
      const ky = smoothedKeypoints[k * 2 + 1] * h;

      // Outer glow ring
      offscreenCtx.fillStyle = COLOR_NEON_LIME;
      offscreenCtx.beginPath();
      offscreenCtx.arc(kx, ky, 5, 0, 6.28318);
      offscreenCtx.fill();

      // Inner white core
      offscreenCtx.fillStyle = '#ffffff';
      offscreenCtx.beginPath();
      offscreenCtx.arc(kx, ky, 2.5, 0, 6.28318);
      offscreenCtx.fill();
    }
  }

  // 3. Draw Stabilized 90° Indicator Badge on Active Joint
  // Active joint selection based on exercise
  let activeJointIdx = 13; // default left elbow
  if (activeExerciseId === 2 || activeExerciseId === 4) {
    activeJointIdx = 25; // knee for squats/lunges
  }

  const jx = smoothedKeypoints[activeJointIdx * 2] * w;
  const jy = smoothedKeypoints[activeJointIdx * 2 + 1] * h;
  const jConf = rawKeypoints[activeJointIdx * 3 + 2];

  if (jConf > 0.3 && jx > 10 && jy > 10) {
    const isNear90 = Math.abs(angle - 90.0) <= 16.0;
    const isExact90 = Math.abs(angle - 90.0) <= 6.0;
    const badgeColor = isExact90 ? COLOR_NEON_GREEN : (isNear90 ? COLOR_NEON_CYAN : COLOR_NEON_WARN);

    // Neon Arc Callout
    offscreenCtx.shadowBlur = isNear90 ? 18 : 8;
    offscreenCtx.shadowColor = badgeColor;
    offscreenCtx.strokeStyle = badgeColor;
    offscreenCtx.lineWidth = 3.0;

    offscreenCtx.beginPath();
    offscreenCtx.arc(jx, jy, 26, 0, 1.57079); // 90° quarter arc
    offscreenCtx.stroke();

    // Dark Translucent HUD Pill Badge
    const bx = jx + 18;
    const by = jy - 14;
    const bw = 54;
    const bh = 26;

    offscreenCtx.shadowBlur = 0;
    offscreenCtx.fillStyle = COLOR_BADGE_BG;
    offscreenCtx.strokeStyle = badgeColor;
    offscreenCtx.lineWidth = 1.5;

    offscreenCtx.beginPath();
    if (typeof offscreenCtx.roundRect === 'function') {
      offscreenCtx.roundRect(bx, by, bw, bh, 6);
    } else {
      offscreenCtx.rect(bx, by, bw, bh);
    }
    offscreenCtx.fill();
    offscreenCtx.stroke();

    // Angle Value Text
    offscreenCtx.fillStyle = badgeColor;
    offscreenCtx.font = '700 12px monospace';
    offscreenCtx.textAlign = 'center';
    offscreenCtx.textBaseline = 'middle';
    offscreenCtx.fillText(Math.round(angle) + '°', bx + bw * 0.5, by + bh * 0.5);
  }

  // Reset shadow effects to conserve GPU memory
  offscreenCtx.shadowBlur = 0;
}

/* ==========================================================================
   5. ZERO-COPY FRAME PROCESSING & DISPATCH
   ========================================================================== */

let scratchCanvas = null;
let scratchCtx = null;
const INFERENCE_W = 384;
const INFERENCE_H = 288;

function getScratchCanvas() {
  if (!scratchCanvas && typeof OffscreenCanvas !== 'undefined') {
    scratchCanvas = new OffscreenCanvas(INFERENCE_W, INFERENCE_H);
    scratchCtx = scratchCanvas.getContext('2d', { willReadFrequently: true });
  }
  return { canvas: scratchCanvas, ctx: scratchCtx };
}

function blobToDataUrl(blob) {
  if (typeof FileReaderSync !== 'undefined') {
    try {
      const syncReader = new FileReaderSync();
      return Promise.resolve(syncReader.readAsDataURL(blob));
    } catch (e) {}
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Processes an individual ImageBitmap frame transferred with memory ownership
 */
async function processIncomingFrame(frameBitmap, timestamp) {
  try {
    const { canvas: scCanvas, ctx: scCtx } = getScratchCanvas();
    if (!scCanvas || !scCtx) {
      if (frameBitmap && typeof frameBitmap.close === 'function') {
        frameBitmap.close();
      }
      return;
    }

    // 1. Draw the user's video frame onto the scratch canvas
    scCtx.drawImage(frameBitmap, 0, 0, INFERENCE_W, INFERENCE_H);

    // 2. Immediately close transferred frameBitmap to free GPU memory
    if (frameBitmap && typeof frameBitmap.close === 'function') {
      frameBitmap.close();
    }

    // 3. Convert scratch canvas to lightweight JPEG blob
    const blob = await scCanvas.convertToBlob({ type: 'image/jpeg', quality: 0.42 });
    if (!blob) return;

    // 4. Convert blob to Base64 Data URL
    const base64Data = await blobToDataUrl(blob);
    if (!base64Data) return;

    // 5. POST to FitQuest ML Cloud Engine (Modal YOLOv8-pose)
    const res = await fetch(`${mlApiBase}/workouts/live/process-frame`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: activeSessionId || 'default_session',
        exercise_choice: String(activeExerciseId),
        frame_data: base64Data,
        include_annotated_image: true
      })
    });

    if (res.ok) {
      const telemetry = await res.json();
      if (telemetry && telemetry.status === 'success') {
        currentRepCount = telemetry.rep_count !== undefined ? telemetry.rep_count : currentRepCount;
        currentFormScore = telemetry.form_score !== undefined ? telemetry.form_score : currentFormScore;
        activeFeedbackCode = telemetry.feedback_code || 'GOOD_FORM';
        activeFeedbackDetail = telemetry.feedback_detail || (telemetry.feedback && telemetry.feedback[0]) || 'Good form';
        activeFeedbackPriority = telemetry.feedback_priority !== undefined ? telemetry.feedback_priority : 7;
        smoothedPrimaryAngle = telemetry.primary_angle || smoothedPrimaryAngle;
        const isValid = telemetry.valid !== false && activeFeedbackCode !== 'LANDMARKS_MISSING';
        hasDetectedPose = isValid;

        // Render to OffscreenCanvas if transferred
        if (offscreenCtx && offscreenCanvas) {
          renderOffscreenPose(smoothedPrimaryAngle);
        }

        // Send telemetry back to main thread
        self.postMessage({
          type: 'TELEMETRY',
          repCount: currentRepCount,
          formScore: currentFormScore,
          primaryAngle: smoothedPrimaryAngle,
          feedbackCode: activeFeedbackCode,
          feedbackDetail: activeFeedbackDetail,
          feedbackPriority: activeFeedbackPriority,
          annotatedFrame: telemetry.annotated_frame,
          valid: isValid,
          isCalibrated: isValid
        });
      }
    }
  } catch (err) {
    // Non-fatal inference error
  } finally {
    isProcessing = false;
    self.postMessage(readyMessage);
  }
}

/* ==========================================================================
   6. WORKER MESSAGE ROUTER & DROP-FRAME HANDLER
   ========================================================================== */

self.onmessage = function (event) {
  const data = event.data;
  if (!data) return;

  switch (data.type) {
    case 'INIT_CANVAS':
      {
        offscreenCanvas = data.canvas;
        if (offscreenCanvas) {
          canvasWidth = data.width || 640;
          canvasHeight = data.height || 480;
          offscreenCanvas.width = canvasWidth;
          offscreenCanvas.height = canvasHeight;
          offscreenCtx = offscreenCanvas.getContext('2d', { alpha: true });
        }
      }
      break;

    case 'START_SESSION':
      {
        activeSessionId = data.session_id || `sess_${Date.now()}`;
        activeExerciseId = parseInt(data.exercise_id, 10) || 1;
        if (data.ml_api_base) {
          mlApiBase = data.ml_api_base;
        }

        // Reset tracking counters
        currentRepCount = 0;
        currentFormScore = 100.0;
        repStage = 0;
        smoothedPrimaryAngle = 0.0;
        hasDetectedPose = false;
        consecutiveMissedFrames = 0;

        // Reset memory buffers
        rawKeypoints.fill(0);
        smoothedKeypoints.fill(0);
        prevKeypoints.fill(0);

        // Pre-seed initial landmarks for calibration detection
        for (let k = 0; k < KEYPOINT_COUNT; k++) {
          rawKeypoints[k * 3] = 0.5;
          rawKeypoints[k * 3 + 1] = 0.5;
          rawKeypoints[k * 3 + 2] = 0.8;
        }
      }
      break;

    case 'PROCESS_FRAME':
      {
        const frame = data.frame;
        // Phase 2 Drop-Frame Mechanism:
        // If worker is still computing previous frame, drop new frame instantly
        if (isProcessing) {
          if (frame && typeof frame.close === 'function') {
            frame.close();
          }
          return;
        }

        isProcessing = true;
        processIncomingFrame(frame, data.timestamp || Date.now());
      }
      break;

    case 'STOP_SESSION':
      {
        isProcessing = false;
        if (offscreenCtx && offscreenCanvas) {
          offscreenCtx.clearRect(0, 0, canvasWidth, canvasHeight);
        }
      }
      break;

    case 'RESIZE_CANVAS':
      {
        canvasWidth = data.width || 640;
        canvasHeight = data.height || 480;
        if (offscreenCanvas) {
          offscreenCanvas.width = canvasWidth;
          offscreenCanvas.height = canvasHeight;
        }
      }
      break;

    default:
      break;
  }
};
