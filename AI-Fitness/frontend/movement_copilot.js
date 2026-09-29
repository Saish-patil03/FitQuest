/**
 * FitQuest Human Movement Intelligence Engine — Phase 5: MOVEMENT COPILOT™
 * Real-Time Biomechanical Degradation Detection, Context-Aware Coaching, & Closed-Loop Recovery HUD.
 */

// ---------------------------------------------------------------------------
// Global Copilot Client State
// ---------------------------------------------------------------------------
let copilotSessionId = null;
let copilotExerciseId = "1";
let copilotExerciseName = "Exercise";
let copilotDnaLimiter = null;
let copilotAdaptiveTempo = null;
let isCopilotActive = false;
let lastCopilotFrameTimestamp = 0;
const COPILOT_THROTTLE_MS = 300; // Send telemetry every 300ms for stable low-latency coaching

let copilotEventTimeline = [];

/**
 * Initializes Copilot engine listeners and hooks
 */
function initializeCopilot() {
  console.log('[FitQuest Copilot]: Initialized Movement Copilot™ Engine.');
}

/**
 * Starts a new active Copilot session
 */
function startCopilot(sessionId, exercise, options = {}) {
  copilotSessionId = sessionId || `copilot_${Date.now()}`;
  copilotExerciseId = String(exercise?.id || "1");
  copilotExerciseName = exercise?.name || "Exercise";
  copilotDnaLimiter = options.dnaLimiter || null;
  copilotAdaptiveTempo = options.adaptiveTempo || null;
  isCopilotActive = true;
  lastCopilotFrameTimestamp = 0;
  copilotEventTimeline = [];

  const copilotCard = document.getElementById('movementCopilotCard');
  if (copilotCard) {
    copilotCard.style.display = 'flex';
  }

  renderCopilotHUD({
    status: 'IDLE',
    exercise: copilotExerciseName,
    dimension_label: 'Overall Movement',
    score: 80.0,
    message: 'Calibrating camera & pose sensors...',
    coaching_cue: 'Position yourself in full view to begin.',
    movement_phase: 'PREPARE',
    current_metrics: {
      range_of_motion: 80.0,
      movement_stability: 80.0,
      tempo_control: 80.0,
      repetition_consistency: 80.0
    }
  });
}

/**
 * Feeds live frame telemetry into Copilot Engine (throttled)
 */
async function processCopilotTelemetry(telemetry) {
  if (!isCopilotActive || !copilotSessionId || !telemetry) return;

  const now = Date.now();
  if ((now - lastCopilotFrameTimestamp) < COPILOT_THROTTLE_MS) {
    return;
  }
  lastCopilotFrameTimestamp = now;

  const token = typeof getAuthToken === 'function' ? getAuthToken() : (localStorage.getItem('fitquest_token') || localStorage.getItem('token'));
  if (!token) return;

  try {
    const payload = {
      session_id: copilotSessionId,
      exercise_id: copilotExerciseId,
      rep_count: telemetry.rep_count || 0,
      form_score: telemetry.form_score || 0.0,
      state: telemetry.state || 'START',
      primary_angle: telemetry.primary_angle || null,
      left_angle: telemetry.left_angle || null,
      right_angle: telemetry.right_angle || null,
      torso_angle: telemetry.torso_angle || null,
      valid: telemetry.valid !== false,
      feedback_code: telemetry.feedback_code || 'GOOD_FORM',
      dna_primary_limiter: copilotDnaLimiter,
      adaptive_tempo_target: copilotAdaptiveTempo
    };

    const res = await fetch(`${API_BASE}/movement-intelligence/copilot/frame`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const copilotData = await res.json();
      renderCopilotHUD(copilotData);
    }
  } catch (err) {
    console.warn('[FitQuest Copilot]: Telemetry ingestion warning:', err);
  }
}

/**
 * Renders the real-time Copilot HUD Card
 */
function renderCopilotHUD(data) {
  if (!data) return;

  // 1. Status Pill & Badge
  const statusBadge = document.getElementById('copilotStatusBadge');
  const statusText = document.getElementById('copilotStatusText');
  if (statusBadge && statusText) {
    statusBadge.className = 'copilot-status-badge';
    if (data.status === 'RECOVERED') {
      statusBadge.classList.add('status-recovered');
      statusText.innerHTML = '<i class="fa-solid fa-check-circle"></i> RECOVERED';
    } else if (data.status === 'WARNING' || data.severity === 'WARNING') {
      statusBadge.classList.add('status-warning');
      statusText.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> DEGRADATION';
    } else if (data.status === 'CRITICAL' || data.severity === 'CRITICAL') {
      statusBadge.classList.add('status-critical');
      statusText.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> CRITICAL FORM';
    } else {
      statusBadge.classList.add('status-monitoring');
      statusText.innerHTML = '<span class="copilot-pulse-dot"></span> MONITORING';
    }
  }

  // 2. Primary Dimension Name & Score
  const dimNameEl = document.getElementById('copilotDimName');
  const dimScoreEl = document.getElementById('copilotDimScore');
  const dimBarEl = document.getElementById('copilotDimBar');
  const deltaBadgeEl = document.getElementById('copilotDeltaBadge');

  if (dimNameEl) dimNameEl.innerText = data.dimension_label || 'Movement Stability';
  if (dimScoreEl) dimScoreEl.innerText = `${Math.round(data.score || 80)} / 100`;
  if (dimBarEl) dimBarEl.style.width = `${Math.min(100, Math.max(10, data.score || 80))}%`;

  if (deltaBadgeEl) {
    if (data.delta && Math.abs(data.delta) >= 1.0) {
      deltaBadgeEl.style.display = 'inline-flex';
      const sign = data.delta > 0 ? '+' : '';
      deltaBadgeEl.innerText = `${sign}${data.delta.toFixed(1)} pts`;
      deltaBadgeEl.className = data.delta > 0 ? 'copilot-delta-pill delta-pos' : 'copilot-delta-pill delta-neg';
    } else {
      deltaBadgeEl.style.display = 'none';
    }
  }

  // 3. AI Coach Cue & Phase Pill
  const cueEl = document.getElementById('copilotCueText');
  const phasePill = document.getElementById('copilotPhasePill');

  if (cueEl) cueEl.innerText = data.coaching_cue || 'Maintain steady cadence and control.';
  if (phasePill) {
    phasePill.innerText = data.movement_phase || 'STEADY';
  }

  // 4. Mini Metric Progress Bars
  const metrics = data.current_metrics || {};
  updateMiniMetric('copilotMiniStab', metrics.movement_stability || 80);
  updateMiniMetric('copilotMiniTempo', metrics.tempo_control || 80);
  updateMiniMetric('copilotMiniRom', metrics.range_of_motion || 80);
  updateMiniMetric('copilotMiniCons', metrics.repetition_consistency || 80);

  // 5. Timeline Events
  if (data.recent_events && data.recent_events.length > 0) {
    renderCopilotTimeline(data.recent_events);
  }
}

function updateMiniMetric(elementId, value) {
  const bar = document.getElementById(`${elementId}Bar`);
  const val = document.getElementById(`${elementId}Val`);
  const v = Math.round(value || 80);
  if (bar) bar.style.width = `${Math.min(100, Math.max(5, v))}%`;
  if (val) val.innerText = `${v}`;
}

function renderCopilotTimeline(events) {
  const container = document.getElementById('copilotTimelineStream');
  if (!container || !events) return;

  container.innerHTML = events.slice(-3).map(ev => {
    let icon = '<i class="fa-solid fa-circle-info" style="color: var(--accent-cyan);"></i>';
    if (ev.type && ev.type.includes('RECOVERY')) {
      icon = '<i class="fa-solid fa-circle-check" style="color: var(--status-success);"></i>';
    } else if (ev.type && ev.type.includes('CRITICAL')) {
      icon = '<i class="fa-solid fa-circle-exclamation" style="color: #ef4444;"></i>';
    } else if (ev.type && ev.type.includes('INTERVENTION')) {
      icon = '<i class="fa-solid fa-triangle-exclamation" style="color: var(--status-warning);"></i>';
    }
    return `
      <div class="copilot-timeline-item">
        <span class="copilot-tl-rep">REP ${String(ev.rep || 0).padStart(2, '0')}</span>
        <span class="copilot-tl-icon">${icon}</span>
        <span class="copilot-tl-msg">${escapeHTML(ev.message || '')}</span>
      </div>
    `;
  }).join('');
}

/**
 * Resets Copilot on exercise transition / new set
 */
async function resetCopilot(newExercise) {
  if (newExercise) {
    copilotExerciseId = String(newExercise.id || "1");
    copilotExerciseName = newExercise.name || "Exercise";
  }
  const token = typeof getAuthToken === 'function' ? getAuthToken() : (localStorage.getItem('fitquest_token') || localStorage.getItem('token'));
  if (token && copilotSessionId) {
    try {
      await fetch(`${API_BASE}/movement-intelligence/copilot/reset`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          session_id: copilotSessionId,
          exercise_id: copilotExerciseId
        })
      });
    } catch (e) {
      console.warn('[FitQuest Copilot]: Reset error:', e);
    }
  }
}

/**
 * Stops Copilot session on workout completion
 */
function stopCopilot() {
  isCopilotActive = false;
  const copilotCard = document.getElementById('movementCopilotCard');
  if (copilotCard) {
    copilotCard.style.display = 'none';
  }
}

/**
 * Fetches and renders Post-Workout Copilot Session Summary
 */
async function loadPostWorkoutCopilotSummary(sessionId) {
  const targetSessionId = sessionId || copilotSessionId;
  const summaryCard = document.getElementById('resMovementCopilotCard');
  if (!summaryCard || !targetSessionId) return;

  const token = typeof getAuthToken === 'function' ? getAuthToken() : (localStorage.getItem('fitquest_token') || localStorage.getItem('token'));
  if (!token) return;

  try {
    const res = await fetch(`${API_BASE}/movement-intelligence/copilot/summary/${targetSessionId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json'
      }
    });

    if (res.ok) {
      const summary = await res.json();
      renderCopilotSummaryCard(summary);
    }
  } catch (err) {
    console.warn('[FitQuest Copilot]: Failed to load post-workout summary:', err);
  }
}

/**
 * Renders Post-Workout Intelligence Summary Card
 */
function renderCopilotSummaryCard(summary) {
  const summaryCard = document.getElementById('resMovementCopilotCard');
  if (!summaryCard || !summary) return;

  summaryCard.style.display = 'flex';

  const intEl = document.getElementById('resCopilotInterventions');
  const corEl = document.getElementById('resCopilotCorrections');
  const rateEl = document.getElementById('resCopilotRecoveryRate');
  const bigEl = document.getElementById('resCopilotBiggestRecovery');
  const freqEl = document.getElementById('resCopilotMostFreqLimiter');
  const verEl = document.getElementById('resCopilotVerdict');

  if (intEl) intEl.innerText = summary.total_interventions ?? 0;
  if (corEl) corEl.innerText = summary.successful_corrections ?? 0;
  if (rateEl) rateEl.innerText = `${(summary.recovery_rate_pct ?? 100).toFixed(0)}%`;

  if (bigEl) {
    if (summary.biggest_recovery) {
      bigEl.innerText = `${summary.biggest_recovery.label} (+${summary.biggest_recovery.gain_pts} pts)`;
    } else {
      bigEl.innerText = 'Optimal Consistency';
    }
  }

  if (freqEl) {
    if (summary.most_frequent_limiter) {
      freqEl.innerText = `${summary.most_frequent_limiter.label} (${summary.most_frequent_limiter.count}x)`;
    } else {
      freqEl.innerText = 'None (Stable)';
    }
  }

  if (verEl) {
    verEl.innerText = summary.verdict || 'Flawless execution throughout your workout set.';
  }
}

// Auto-initialize on load
document.addEventListener('DOMContentLoaded', () => {
  initializeCopilot();
});
