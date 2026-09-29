/**
 * FitQuest 2D Kinematic Exercise Demo Avatar Engine
 * Lightweight, hardware-accelerated 60 FPS Canvas Avatar demonstrating ideal form for 20 exercises.
 * Zero external dependencies. Zero network assets. Fully responsive.
 */

(function (window) {
  'use strict';

  /**
   * Helper math & easing functions
   */
  const TWO_PI = Math.PI * 2;

  function easeInOutQuad(t) {
    return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function clamp(val, min, max) {
    return Math.max(min, Math.min(max, val));
  }

  /**
   * Motion cycle curve: converts linear progress t in [0, 1) into smooth 2-way oscillation (0 -> 1 -> 0)
   * with configurable peak hold time.
   */
  function cycleProgress(t, holdFraction = 0.1) {
    // 0 -> 0.5 - hold/2 : descent/concentric
    // peak hold
    // ascent/return
    const halfHold = holdFraction / 2;
    if (t < 0.5 - halfHold) {
      const normalized = t / (0.5 - halfHold);
      return easeInOutQuad(normalized);
    } else if (t <= 0.5 + halfHold) {
      return 1.0;
    } else {
      const normalized = (t - (0.5 + halfHold)) / (0.5 - halfHold);
      return easeInOutQuad(1.0 - normalized);
    }
  }

  /**
   * Biomechanical Kinematic Motion Models for all 20 FitQuest exercises.
   * Coordinate origin is center-grounded: (0, 0) is hip-center / center-of-mass anchor.
   * Y points DOWN, X points RIGHT.
   */
  const EXERCISE_DEMO_CATALOG = {
    // 1. BICEP CURL
    1: {
      name: 'Bicep Curl',
      category: 'Upper Body',
      stance: 'standing_profile',
      primaryJoint: 'Elbow Flexion',
      targetMuscles: 'Biceps Brachii',
      repDurationSec: 2.6,
      getPose: function (t) {
        const p = cycleProgress(t, 0.12);
        // Elbow angle: 165° (relaxed) -> 40° (peak curl)
        const elbowAngle = lerp(165, 40, p) * (Math.PI / 180);
        const shoulder = { x: -10, y: -70 };
        const elbow = { x: -8, y: -25 };
        const wrist = {
          x: elbow.x + Math.sin(elbowAngle) * 42,
          y: elbow.y + Math.cos(elbowAngle) * 42
        };

        return {
          view: 'profile',
          head: { x: -5, y: -105 },
          neck: { x: -6, y: -80 },
          left_shoulder: shoulder,
          right_shoulder: { x: shoulder.x + 8, y: shoulder.y },
          left_elbow: elbow,
          right_elbow: { x: elbow.x + 6, y: elbow.y },
          left_wrist: wrist,
          right_wrist: { x: wrist.x + 6, y: wrist.y },
          mid_hip: { x: -5, y: 0 },
          left_hip: { x: -8, y: 0 },
          right_hip: { x: -2, y: 0 },
          left_knee: { x: -10, y: 50 },
          right_knee: { x: -4, y: 50 },
          left_ankle: { x: -10, y: 100 },
          right_ankle: { x: -4, y: 100 },
          targetAngle: {
            joint: elbow,
            label: `${Math.round(180 - elbowAngle * (180 / Math.PI))}°`,
            angleVal: 180 - elbowAngle * (180 / Math.PI)
          }
        };
      },
      phaseAt: function (t) {
        if (t < 0.44) return { text: 'CONCENTRIC (CURL UP)', class: 'phase-concentric' };
        if (t < 0.56) return { text: 'PEAK SQUEEZE (HOLD)', class: 'phase-hold' };
        return { text: 'ECCENTRIC (LOWER SLOWLY)', class: 'phase-eccentric' };
      },
      cue: 'Keep elbows pinned to your torso. Squeeze biceps at the top.'
    },

    // 2. SQUAT
    2: {
      name: 'Squat',
      category: 'Lower Body',
      stance: 'standing_profile',
      primaryJoint: 'Knee & Hip Flexion',
      targetMuscles: 'Quadriceps, Glutes',
      repDurationSec: 3.0,
      getPose: function (t) {
        const p = cycleProgress(t, 0.15);
        // Squat depth: hip drops and shifts back, knees bend forward, torso angles forward for balance
        const hipY = lerp(0, 48, p);
        const hipX = lerp(-5, -28, p);
        const kneeX = lerp(-10, 16, p);
        const kneeY = lerp(50, 56, p);
        const torsoTilt = lerp(0, 24, p); // degrees
        const neckX = hipX + Math.sin(torsoTilt * (Math.PI / 180)) * 75 + 10;
        const neckY = hipY - Math.cos(torsoTilt * (Math.PI / 180)) * 75;
        const headX = neckX + 2;
        const headY = neckY - 24;

        // Arms reach forward for balance during descent
        const shoulder = { x: neckX - 2, y: neckY + 8 };
        const armReach = lerp(10, 45, p);
        const wrist = { x: shoulder.x + armReach, y: shoulder.y + lerp(35, 5, p) };

        return {
          view: 'profile',
          head: { x: headX, y: headY },
          neck: { x: neckX, y: neckY },
          left_shoulder: shoulder,
          right_shoulder: { x: shoulder.x + 8, y: shoulder.y },
          left_elbow: { x: (shoulder.x + wrist.x) / 2 + 5, y: (shoulder.y + wrist.y) / 2 + 8 },
          right_elbow: { x: (shoulder.x + wrist.x) / 2 + 12, y: (shoulder.y + wrist.y) / 2 + 8 },
          left_wrist: wrist,
          right_wrist: { x: wrist.x + 8, y: wrist.y },
          mid_hip: { x: hipX, y: hipY },
          left_hip: { x: hipX, y: hipY },
          right_hip: { x: hipX + 6, y: hipY },
          left_knee: { x: kneeX, y: kneeY },
          right_knee: { x: kneeX + 8, y: kneeY },
          left_ankle: { x: -8, y: 100 },
          right_ankle: { x: 2, y: 100 },
          targetAngle: {
            joint: { x: kneeX, y: kneeY },
            label: `${Math.round(lerp(170, 85, p))}°`,
            angleVal: lerp(170, 85, p)
          }
        };
      },
      phaseAt: function (t) {
        if (t < 0.42) return { text: 'DESCENT (HIPS BACK)', class: 'phase-eccentric' };
        if (t < 0.58) return { text: 'DEPTH HOLD (THIGHS PARALLEL)', class: 'phase-hold' };
        return { text: 'DRIVE UP (PUSH THROUGH HEELS)', class: 'phase-concentric' };
      },
      cue: 'Break at hips and knees simultaneously. Keep chest proud and knees tracking toes.'
    },

    // 3. PUSH-UP
    3: {
      name: 'Push-up',
      category: 'Chest & Arms',
      stance: 'prone_horizontal',
      primaryJoint: 'Elbow & Shoulder',
      targetMuscles: 'Pectorals, Triceps, Core',
      repDurationSec: 2.8,
      getPose: function (t) {
        const p = cycleProgress(t, 0.12);
        // In prone horizontal position, body pivots at feet/ankles
        // Push-up depth: body drops from chest elevation 55px -> 18px
        const chestY = lerp(20, 58, p);
        const shoulderX = -55;
        const shoulderY = chestY;
        const hipX = 15;
        const hipY = chestY + 6;
        const ankleX = 85;
        const ankleY = 65; // feet on floor

        const headX = shoulderX - 22;
        const headY = shoulderY - 8;
        const neckX = shoulderX - 6;
        const neckY = shoulderY - 2;

        const handX = shoulderX + 4;
        const handY = 65; // hands on floor
        const elbowX = shoulderX + lerp(8, 22, p);
        const elbowY = (shoulderY + handY) / 2 - lerp(10, 20, p);

        return {
          view: 'horizontal',
          head: { x: headX, y: headY },
          neck: { x: neckX, y: neckY },
          left_shoulder: { x: shoulderX, y: shoulderY },
          right_shoulder: { x: shoulderX + 4, y: shoulderY - 4 },
          left_elbow: { x: elbowX, y: elbowY },
          right_elbow: { x: elbowX + 4, y: elbowY - 4 },
          left_wrist: { x: handX, y: handY },
          right_wrist: { x: handX + 4, y: handY - 4 },
          mid_hip: { x: hipX, y: hipY },
          left_hip: { x: hipX, y: hipY },
          right_hip: { x: hipX + 4, y: hipY - 4 },
          left_knee: { x: (hipX + ankleX) / 2, y: (hipY + ankleY) / 2 },
          right_knee: { x: (hipX + ankleX) / 2 + 4, y: (hipY + ankleY) / 2 - 4 },
          left_ankle: { x: ankleX, y: ankleY },
          right_ankle: { x: ankleX + 4, y: ankleY - 4 },
          targetAngle: {
            joint: { x: elbowX, y: elbowY },
            label: `${Math.round(lerp(165, 88, p))}°`,
            angleVal: lerp(165, 88, p)
          }
        };
      },
      phaseAt: function (t) {
        if (t < 0.44) return { text: 'LOWER CHEST (45° ELBOWS)', class: 'phase-eccentric' };
        if (t < 0.56) return { text: 'BOTTOM HOVER (CHEST NEAR FLOOR)', class: 'phase-hold' };
        return { text: 'PRESS UP (FULL LOCKOUT)', class: 'phase-concentric' };
      },
      cue: 'Maintain a straight plank line from head to heels. Do not let hips sag.'
    },

    // 4. LUNGES
    4: {
      name: 'Lunges',
      category: 'Lower Body',
      stance: 'split_side',
      primaryJoint: 'Knee Flexion',
      targetMuscles: 'Quadriceps, Glutes, Hamstrings',
      repDurationSec: 3.2,
      getPose: function (t) {
        const p = cycleProgress(t, 0.12);
        const drop = lerp(0, 36, p);
        const hipX = 0;
        const hipY = drop;

        const frontKneeX = 35;
        const frontKneeY = 48 + drop * 0.4;
        const frontAnkleX = 35;
        const frontAnkleY = 100;

        const backKneeX = -32;
        const backKneeY = 55 + drop * 0.85;
        const backAnkleX = -58;
        const backAnkleY = 92;

        return {
          view: 'profile',
          head: { x: -2, y: -105 + drop },
          neck: { x: -2, y: -80 + drop },
          left_shoulder: { x: -4, y: -72 + drop },
          right_shoulder: { x: 4, y: -72 + drop },
          left_elbow: { x: -12, y: -38 + drop },
          right_elbow: { x: 12, y: -38 + drop },
          left_wrist: { x: -6, y: -5 + drop },
          right_wrist: { x: 6, y: -5 + drop },
          mid_hip: { x: hipX, y: hipY },
          left_hip: { x: hipX - 6, y: hipY },
          right_hip: { x: hipX + 6, y: hipY },
          left_knee: { x: frontKneeX, y: frontKneeY },
          right_knee: { x: backKneeX, y: backKneeY },
          left_ankle: { x: frontAnkleX, y: frontAnkleY },
          right_ankle: { x: backAnkleX, y: backAnkleY },
          targetAngle: {
            joint: { x: frontKneeX, y: frontKneeY },
            label: `${Math.round(lerp(160, 90, p))}°`,
            angleVal: lerp(160, 90, p)
          }
        };
      },
      phaseAt: function (t) {
        if (t < 0.44) return { text: 'STEP & LOWER (DROP BACK KNEE)', class: 'phase-eccentric' };
        if (t < 0.56) return { text: '90° DEPTH HOLD', class: 'phase-hold' };
        return { text: 'PUSH UP & RETURN', class: 'phase-concentric' };
      },
      cue: 'Keep front knee stacked over ankle. Torso tall and upright.'
    },

    // 5. SHOULDER PRESS
    5: {
      name: 'Shoulder Press',
      category: 'Upper Body',
      stance: 'standing_frontal',
      primaryJoint: 'Shoulder & Elbow Overhead',
      targetMuscles: 'Anterior & Medial Deltoids, Triceps',
      repDurationSec: 2.8,
      getPose: function (t) {
        const p = cycleProgress(t, 0.12);
        // Arms press from shoulder level (elbows 90°) to full overhead lockout (elbows 175°)
        const lElbowX = -38;
        const rElbowX = 38;
        const elbowY = lerp(-60, -90, p);

        const lWristX = lerp(-38, -16, p);
        const rWristX = lerp(38, 16, p);
        const wristY = lerp(-75, -135, p);

        return {
          view: 'frontal',
          head: { x: 0, y: -105 },
          neck: { x: 0, y: -80 },
          left_shoulder: { x: -26, y: -72 },
          right_shoulder: { x: 26, y: -72 },
          left_elbow: { x: lElbowX, y: elbowY },
          right_elbow: { x: rElbowX, y: elbowY },
          left_wrist: { x: lWristX, y: wristY },
          right_wrist: { x: rWristX, y: wristY },
          mid_hip: { x: 0, y: 0 },
          left_hip: { x: -18, y: 0 },
          right_hip: { x: 18, y: 0 },
          left_knee: { x: -20, y: 50 },
          right_knee: { x: 20, y: 50 },
          left_ankle: { x: -20, y: 100 },
          right_ankle: { x: 20, y: 100 },
          targetAngle: {
            joint: { x: lElbowX, y: elbowY },
            label: `${Math.round(lerp(85, 175, p))}°`,
            angleVal: lerp(85, 175, p)
          }
        };
      },
      phaseAt: function (t) {
        if (t < 0.44) return { text: 'PRESS OVERHEAD (LOCKOUT)', class: 'phase-concentric' };
        if (t < 0.56) return { text: 'TOP HOLD', class: 'phase-hold' };
        return { text: 'CONTROLLED LOWER TO CHIN', class: 'phase-eccentric' };
      },
      cue: 'Press straight upward without arching lower back. Lock out elbows overhead.'
    },

    // 6. JUMPING JACKS
    6: {
      name: 'Jumping Jacks',
      category: 'Cardio & Full Body',
      stance: 'standing_frontal',
      primaryJoint: 'Shoulder & Hip Abduction',
      targetMuscles: 'Full Body, Calves, Deltoids',
      repDurationSec: 1.6,
      getPose: function (t) {
        const p = cycleProgress(t, 0.05);
        // Jump out: arms raise to overhead V, feet spread wide; Return: arms down, feet together
        const armAngle = lerp(20, 160, p) * (Math.PI / 180);
        const lHandX = -Math.sin(armAngle) * 58;
        const lHandY = -72 - Math.cos(armAngle) * 58;
        const rHandX = Math.sin(armAngle) * 58;
        const rHandY = -72 - Math.cos(armAngle) * 58;

        const legSpread = lerp(16, 52, p);
        const jumpY = -Math.sin(t * Math.PI) * 12; // vertical hop bounce

        return {
          view: 'frontal',
          head: { x: 0, y: -105 + jumpY },
          neck: { x: 0, y: -80 + jumpY },
          left_shoulder: { x: -24, y: -72 + jumpY },
          right_shoulder: { x: 24, y: -72 + jumpY },
          left_elbow: { x: lHandX * 0.55, y: -72 + (lHandY - (-72)) * 0.55 + jumpY },
          right_elbow: { x: rHandX * 0.55, y: -72 + (rHandY - (-72)) * 0.55 + jumpY },
          left_wrist: { x: lHandX, y: lHandY + jumpY },
          right_wrist: { x: rHandX, y: rHandY + jumpY },
          mid_hip: { x: 0, y: 0 + jumpY },
          left_hip: { x: -16, y: 0 + jumpY },
          right_hip: { x: 16, y: 0 + jumpY },
          left_knee: { x: -legSpread * 0.65, y: 50 + jumpY },
          right_knee: { x: legSpread * 0.65, y: 50 + jumpY },
          left_ankle: { x: -legSpread, y: 100 + jumpY },
          right_ankle: { x: legSpread, y: 100 + jumpY }
        };
      },
      phaseAt: function (t) {
        if (t < 0.5) return { text: 'OUTWARD JUMP (SPREAD ARMS & LEGS)', class: 'phase-concentric' };
        return { text: 'INWARD RETURN (FEET TOGETHER)', class: 'phase-eccentric' };
      },
      cue: 'Land softly on the balls of your feet. Touch hands overhead.'
    },

    // 7. HIGH KNEES
    7: {
      name: 'High Knees',
      category: 'Cardio & Core',
      stance: 'running_profile',
      primaryJoint: 'Hip & Knee Elevation',
      targetMuscles: 'Hip Flexors, Quadriceps, Core',
      repDurationSec: 1.4,
      getPose: function (t) {
        // Alternating left/right knee drives
        const leftUp = Math.sin(t * TWO_PI) > 0;
        const p = Math.abs(Math.sin(t * TWO_PI));

        const lKneeY = leftUp ? lerp(50, -5, p) : lerp(50, 60, p);
        const lKneeX = leftUp ? lerp(-10, 22, p) : lerp(-10, -22, p);
        const lAnkleX = leftUp ? lKneeX - 5 : -15;
        const lAnkleY = leftUp ? lKneeY + 45 : 100;

        const rKneeY = !leftUp ? lerp(50, -5, p) : lerp(50, 60, p);
        const rKneeX = !leftUp ? lerp(-10, 22, p) : lerp(-10, -22, p);
        const rAnkleX = !leftUp ? rKneeX - 5 : -15;
        const rAnkleY = !leftUp ? rKneeY + 45 : 100;

        // Pumping opposite arms
        const lArmSwing = leftUp ? -25 : 25;

        return {
          view: 'profile',
          head: { x: 2, y: -105 },
          neck: { x: 0, y: -80 },
          left_shoulder: { x: -4, y: -72 },
          right_shoulder: { x: 4, y: -72 },
          left_elbow: { x: -10 - lArmSwing * 0.4, y: -38 },
          right_elbow: { x: 10 + lArmSwing * 0.4, y: -38 },
          left_wrist: { x: -lArmSwing, y: -15 },
          right_wrist: { x: lArmSwing, y: -15 },
          mid_hip: { x: 0, y: 0 },
          left_hip: { x: -6, y: 0 },
          right_hip: { x: 6, y: 0 },
          left_knee: { x: lKneeX, y: lKneeY },
          right_knee: { x: rKneeX, y: rKneeY },
          left_ankle: { x: lAnkleX, y: lAnkleY },
          right_ankle: { x: rAnkleX, y: rAnkleY }
        };
      },
      phaseAt: function (t) {
        return { text: 'HIGH KNEE CADENCE (KNEE TO HIP LEVEL)', class: 'phase-concentric' };
      },
      cue: 'Drive knees up past hip crease. Pump arms rhythmically.'
    },

    // 8. MOUNTAIN CLIMBERS
    8: {
      name: 'Mountain Climbers',
      category: 'Cardio & Core',
      stance: 'prone_horizontal',
      primaryJoint: 'Hip Flexion in Plank',
      targetMuscles: 'Core, Abdominals, Shoulders',
      repDurationSec: 1.5,
      getPose: function (t) {
        const leftDrive = Math.sin(t * TWO_PI) > 0;
        const p = Math.abs(Math.sin(t * TWO_PI));

        const shoulder = { x: -55, y: 25 };
        const hand = { x: -50, y: 65 };
        const hip = { x: 15, y: 30 };

        const lKneeX = leftDrive ? lerp(50, -10, p) : lerp(50, 75, p);
        const lKneeY = leftDrive ? lerp(55, 38, p) : 55;
        const lAnkleX = leftDrive ? lKneeX + 25 : 85;
        const lAnkleY = leftDrive ? 52 : 65;

        const rKneeX = !leftDrive ? lerp(50, -10, p) : lerp(50, 75, p);
        const rKneeY = !leftDrive ? lerp(55, 38, p) : 55;
        const rAnkleX = !leftDrive ? rKneeX + 25 : 85;
        const rAnkleY = !leftDrive ? 52 : 65;

        return {
          view: 'horizontal',
          head: { x: -75, y: 18 },
          neck: { x: -60, y: 22 },
          left_shoulder: shoulder,
          right_shoulder: { x: shoulder.x + 4, y: shoulder.y - 4 },
          left_elbow: { x: -52, y: 45 },
          right_elbow: { x: -48, y: 42 },
          left_wrist: hand,
          right_wrist: { x: hand.x + 4, y: hand.y - 4 },
          mid_hip: hip,
          left_hip: hip,
          right_hip: { x: hip.x + 4, y: hip.y - 4 },
          left_knee: { x: lKneeX, y: lKneeY },
          right_knee: { x: rKneeX, y: rKneeY },
          left_ankle: { x: lAnkleX, y: lAnkleY },
          right_ankle: { x: rAnkleX, y: rAnkleY }
        };
      },
      phaseAt: function (t) {
        return { text: 'DRIVE KNEE TO CHEST (PUMP)', class: 'phase-concentric' };
      },
      cue: 'Keep shoulders directly over wrists. Maintain flat hips without bouncing.'
    },

    // 9. PLANK
    9: {
      name: 'Plank',
      category: 'Core & Isometric',
      stance: 'prone_horizontal',
      primaryJoint: 'Spine & Core Isometric',
      targetMuscles: 'Transverse Abdominis, Glutes, Deltoids',
      repDurationSec: 4.0,
      getPose: function (t) {
        // Micro-breathing oscillation in isometric hold
        const breath = Math.sin(t * TWO_PI) * 1.5;

        const head = { x: -72, y: 35 + breath };
        const neck = { x: -58, y: 38 + breath };
        const shoulder = { x: -45, y: 40 + breath };
        const elbow = { x: -45, y: 65 }; // on forearms
        const wrist = { x: -28, y: 65 };
        const hip = { x: 15, y: 42 - breath * 0.5 };
        const knee = { x: 50, y: 48 };
        const ankle = { x: 85, y: 65 };

        return {
          view: 'horizontal',
          head: head,
          neck: neck,
          left_shoulder: shoulder,
          right_shoulder: { x: shoulder.x + 4, y: shoulder.y - 4 },
          left_elbow: elbow,
          right_elbow: { x: elbow.x + 4, y: elbow.y - 4 },
          left_wrist: wrist,
          right_wrist: { x: wrist.x + 4, y: wrist.y - 4 },
          mid_hip: hip,
          left_hip: hip,
          right_hip: { x: hip.x + 4, y: hip.y - 4 },
          left_knee: knee,
          right_knee: { x: knee.x + 4, y: knee.y - 4 },
          left_ankle: ankle,
          right_ankle: { x: ankle.x + 4, y: ankle.y - 4 },
          targetAngle: {
            joint: hip,
            label: '180° FLAT',
            angleVal: 180
          }
        };
      },
      phaseAt: function (t) {
        return { text: 'ISOMETRIC CORE HOLD (BRACE ABS)', class: 'phase-hold' };
      },
      cue: 'Form a straight line from crown of head to heels. Squeeze glutes and brace core.'
    },

    // 10. GLUTE BRIDGE
    10: {
      name: 'Glute Bridge',
      category: 'Lower Body & Glutes',
      stance: 'supine_bridge',
      primaryJoint: 'Hip Extension',
      targetMuscles: 'Gluteus Maximus, Hamstrings',
      repDurationSec: 3.0,
      getPose: function (t) {
        const p = cycleProgress(t, 0.15);
        // Supine on floor: shoulders on floor, feet on floor, hips drive up from floor to straight line
        const shoulder = { x: -55, y: 60 };
        const head = { x: -75, y: 62 };
        const neck = { x: -62, y: 60 };

        const hipX = lerp(-10, -5, p);
        const hipY = lerp(60, 22, p); // hip rises up

        const kneeX = 35;
        const kneeY = lerp(35, 22, p);
        const ankleX = 38;
        const ankleY = 65; // feet on floor

        return {
          view: 'horizontal',
          head: head,
          neck: neck,
          left_shoulder: shoulder,
          right_shoulder: { x: shoulder.x + 4, y: shoulder.y - 4 },
          left_elbow: { x: -35, y: 62 },
          right_elbow: { x: -31, y: 58 },
          left_wrist: { x: -15, y: 62 },
          right_wrist: { x: -11, y: 58 },
          mid_hip: { x: hipX, y: hipY },
          left_hip: { x: hipX, y: hipY },
          right_hip: { x: hipX + 4, y: hipY - 4 },
          left_knee: { x: kneeX, y: kneeY },
          right_knee: { x: kneeX + 4, y: kneeY - 4 },
          left_ankle: { x: ankleX, y: ankleY },
          right_ankle: { x: ankleX + 4, y: ankleY - 4 },
          targetAngle: {
            joint: { x: hipX, y: hipY },
            label: `${Math.round(lerp(120, 180, p))}°`,
            angleVal: lerp(120, 180, p)
          }
        };
      },
      phaseAt: function (t) {
        if (t < 0.44) return { text: 'DRIVE HIPS UP (SQUEEZE GLUTES)', class: 'phase-concentric' };
        if (t < 0.56) return { text: 'TOP HOLD (STRAIGHT LINE)', class: 'phase-hold' };
        return { text: 'LOWER UNDER CONTROL', class: 'phase-eccentric' };
      },
      cue: 'Drive through heels. Lock hips at the top without over-arching lower back.'
    },

    // 11. SIT-UPS
    11: {
      name: 'Sit-ups',
      category: 'Core & Abdominals',
      stance: 'supine_flexion',
      primaryJoint: 'Spine & Hip Flexion',
      targetMuscles: 'Rectus Abdominis, Hip Flexors',
      repDurationSec: 3.2,
      getPose: function (t) {
        const p = cycleProgress(t, 0.12);
        // Supine bent-knee sit up: torso curls from floor (angle 0°) to upright near knees (angle 75°)
        const torsoAngle = lerp(0, 75, p) * (Math.PI / 180);
        const hip = { x: -10, y: 60 };
        const shoulderX = hip.x - Math.cos(torsoAngle) * 55;
        const shoulderY = hip.y - Math.sin(torsoAngle) * 55;
        const headX = shoulderX - Math.cos(torsoAngle) * 22;
        const headY = shoulderY - Math.sin(torsoAngle) * 22;

        const knee = { x: 35, y: 32 };
        const ankle = { x: 45, y: 65 };

        return {
          view: 'horizontal',
          head: { x: headX, y: headY },
          neck: { x: (headX + shoulderX) / 2, y: (headY + shoulderY) / 2 },
          left_shoulder: { x: shoulderX, y: shoulderY },
          right_shoulder: { x: shoulderX + 4, y: shoulderY - 4 },
          left_elbow: { x: shoulderX + 18, y: shoulderY - 12 },
          right_elbow: { x: shoulderX + 22, y: shoulderY - 16 },
          left_wrist: { x: headX + 12, y: headY },
          right_wrist: { x: headX + 16, y: headY - 4 },
          mid_hip: hip,
          left_hip: hip,
          right_hip: { x: hip.x + 4, y: hip.y - 4 },
          left_knee: knee,
          right_knee: { x: knee.x + 4, y: knee.y - 4 },
          left_ankle: ankle,
          right_ankle: { x: ankle.x + 4, y: ankle.y - 4 }
        };
      },
      phaseAt: function (t) {
        if (t < 0.44) return { text: 'CURL TORSO UP TO KNEES', class: 'phase-concentric' };
        if (t < 0.56) return { text: 'TOP SQUEEZE', class: 'phase-hold' };
        return { text: 'LOWER CONTROLLED TO FLOOR', class: 'phase-eccentric' };
      },
      cue: 'Initiate movement with abdominals, not by pulling on your neck.'
    },

    // 12. CRUNCHES
    12: {
      name: 'Crunches',
      category: 'Upper Abdominals',
      stance: 'supine_partial',
      primaryJoint: 'Thoracic Spine Flexion',
      targetMuscles: 'Upper Rectus Abdominis',
      repDurationSec: 2.4,
      getPose: function (t) {
        const p = cycleProgress(t, 0.15);
        // Crunches lift shoulder blades off floor (30° flexion)
        const torsoAngle = lerp(0, 32, p) * (Math.PI / 180);
        const hip = { x: -10, y: 60 };
        const shoulderX = hip.x - Math.cos(torsoAngle) * 55;
        const shoulderY = hip.y - Math.sin(torsoAngle) * 55;
        const headX = shoulderX - Math.cos(torsoAngle) * 22;
        const headY = shoulderY - Math.sin(torsoAngle) * 22;

        const knee = { x: 35, y: 32 };
        const ankle = { x: 45, y: 65 };

        return {
          view: 'horizontal',
          head: { x: headX, y: headY },
          neck: { x: (headX + shoulderX) / 2, y: (headY + shoulderY) / 2 },
          left_shoulder: { x: shoulderX, y: shoulderY },
          right_shoulder: { x: shoulderX + 4, y: shoulderY - 4 },
          left_elbow: { x: shoulderX + 15, y: shoulderY - 18 },
          right_elbow: { x: shoulderX + 19, y: shoulderY - 22 },
          left_wrist: { x: headX + 10, y: headY },
          right_wrist: { x: headX + 14, y: headY - 4 },
          mid_hip: hip,
          left_hip: hip,
          right_hip: { x: hip.x + 4, y: hip.y - 4 },
          left_knee: knee,
          right_knee: { x: knee.x + 4, y: knee.y - 4 },
          left_ankle: ankle,
          right_ankle: { x: ankle.x + 4, y: ankle.y - 4 },
          targetAngle: {
            joint: { x: shoulderX, y: shoulderY },
            label: `${Math.round(lerp(0, 32, p))}°`,
            angleVal: lerp(0, 32, p)
          }
        };
      },
      phaseAt: function (t) {
        if (t < 0.44) return { text: 'FLEX RIBS TO HIPS', class: 'phase-concentric' };
        if (t < 0.56) return { text: 'PEAK ABDOMINAL CONTRACTION', class: 'phase-hold' };
        return { text: 'LOWER SHOULDER BLADES', class: 'phase-eccentric' };
      },
      cue: 'Keep lower back glued to the floor. Focus on contracting upper abs.'
    },

    // 13. LEG RAISES
    13: {
      name: 'Leg Raises',
      category: 'Lower Abdominals',
      stance: 'supine_horizontal',
      primaryJoint: 'Hip Flexion',
      targetMuscles: 'Lower Abs, Hip Flexors',
      repDurationSec: 3.0,
      getPose: function (t) {
        const p = cycleProgress(t, 0.12);
        // Supine on floor: straight legs lift together from 0° (floor) to 85° (vertical)
        const legAngle = lerp(6, 85, p) * (Math.PI / 180);
        const hip = { x: -10, y: 60 };
        const shoulder = { x: -65, y: 60 };
        const head = { x: -85, y: 60 };

        const kneeX = hip.x + Math.cos(legAngle) * 45;
        const kneeY = hip.y - Math.sin(legAngle) * 45;
        const ankleX = hip.x + Math.cos(legAngle) * 90;
        const ankleY = hip.y - Math.sin(legAngle) * 90;

        return {
          view: 'horizontal',
          head: head,
          neck: { x: -75, y: 60 },
          left_shoulder: shoulder,
          right_shoulder: { x: shoulder.x + 4, y: shoulder.y - 4 },
          left_elbow: { x: -45, y: 62 },
          right_elbow: { x: -41, y: 58 },
          left_wrist: { x: -25, y: 62 },
          right_wrist: { x: -21, y: 58 },
          mid_hip: hip,
          left_hip: hip,
          right_hip: { x: hip.x + 4, y: hip.y - 4 },
          left_knee: { x: kneeX, y: kneeY },
          right_knee: { x: kneeX + 4, y: kneeY - 4 },
          left_ankle: { x: ankleX, y: ankleY },
          right_ankle: { x: ankleX + 4, y: ankleY - 4 },
          targetAngle: {
            joint: hip,
            label: `${Math.round(legAngle * (180 / Math.PI))}°`,
            angleVal: legAngle * (180 / Math.PI)
          }
        };
      },
      phaseAt: function (t) {
        if (t < 0.44) return { text: 'LIFT STRAIGHT LEGS TO 90°', class: 'phase-concentric' };
        if (t < 0.56) return { text: 'VERTICAL HOLD', class: 'phase-hold' };
        return { text: 'LOWER LEGS WITHOUT TOUCHING FLOOR', class: 'phase-eccentric' };
      },
      cue: 'Press lower back into the mat. Lower legs with control without arching spine.'
    },

    // 14. RUSSIAN TWISTS
    14: {
      name: 'Russian Twists',
      category: 'Obliques & Core',
      stance: 'v_sit_seated',
      primaryJoint: 'Torso Rotation',
      targetMuscles: 'Internal & External Obliques',
      repDurationSec: 2.2,
      getPose: function (t) {
        // Seated V-sit rotating arms/hands from left side to right side
        const rot = Math.sin(t * TWO_PI); // -1 (left) to 1 (right)
        const hip = { x: -10, y: 35 };
        const torsoAngle = 45 * (Math.PI / 180);
        const shoulderBaseX = hip.x - Math.cos(torsoAngle) * 50;
        const shoulderBaseY = hip.y - Math.sin(torsoAngle) * 50;

        const handX = shoulderBaseX + 35 + rot * 25;
        const handY = shoulderBaseY + 25 + Math.abs(rot) * 10;

        return {
          view: 'frontal',
          head: { x: shoulderBaseX, y: shoulderBaseY - 24 },
          neck: { x: shoulderBaseX, y: shoulderBaseY - 6 },
          left_shoulder: { x: shoulderBaseX - 16 + rot * 6, y: shoulderBaseY },
          right_shoulder: { x: shoulderBaseX + 16 + rot * 6, y: shoulderBaseY },
          left_elbow: { x: (shoulderBaseX - 16 + handX) / 2, y: shoulderBaseY + 15 },
          right_elbow: { x: (shoulderBaseX + 16 + handX) / 2, y: shoulderBaseY + 15 },
          left_wrist: { x: handX - 4, y: handY },
          right_wrist: { x: handX + 4, y: handY },
          mid_hip: hip,
          left_hip: { x: hip.x - 12, y: hip.y },
          right_hip: { x: hip.x + 12, y: hip.y },
          left_knee: { x: hip.x + 35, y: hip.y - 12 },
          right_knee: { x: hip.x + 40, y: hip.y - 8 },
          left_ankle: { x: hip.x + 55, y: hip.y + 15 },
          right_ankle: { x: hip.x + 60, y: hip.y + 18 }
        };
      },
      phaseAt: function (t) {
        return { text: 'CONTROLLED ROTATION (LEFT & RIGHT)', class: 'phase-concentric' };
      },
      cue: 'Rotate your whole ribcage, not just your arms. Keep chest up and feet elevated.'
    },

    // 15. BICYCLE CRUNCHES
    15: {
      name: 'Bicycle Crunches',
      category: 'Obliques & Core',
      stance: 'supine_cross',
      primaryJoint: 'Diagonal Elbow-to-Knee',
      targetMuscles: 'Obliques, Rectus Abdominis',
      repDurationSec: 2.0,
      getPose: function (t) {
        const leftTurn = Math.sin(t * TWO_PI) > 0;
        const p = Math.abs(Math.sin(t * TWO_PI));

        const hip = { x: -10, y: 55 };
        const shoulder = { x: -60, y: 52 };
        const head = { x: -78, y: 46 };

        const lKneeX = leftTurn ? lerp(45, 10, p) : lerp(45, 75, p);
        const lKneeY = leftTurn ? lerp(45, 20, p) : lerp(45, 55, p);
        const rKneeX = !leftTurn ? lerp(45, 10, p) : lerp(45, 75, p);
        const rKneeY = !leftTurn ? lerp(45, 20, p) : lerp(45, 55, p);

        const lElbow = leftTurn ? { x: -25 + p * 20, y: 35 - p * 10 } : { x: -45, y: 35 };
        const rElbow = !leftTurn ? { x: -25 + p * 20, y: 35 - p * 10 } : { x: -45, y: 35 };

        return {
          view: 'horizontal',
          head: head,
          neck: { x: -68, y: 50 },
          left_shoulder: shoulder,
          right_shoulder: { x: shoulder.x + 4, y: shoulder.y - 4 },
          left_elbow: lElbow,
          right_elbow: rElbow,
          left_wrist: { x: head.x + 10, y: head.y },
          right_wrist: { x: head.x + 14, y: head.y - 4 },
          mid_hip: hip,
          left_hip: hip,
          right_hip: { x: hip.x + 4, y: hip.y - 4 },
          left_knee: { x: lKneeX, y: lKneeY },
          right_knee: { x: rKneeX, y: rKneeY },
          left_ankle: { x: lKneeX + 35, y: lKneeY + 20 },
          right_ankle: { x: rKneeX + 35, y: rKneeY + 20 }
        };
      },
      phaseAt: function (t) {
        return { text: 'DIAGONAL TWIST (ELBOW TO OPPOSITE KNEE)', class: 'phase-concentric' };
      },
      cue: 'Rotate through thoracic spine. Extend straight leg fully to 45° off the floor.'
    },

    // 16. SIDE LUNGES
    16: {
      name: 'Side Lunges',
      category: 'Lower Body',
      stance: 'lateral_frontal',
      primaryJoint: 'Lateral Knee & Hip Flexion',
      targetMuscles: 'Quadriceps, Glutes, Adductors',
      repDurationSec: 3.0,
      getPose: function (t) {
        const p = cycleProgress(t, 0.12);
        // Squats deep onto right leg while left leg stays straight
        const hipShift = lerp(0, 24, p);
        const hipDrop = lerp(0, 38, p);

        const rKneeX = lerp(20, 42, p);
        const rKneeY = lerp(50, 56 + hipDrop * 0.4, p);
        const lKneeX = lerp(-20, -35, p);
        const lKneeY = lerp(50, 48, p);

        return {
          view: 'frontal',
          head: { x: hipShift * 0.7, y: -105 + hipDrop * 0.6 },
          neck: { x: hipShift * 0.7, y: -80 + hipDrop * 0.6 },
          left_shoulder: { x: -24 + hipShift * 0.7, y: -72 + hipDrop * 0.6 },
          right_shoulder: { x: 24 + hipShift * 0.7, y: -72 + hipDrop * 0.6 },
          left_elbow: { x: -15 + hipShift, y: -35 + hipDrop },
          right_elbow: { x: 15 + hipShift, y: -35 + hipDrop },
          left_wrist: { x: hipShift, y: -10 + hipDrop },
          right_wrist: { x: hipShift, y: -10 + hipDrop },
          mid_hip: { x: hipShift, y: hipDrop },
          left_hip: { x: -18 + hipShift, y: hipDrop },
          right_hip: { x: 18 + hipShift, y: hipDrop },
          left_knee: { x: lKneeX, y: lKneeY },
          right_knee: { x: rKneeX, y: rKneeY },
          left_ankle: { x: -55, y: 100 },
          right_ankle: { x: 42, y: 100 }
        };
      },
      phaseAt: function (t) {
        if (t < 0.44) return { text: 'LATERAL SINK (SIT HIPS BACK)', class: 'phase-eccentric' };
        if (t < 0.56) return { text: 'DEEP LATERAL DEPTH', class: 'phase-hold' };
        return { text: 'DRIVE UP TO CENTER', class: 'phase-concentric' };
      },
      cue: 'Keep stationary leg completely straight with foot flat on the floor.'
    },

    // 17. CALF RAISES
    17: {
      name: 'Calf Raises',
      category: 'Lower Body',
      stance: 'standing_profile',
      primaryJoint: 'Ankle Plantarflexion',
      targetMuscles: 'Gastrocnemius, Soleus',
      repDurationSec: 2.2,
      getPose: function (t) {
        const p = cycleProgress(t, 0.18);
        // Entire body elevates 24px as heels rise off ground
        const heelElevation = lerp(0, 24, p);

        return {
          view: 'profile',
          head: { x: -5, y: -105 - heelElevation },
          neck: { x: -6, y: -80 - heelElevation },
          left_shoulder: { x: -8, y: -72 - heelElevation },
          right_shoulder: { x: 0, y: -72 - heelElevation },
          left_elbow: { x: -8, y: -32 - heelElevation },
          right_elbow: { x: 0, y: -32 - heelElevation },
          left_wrist: { x: -8, y: 5 - heelElevation },
          right_wrist: { x: 0, y: 5 - heelElevation },
          mid_hip: { x: -5, y: 0 - heelElevation },
          left_hip: { x: -8, y: 0 - heelElevation },
          right_hip: { x: -2, y: 0 - heelElevation },
          left_knee: { x: -8, y: 50 - heelElevation },
          right_knee: { x: -2, y: 50 - heelElevation },
          left_ankle: { x: -8, y: 95 - heelElevation },
          right_ankle: { x: -2, y: 95 - heelElevation },
          left_foot: { x: 4, y: 100 },
          right_foot: { x: 8, y: 100 },
          targetAngle: {
            joint: { x: -8, y: 95 - heelElevation },
            label: `${Math.round(lerp(90, 135, p))}°`,
            angleVal: lerp(90, 135, p)
          }
        };
      },
      phaseAt: function (t) {
        if (t < 0.44) return { text: 'DRIVE ONTO BALLS OF FEET', class: 'phase-concentric' };
        if (t < 0.56) return { text: 'PEAK CALF SQUEEZE', class: 'phase-hold' };
        return { text: 'LOWER HEELS SLOWLY', class: 'phase-eccentric' };
      },
      cue: 'Pause at the peak of the raise. Lower heels under control without bouncing.'
    },

    // 18. FRONT RAISES
    18: {
      name: 'Front Raises',
      category: 'Shoulders',
      stance: 'standing_profile',
      primaryJoint: 'Anterior Shoulder Flexion',
      targetMuscles: 'Anterior Deltoids',
      repDurationSec: 2.8,
      getPose: function (t) {
        const p = cycleProgress(t, 0.12);
        // Straight arm raises forward from 10° to 90° (parallel to floor)
        const armAngle = lerp(12, 90, p) * (Math.PI / 180);
        const shoulder = { x: -8, y: -72 };
        const handX = shoulder.x + Math.sin(armAngle) * 58;
        const handY = shoulder.y + Math.cos(armAngle) * 58;

        return {
          view: 'profile',
          head: { x: -5, y: -105 },
          neck: { x: -6, y: -80 },
          left_shoulder: shoulder,
          right_shoulder: { x: shoulder.x + 6, y: shoulder.y },
          left_elbow: { x: (shoulder.x + handX) / 2, y: (shoulder.y + handY) / 2 },
          right_elbow: { x: (shoulder.x + handX) / 2 + 6, y: (shoulder.y + handY) / 2 },
          left_wrist: { x: handX, y: handY },
          right_wrist: { x: handX + 6, y: handY },
          mid_hip: { x: -5, y: 0 },
          left_hip: { x: -8, y: 0 },
          right_hip: { x: -2, y: 0 },
          left_knee: { x: -8, y: 50 },
          right_knee: { x: -2, y: 50 },
          left_ankle: { x: -8, y: 100 },
          right_ankle: { x: -2, y: 100 },
          targetAngle: {
            joint: shoulder,
            label: `${Math.round(armAngle * (180 / Math.PI))}°`,
            angleVal: armAngle * (180 / Math.PI)
          }
        };
      },
      phaseAt: function (t) {
        if (t < 0.44) return { text: 'RAISE ARMS TO SHOULDER HEIGHT', class: 'phase-concentric' };
        if (t < 0.56) return { text: 'PARALLEL HOLD', class: 'phase-hold' };
        return { text: 'CONTROLLED DESCENT', class: 'phase-eccentric' };
      },
      cue: 'Do not swing your torso. Lift smoothly to eye level with slight elbow bend.'
    },

    // 19. LATERAL RAISES
    19: {
      name: 'Lateral Raises',
      category: 'Shoulders',
      stance: 'standing_frontal',
      primaryJoint: 'Shoulder Abduction',
      targetMuscles: 'Lateral Deltoids',
      repDurationSec: 2.8,
      getPose: function (t) {
        const p = cycleProgress(t, 0.12);
        // Arms raise laterally to sides from 15° to 90° (T-pose)
        const armAngle = lerp(15, 90, p) * (Math.PI / 180);
        const lHandX = -24 - Math.sin(armAngle) * 52;
        const lHandY = -72 + Math.cos(armAngle) * 52;
        const rHandX = 24 + Math.sin(armAngle) * 52;
        const rHandY = -72 + Math.cos(armAngle) * 52;

        return {
          view: 'frontal',
          head: { x: 0, y: -105 },
          neck: { x: 0, y: -80 },
          left_shoulder: { x: -24, y: -72 },
          right_shoulder: { x: 24, y: -72 },
          left_elbow: { x: (-24 + lHandX) / 2, y: (-72 + lHandY) / 2 - 4 },
          right_elbow: { x: (24 + rHandX) / 2, y: (-72 + rHandY) / 2 - 4 },
          left_wrist: { x: lHandX, y: lHandY },
          right_wrist: { x: rHandX, y: rHandY },
          mid_hip: { x: 0, y: 0 },
          left_hip: { x: -18, y: 0 },
          right_hip: { x: 18, y: 0 },
          left_knee: { x: -20, y: 50 },
          right_knee: { x: 20, y: 50 },
          left_ankle: { x: -20, y: 100 },
          right_ankle: { x: 20, y: 100 },
          targetAngle: {
            joint: { x: -24, y: -72 },
            label: `${Math.round(armAngle * (180 / Math.PI))}°`,
            angleVal: armAngle * (180 / Math.PI)
          }
        };
      },
      phaseAt: function (t) {
        if (t < 0.44) return { text: 'RAISE LATERALLY TO PARALLEL', class: 'phase-concentric' };
        if (t < 0.56) return { text: 'T-POSE HOLD', class: 'phase-hold' };
        return { text: 'LOWER SLOWLY', class: 'phase-eccentric' };
      },
      cue: 'Lead with your elbows. Stop when arms are parallel to the floor.'
    },

    // 20. TRICEP EXTENSIONS
    20: {
      name: 'Tricep Extensions',
      category: 'Arms & Triceps',
      stance: 'standing_profile',
      primaryJoint: 'Overhead Elbow Extension',
      targetMuscles: 'Triceps Brachii',
      repDurationSec: 2.8,
      getPose: function (t) {
        const p = cycleProgress(t, 0.12);
        // Upper arm stays fixed vertically overhead; forearm flexes back to 60° and extends to 175°
        const elbow = { x: -5, y: -95 };
        const forearmAngle = lerp(60, 175, p) * (Math.PI / 180);
        const wrist = {
          x: elbow.x + Math.sin(forearmAngle) * 40,
          y: elbow.y - Math.cos(forearmAngle) * 40
        };

        return {
          view: 'profile',
          head: { x: -5, y: -105 },
          neck: { x: -6, y: -80 },
          left_shoulder: { x: -8, y: -72 },
          right_shoulder: { x: 0, y: -72 },
          left_elbow: elbow,
          right_elbow: { x: elbow.x + 6, y: elbow.y },
          left_wrist: wrist,
          right_wrist: { x: wrist.x + 6, y: wrist.y },
          mid_hip: { x: -5, y: 0 },
          left_hip: { x: -8, y: 0 },
          right_hip: { x: -2, y: 0 },
          left_knee: { x: -8, y: 50 },
          right_knee: { x: -2, y: 50 },
          left_ankle: { x: -8, y: 100 },
          right_ankle: { x: -2, y: 100 },
          targetAngle: {
            joint: elbow,
            label: `${Math.round(forearmAngle * (180 / Math.PI))}°`,
            angleVal: forearmAngle * (180 / Math.PI)
          }
        };
      },
      phaseAt: function (t) {
        if (t < 0.44) return { text: 'EXTEND OVERHEAD (LOCK TRICEPS)', class: 'phase-concentric' };
        if (t < 0.56) return { text: 'TOP SQUEEZE', class: 'phase-hold' };
        return { text: 'CONTROLLED BEND BEHIND HEAD', class: 'phase-eccentric' };
      },
      cue: 'Keep upper arms still next to your ears. Move only your forearms.'
    }
  };

  /**
   * High-Performance 2D Canvas Kinematic Avatar Renderer
   */
  class DemoAvatarEngine {
    constructor(canvasId) {
      this.canvas = document.getElementById(canvasId);
      if (!this.canvas) {
        console.warn(`[FitQuest Demo]: Canvas element #${canvasId} not found.`);
        return;
      }

      this.ctx = this.canvas.getContext('2d');
      this.currentExerciseId = 2; // Default to Squat
      this.isPlaying = true;
      this.speedMultiplier = 1.0;
      this.animationFrameId = null;
      this.lastTimestamp = 0;
      this.progress = 0.0; // 0.0 to 1.0

      // DOM Hook Elements for dynamic feedback (scoped to container card if present)
      const card = this.canvas.closest('.demo-avatar-card');
      this.phaseBadgeEl = (card && card.querySelector('.demo-phase-pill')) || document.getElementById('demoPhaseBadge') || document.getElementById('learnDemoPhaseBadge');
      this.cueTextEl = (card && card.querySelector('.demo-cue-bar span')) || document.getElementById('demoCueText') || document.getElementById('learnDemoCueText');
      this.exTitleEl = (card && card.querySelector('.demo-title-group h3')) || document.getElementById('demoExerciseTitle') || document.getElementById('learnDemoTitle');
      this.muscleTagEl = (card && card.querySelector('[title="Target Muscle Group"] span')) || document.getElementById('demoMuscleTag') || document.getElementById('learnDemoMuscleTag');
      this.jointTagEl = (card && card.querySelector('[title="Primary Joint Action"] span')) || document.getElementById('demoJointTag') || document.getElementById('learnDemoJointTag');
      this.playPauseBtn = (card && card.querySelector('.demo-ctrl-btn')) || document.getElementById('demoPlayPauseBtn') || document.getElementById('learnDemoPlayPauseBtn');
      this.lowOverheadMode = false; // High-performance mode: turns off expensive canvas shadow/blur filters during active workouts

      this.initResizeObserver();
    }

    /**
     * Toggles low overhead canvas mode (disables expensive shadowBlur during active camera tracking)
     */
    setPerformanceMode(enabled = true) {
      this.lowOverheadMode = !!enabled;
    }

    initResizeObserver() {
      if (window.ResizeObserver && this.canvas.parentElement) {
        this.resizeObserver = new ResizeObserver(() => this.resizeCanvas());
        this.resizeObserver.observe(this.canvas.parentElement);
      } else {
        window.addEventListener('resize', () => this.resizeCanvas());
      }
      this.resizeCanvas();
    }

    resizeCanvas() {
      if (!this.canvas || !this.canvas.parentElement) return;
      const rect = this.canvas.parentElement.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const width = rect.width || 360;
      const height = rect.height || 280;

      this.canvas.width = width * dpr;
      this.canvas.height = height * dpr;
      this.canvas.style.width = `${width}px`;
      this.canvas.style.height = `${height}px`;

      this.ctx.setTransform(1, 0, 0, 1, 0, 0); // Reset transform
      this.ctx.scale(dpr, dpr);
      this.renderWidth = width;
      this.renderHeight = height;
    }

    loadExercise(exerciseId) {
      const id = parseInt(exerciseId, 10);
      if (!EXERCISE_DEMO_CATALOG[id]) {
        console.warn(`[FitQuest Demo]: Exercise ID ${id} not found in catalog. Falling back to ID 1.`);
        this.currentExerciseId = 1;
      } else {
        this.currentExerciseId = id;
      }

      this.progress = 0.0;
      const def = EXERCISE_DEMO_CATALOG[this.currentExerciseId];

      if (this.exTitleEl) this.exTitleEl.innerText = def.name;
      if (this.muscleTagEl) this.muscleTagEl.innerText = def.targetMuscles;
      if (this.jointTagEl) this.jointTagEl.innerText = def.primaryJoint;
      if (this.cueTextEl) this.cueTextEl.innerText = def.cue;

      this.start();
    }

    start() {
      this.isPlaying = true;
      this.lastTimestamp = performance.now();
      if (this.playPauseBtn) {
        this.playPauseBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
        this.playPauseBtn.setAttribute('title', 'Pause Demo');
      }

      if (!this.animationFrameId) {
        this.loop = this.loop.bind(this);
        this.animationFrameId = requestAnimationFrame(this.loop);
      }
    }

    pause() {
      this.isPlaying = false;
      if (this.playPauseBtn) {
        this.playPauseBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
        this.playPauseBtn.setAttribute('title', 'Play Demo');
      }
    }

    togglePlayPause() {
      if (this.isPlaying) {
        this.pause();
      } else {
        this.start();
      }
    }

    setSpeed(speed) {
      this.speedMultiplier = parseFloat(speed) || 1.0;
      const buttons = document.querySelectorAll('.demo-speed-btn');
      buttons.forEach((btn) => {
        if (parseFloat(btn.getAttribute('data-speed')) === this.speedMultiplier) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });
    }

    reset() {
      this.progress = 0.0;
      this.start();
    }

    stop() {
      this.isPlaying = false;
      if (this.animationFrameId) {
        cancelAnimationFrame(this.animationFrameId);
        this.animationFrameId = null;
      }
    }

    destroy() {
      this.stop();
      if (this.resizeObserver) {
        this.resizeObserver.disconnect();
      }
    }

    loop(timestamp) {
      if (!this.lastTimestamp) this.lastTimestamp = timestamp;
      const deltaSec = (timestamp - this.lastTimestamp) / 1000;
      this.lastTimestamp = timestamp;

      const def = EXERCISE_DEMO_CATALOG[this.currentExerciseId] || EXERCISE_DEMO_CATALOG[1];
      const cycleDuration = def.repDurationSec || 2.8;

      if (this.isPlaying && deltaSec > 0) {
        const step = (deltaSec * this.speedMultiplier) / cycleDuration;
        this.progress = (this.progress + step) % 1.0;
      }

      this.render(def, this.progress);

      if (this.isPlaying) {
        this.animationFrameId = requestAnimationFrame(this.loop);
      } else {
        this.animationFrameId = null;
      }
    }

    render(def, progress) {
      const ctx = this.ctx;
      const w = this.renderWidth || 360;
      const h = this.renderHeight || 280;

      ctx.clearRect(0, 0, w, h);

      // Background subtle gradient
      const bgGrad = ctx.createLinearGradient(0, 0, 0, h);
      bgGrad.addColorStop(0, '#0c1017');
      bgGrad.addColorStop(1, '#07090d');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);

      // Center stage & ground floor grid
      const centerX = w / 2;
      const centerY = h * 0.52;
      const scale = Math.min(w / 230, h / 240) * 0.95;

      this.drawEnvironmentGrid(ctx, w, h, centerX, centerY, scale);

      // Compute kinematic pose from definition
      const pose = def.getPose(progress);

      // Draw Avatar
      this.drawAvatar(ctx, pose, centerX, centerY, scale);

      // Update Phase Badge & Form Cue
      const phase = def.phaseAt(progress);
      if (this.phaseBadgeEl && phase) {
        this.phaseBadgeEl.innerText = phase.text;
        this.phaseBadgeEl.className = `demo-phase-pill ${phase.class || ''}`;
      }
    }

    drawEnvironmentGrid(ctx, w, h, cx, cy, scale) {
      ctx.save();
      const floorY = cy + 100 * scale;

      // Subtle floor line
      ctx.strokeStyle = 'rgba(204, 255, 0, 0.15)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(cx - 100 * scale, floorY);
      ctx.lineTo(cx + 100 * scale, floorY);
      ctx.stroke();

      // Floor glow ellipse
      const glowGrad = ctx.createRadialGradient(cx, floorY, 5, cx, floorY, 90 * scale);
      glowGrad.addColorStop(0, 'rgba(204, 255, 0, 0.10)');
      glowGrad.addColorStop(1, 'rgba(204, 255, 0, 0)');
      ctx.fillStyle = glowGrad;
      ctx.beginPath();
      ctx.ellipse(cx, floorY, 90 * scale, 16 * scale, 0, 0, TWO_PI);
      ctx.fill();

      ctx.restore();
    }

    drawAvatar(ctx, pose, cx, cy, scale) {
      ctx.save();

      const toScreen = (pt) => ({
        x: cx + pt.x * scale,
        y: cy + pt.y * scale
      });

      // Neon Palette
      const boneColorPrimary = '#ccff00';     // Bright FitQuest Lime
      const boneColorSecondary = '#90b800';   // Depth/Far Limb Lime
      const jointGlowColor = '#ccff00';
      const torsoGlowColor = '#00f0ff';       // Cyan Core
      const headColor = '#ffffff';

      // 1. Draw Torso Core Spine
      const neck = toScreen(pose.neck);
      const hip = toScreen(pose.mid_hip);

      ctx.strokeStyle = torsoGlowColor;
      ctx.lineWidth = 5.5 * scale;
      ctx.lineCap = 'round';
      if (!this.lowOverheadMode) {
        ctx.shadowColor = 'rgba(0, 240, 255, 0.6)';
        ctx.shadowBlur = 12;
      } else {
        ctx.shadowBlur = 0;
      }
      ctx.beginPath();
      ctx.moveTo(neck.x, neck.y);
      ctx.lineTo(hip.x, hip.y);
      ctx.stroke();
      ctx.shadowBlur = 0; // reset

      // 2. Draw Limbs (Far side limbs first for correct z-depth)
      const drawBone = (p1, p2, color, width) => {
        const a = toScreen(p1);
        const b = toScreen(p2);
        ctx.strokeStyle = color;
        ctx.lineWidth = width * scale;
        ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      };

      // Far Leg (Right)
      if (pose.right_hip && pose.right_knee) drawBone(pose.right_hip, pose.right_knee, boneColorSecondary, 4.0);
      if (pose.right_knee && pose.right_ankle) drawBone(pose.right_knee, pose.right_ankle, boneColorSecondary, 3.5);

      // Far Arm (Right)
      if (pose.right_shoulder && pose.right_elbow) drawBone(pose.right_shoulder, pose.right_elbow, boneColorSecondary, 3.5);
      if (pose.right_elbow && pose.right_wrist) drawBone(pose.right_elbow, pose.right_wrist, boneColorSecondary, 3.0);

      // Near Leg (Left)
      if (pose.left_hip && pose.left_knee) drawBone(pose.left_hip, pose.left_knee, boneColorPrimary, 4.8);
      if (pose.left_knee && pose.left_ankle) drawBone(pose.left_knee, pose.left_ankle, boneColorPrimary, 4.2);

      // Near Arm (Left)
      if (pose.left_shoulder && pose.left_elbow) drawBone(pose.left_shoulder, pose.left_elbow, boneColorPrimary, 4.2);
      if (pose.left_elbow && pose.left_wrist) drawBone(pose.left_elbow, pose.left_wrist, boneColorPrimary, 3.8);

      // Shoulder and Pelvis Bars (Frontal View)
      if (pose.view === 'frontal') {
        if (pose.left_shoulder && pose.right_shoulder) drawBone(pose.left_shoulder, pose.right_shoulder, '#ffffff', 4.0);
        if (pose.left_hip && pose.right_hip) drawBone(pose.left_hip, pose.right_hip, '#ffffff', 4.0);
      }

      // 3. Draw Joints (Neon Glow Spheres)
      const drawJoint = (pt, r = 4.5, glow = true) => {
        if (!pt) return;
        const s = toScreen(pt);
        ctx.save();
        if (glow && !this.lowOverheadMode) {
          ctx.shadowColor = jointGlowColor;
          ctx.shadowBlur = 10;
        } else {
          ctx.shadowBlur = 0;
        }
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(s.x, s.y, r * scale, 0, TWO_PI);
        ctx.fill();

        ctx.strokeStyle = jointGlowColor;
        ctx.lineWidth = 1.8 * scale;
        ctx.beginPath();
        ctx.arc(s.x, s.y, (r + 2) * scale, 0, TWO_PI);
        ctx.stroke();
        ctx.restore();
      };

      drawJoint(pose.left_shoulder, 4.2);
      drawJoint(pose.left_elbow, 3.8);
      drawJoint(pose.left_wrist, 3.4);
      drawJoint(pose.left_hip, 4.5);
      drawJoint(pose.left_knee, 4.2);
      drawJoint(pose.left_ankle, 3.8);

      // 4. Draw Head / Visor
      const head = toScreen(pose.head);
      ctx.save();
      if (!this.lowOverheadMode) {
        ctx.shadowColor = 'rgba(204, 255, 0, 0.7)';
        ctx.shadowBlur = 14;
      } else {
        ctx.shadowBlur = 0;
      }
      ctx.fillStyle = headColor;
      ctx.beginPath();
      ctx.arc(head.x, head.y, 9.5 * scale, 0, TWO_PI);
      ctx.fill();

      // Cyberpunk Visor Strip
      ctx.fillStyle = '#0c1017';
      ctx.beginPath();
      ctx.roundRect(head.x - 7 * scale, head.y - 3 * scale, 14 * scale, 5 * scale, 2 * scale);
      ctx.fill();

      ctx.fillStyle = '#00f0ff';
      ctx.beginPath();
      ctx.roundRect(head.x - 5 * scale, head.y - 2 * scale, 10 * scale, 3 * scale, 1.5 * scale);
      ctx.fill();
      ctx.restore();

      // 5. Draw Primary Angle Arc Indicator
      if (pose.targetAngle && pose.targetAngle.joint) {
        const jointPos = toScreen(pose.targetAngle.joint);
        ctx.save();
        ctx.fillStyle = '#ccff00';
        ctx.font = `bold ${Math.max(11, Math.round(12 * scale))}px Outfit, Inter, sans-serif`;
        if (!this.lowOverheadMode) {
          ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
          ctx.shadowBlur = 6;
        } else {
          ctx.shadowBlur = 0;
        }
        ctx.fillText(pose.targetAngle.label, jointPos.x + 10 * scale, jointPos.y - 8 * scale);
        ctx.restore();
      }

      ctx.restore();
    }
  }

  // Expose global instance & catalog
  window.EXERCISE_DEMO_CATALOG = EXERCISE_DEMO_CATALOG;
  window.DemoAvatarEngine = DemoAvatarEngine;

})(window);
