/**
 * FitQuest — Movement DNA™ & AI Performance Intelligence (Phase 4)
 * Hardware-accelerated Canvas 5-Axis Radar, Multi-Metric Spline Timeline,
 * Deterministic Dimension Breakdown, Explainable AI Report, and Adaptive Binding.
 * 
 * Includes layout-stability lifecycle guards and container-locked canvas sizing.
 */

let activeDNAExerciseId = null;
let currentMovementDNAData = null;
let activeDNATimelineFilter = 'all';
let isDNALoading = false;
let dnaResizeTimer = null;

const FALLBACK_DNA_EXERCISES = [
  { id: 1, name: 'Bicep Curl' },
  { id: 2, name: 'Squat' },
  { id: 3, name: 'Push-up' },
  { id: 4, name: 'Lunges' },
  { id: 5, name: 'Shoulder Press' },
  { id: 6, name: 'Jumping Jacks' },
  { id: 7, name: 'High Knees' },
  { id: 8, name: 'Mountain Climbers' },
  { id: 9, name: 'Plank' },
  { id: 10, name: 'Glute Bridge' },
  { id: 11, name: 'Sit-ups' },
  { id: 12, name: 'Crunches' },
  { id: 13, name: 'Leg Raises' },
  { id: 14, name: 'Russian Twists' },
  { id: 15, name: 'Bicycle Crunches' },
  { id: 16, name: 'Side Lunges' },
  { id: 17, name: 'Calf Raises' },
  { id: 18, name: 'Front Raises' },
  { id: 19, name: 'Lateral Raises' },
  { id: 20, name: 'Tricep Extensions' }
];

function getMovementDnaApiUrl() {
  const base = (window.getFitQuestApiBase ? window.getFitQuestApiBase() : (window.API_BASE || 'https://saish-patil03--fitquest-backend-serve.modal.run/api/v1'));
  return `${base}/movement-intelligence/dna`;
}

/**
 * Loads Movement DNA data for the authenticated user and optional exercise filter.
 */
async function loadMovementDNA(exerciseId = null) {
  const container = document.getElementById('movementDnaView');
  if (!container) return;

  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('token') || localStorage.getItem('fitquest_token');

  // Populate exercise filter dropdown
  await populateDNAExerciseSelector();

  if (isDNALoading) return;
  isDNALoading = true;

  try {
    let url = getMovementDnaApiUrl();
    if (exerciseId) {
      url += `?exercise_id=${exerciseId}`;
    }

    const headers = { 'Accept': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3500);

    const res = await fetch(url, { headers, signal: controller.signal });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      currentMovementDNAData = data;
      activeDNAExerciseId = exerciseId;

      requestAnimationFrame(() => {
        renderMovementDNADashboard(data);
      });
      return;
    }
    throw new Error(`Server returned HTTP ${res.status}`);

  } catch (err) {
    console.warn('[FitQuest DNA Warning]: Backend request unfulfilled, utilizing local movement telemetry:', err);
    const clientData = generateClientMovementDNA(exerciseId);
    currentMovementDNAData = clientData;
    activeDNAExerciseId = exerciseId;
    requestAnimationFrame(() => {
      renderMovementDNADashboard(clientData);
    });
  } finally {
    isDNALoading = false;
  }
}

function generateClientMovementDNA(exerciseId = null) {
  let localWorkouts = [];
  try {
    const raw = localStorage.getItem('fitquest_local_workouts');
    if (raw) localWorkouts = JSON.parse(raw);
  } catch (e) {}

  if (exerciseId) {
    localWorkouts = localWorkouts.filter(w => String(w.exercise_id || w.exerciseId || '') === String(exerciseId));
  }

  const nSessions = localWorkouts.length;

  // Zero-sessions honest empty state
  if (nSessions === 0) {
    return {
      overall_score: null,
      total_sessions_analyzed: 0,
      confidence: 'Baseline',
      confidence_reason: 'No recorded workout history. Complete your first workout to establish your Movement DNA.',
      strongest_dimension: { key: 'none', label: 'None Yet', score: null, status: 'N/A' },
      strongest_trait: { key: 'none', label: 'None Yet', score: null, status: 'N/A' },
      primary_limiter: {
        key: 'none',
        label: 'None Yet',
        score: null,
        status: 'N/A',
        why_it_matters: 'Movement DNA is established after your first workout session.',
        ai_response: 'Complete any workout with camera tracking to begin automated movement decoding.'
      },
      needs_attention: { key: 'none', label: 'None Yet', score: null, status: 'N/A' },
      secondary_limiter: { key: 'none', label: 'None Yet', score: null, status: 'N/A' },
      trend: { direction: 'INSUFFICIENT DATA', delta: 0.0, pct_change: 0.0, velocity_per_session: 0.0 },
      dimensions: {
        range_of_motion: { key: 'range_of_motion', label: 'Range of Motion', score: null, baseline: null, recent: null, overall_avg: null, delta: 0, pct_change: 0, velocity: 0, status: 'N/A', trend: 'INSUFFICIENT DATA', interpretation: 'No recorded movement data. Complete your first workout to establish your Movement DNA.' },
        movement_stability: { key: 'movement_stability', label: 'Movement Stability', score: null, baseline: null, recent: null, overall_avg: null, delta: 0, pct_change: 0, velocity: 0, status: 'N/A', trend: 'INSUFFICIENT DATA', interpretation: 'No recorded movement data. Complete your first workout to establish your Movement DNA.' },
        tempo_control: { key: 'tempo_control', label: 'Tempo Control', score: null, baseline: null, recent: null, overall_avg: null, delta: 0, pct_change: 0, velocity: 0, status: 'N/A', trend: 'INSUFFICIENT DATA', interpretation: 'No recorded movement data. Complete your first workout to establish your Movement DNA.' },
        repetition_consistency: { key: 'repetition_consistency', label: 'Repetition Consistency', score: null, baseline: null, recent: null, overall_avg: null, delta: 0, pct_change: 0, velocity: 0, status: 'N/A', trend: 'INSUFFICIENT DATA', interpretation: 'No recorded movement data. Complete your first workout to establish your Movement DNA.' },
        bilateral_symmetry: { key: 'bilateral_symmetry', label: 'Bilateral Symmetry', score: null, baseline: null, recent: null, overall_avg: null, delta: 0, pct_change: 0, velocity: 0, status: 'N/A', trend: 'INSUFFICIENT DATA', interpretation: 'No recorded movement data. Complete your first workout to establish your Movement DNA.' }
      },
      timeline: [],
      ai_report: {
        what_you_do_well: 'Complete your first workout to reveal your movement strengths.',
        what_is_limiting_you: 'No movement limiters detected yet.',
        what_changed: 'No workout history recorded yet.',
        what_fitquest_recommends: 'Start any exercise session to calibrate your personal Movement DNA vectors.',
        next_step: 'Launch a workout session with your camera enabled to begin automated movement analysis.'
      },
      adaptive_action: {
        endpoint: '/api/v1/adaptive-training/generate',
        primary_focus: 'general',
        recommended_title: 'Initial Baseline Calibration'
      }
    };
  }

  // When sessions exist (> 0):
  const scores = localWorkouts.map(w => parseFloat(w.form_score || w.formScore || 0)).filter(s => !isNaN(s) && s > 0);
  const avgForm = scores.length > 0
    ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length * 10) / 10
    : 75.0;

  const baseStability = Math.min(95, Math.max(50, Math.round(avgForm + 2)));
  const baseROM = Math.min(95, Math.max(50, Math.round(avgForm - 2)));
  const baseTempo = Math.min(95, Math.max(50, Math.round(avgForm - 6)));
  const baseConsistency = Math.min(95, Math.max(50, Math.round(avgForm + 4)));
  const baseSymmetry = Math.min(95, Math.max(50, Math.round(avgForm - 1)));

  const dimLabels = {
    range_of_motion: 'Range of Motion',
    movement_stability: 'Movement Stability',
    tempo_control: 'Tempo Control',
    repetition_consistency: 'Repetition Consistency',
    bilateral_symmetry: 'Bilateral Symmetry'
  };

  const dimScores = {
    range_of_motion: baseROM,
    movement_stability: baseStability,
    tempo_control: baseTempo,
    repetition_consistency: baseConsistency,
    bilateral_symmetry: baseSymmetry
  };

  const dimensions = {};
  for (const [k, score] of Object.entries(dimScores)) {
    dimensions[k] = {
      key: k,
      label: dimLabels[k],
      score: score,
      baseline: score,
      recent: score,
      overall_avg: score,
      delta: 0.0,
      pct_change: 0.0,
      velocity: 0.0,
      status: score >= 80 ? 'STRONG' : (score >= 65 ? 'ADEQUATE' : 'NEEDS ATTENTION'),
      trend: 'STABLE',
      interpretation: `Baseline ${dimLabels[k].toLowerCase()} calibrated. Complete additional workout sets to track longitudinal adaptation.`
    };
  }

  const timeline = localWorkouts.slice(-6).map((w, idx) => ({
    session_index: idx + 1,
    overall_quality: parseFloat(w.form_score || w.formScore || 0),
    date: w.timestamp ? new Date(w.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : `S${idx + 1}`
  }));

  const intOverall = Math.round(avgForm);

  return {
    overall_score: intOverall,
    total_sessions_analyzed: nSessions,
    confidence: nSessions >= 3 ? 'High' : (nSessions >= 1 ? 'Medium' : 'Baseline'),
    confidence_reason: `Calibrated from ${nSessions} workout ${nSessions === 1 ? 'session' : 'sessions'}.`,
    strongest_dimension: { key: 'repetition_consistency', label: 'Repetition Consistency', score: baseConsistency, status: 'STRONG' },
    strongest_trait: { key: 'repetition_consistency', label: 'Repetition Consistency', score: baseConsistency, status: 'STRONG' },
    primary_limiter: {
      key: 'tempo_control',
      label: 'Tempo Control',
      score: baseTempo,
      status: 'ADEQUATE',
      why_it_matters: 'Controlling the eccentric (lowering) phase maximizes motor unit recruitment and joint safety.',
      ai_response: 'Pace your descent with a steady 2-1-2 cadence during active repetitions.'
    },
    needs_attention: {
      key: 'tempo_control',
      label: 'Tempo Control',
      score: baseTempo,
      status: 'ADEQUATE'
    },
    secondary_limiter: { key: 'movement_stability', label: 'Movement Stability', score: baseStability, status: 'ADEQUATE' },
    trend: { direction: 'STABLE', delta: 0.0, pct_change: 0.0, velocity_per_session: 0.0 },
    dimensions: dimensions,
    timeline: timeline,
    ai_report: {
      what_you_do_well: 'Your Repetition Consistency is your highest movement characteristic, showing steady execution rhythm.',
      what_is_limiting_you: `Tempo Control (${baseTempo}/100) represents your best opportunity for mechanical optimization.`,
      what_changed: 'Biomechanical signature actively calibrated across your movement vectors.',
      what_fitquest_recommends: 'Incorporate controlled tempo pacing on eccentric phases to strengthen tendon resilience.',
      next_step: 'Launch any workout session to update your live Movement DNA vectors.'
    },
    adaptive_action: {
      endpoint: '/api/v1/adaptive-training/generate',
      primary_focus: 'tempo_control',
      recommended_title: 'Adaptive Session: Tempo Control Calibration'
    }
  };
}

/**
 * Populates the Exercise Selector dropdown with all available exercises.
 */
async function populateDNAExerciseSelector() {
  const selector = document.getElementById('dnaExerciseSelect');
  if (!selector) return;

  const catalogue = (typeof BUILTIN_EXERCISE_CATALOGUE !== 'undefined' && Array.isArray(BUILTIN_EXERCISE_CATALOGUE))
    ? BUILTIN_EXERCISE_CATALOGUE
    : FALLBACK_DNA_EXERCISES;

  // Immediately ensure options exist with >1 choices
  if (selector.children.length <= 1) {
    const curVal = selector.value || (activeDNAExerciseId ? String(activeDNAExerciseId) : '');
    selector.innerHTML = '<option value="">All Exercises (Overall Movement DNA)</option>' +
      catalogue.map(ex => `<option value="${ex.id}" ${String(ex.id) === String(curVal) ? 'selected' : ''}>${escapeHTML(ex.name)}</option>`).join('');
  }

  try {
    const base = (window.getFitQuestApiBase ? window.getFitQuestApiBase() : (window.API_BASE || 'https://saish-patil03--fitquest-backend-serve.modal.run/api/v1'));
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);

    const res = await fetch(`${base}/exercises`, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (res.ok) {
      const exercises = await res.json();
      if (Array.isArray(exercises) && exercises.length > 0) {
        const curVal = selector.value || (activeDNAExerciseId ? String(activeDNAExerciseId) : '');
        selector.innerHTML = '<option value="">All Exercises (Overall Movement DNA)</option>' +
          exercises.map(ex => `<option value="${ex.id}" ${String(ex.id) === String(curVal) ? 'selected' : ''}>${escapeHTML(ex.name)}</option>`).join('');
      }
    }
  } catch (e) {
    console.warn('[FitQuest DNA]: Using local exercise catalogue for DNA filter:', e);
  }
}

/**
 * Refreshes canvas visualizations using current data (e.g. after tab switch or window resize)
 */
function refreshMovementDNACanvases() {
  if (!currentMovementDNAData) return;
  const view = document.getElementById('movementDnaView');
  if (!view || !view.classList.contains('active')) return;

  renderMovementDNARadar('dnaRadarCanvas', currentMovementDNAData.dimensions);
  renderMovementDNATimeline('dnaTimelineCanvas', currentMovementDNAData.timeline, activeDNATimelineFilter);
}

/**
 * Debounced resize handler to ensure radar and timeline adapt cleanly
 */
function handleMovementDNAResize() {
  if (dnaResizeTimer) clearTimeout(dnaResizeTimer);
  dnaResizeTimer = setTimeout(() => {
    refreshMovementDNACanvases();
  }, 100);
}

if (typeof window !== 'undefined' && !window._dnaResizeAttached) {
  window.addEventListener('resize', handleMovementDNAResize);
  window._dnaResizeAttached = true;
}

/**
 * Renders all components in the Movement DNA view.
 */
function renderMovementDNADashboard(data) {
  if (!data) return;

  const nSessions = (typeof data.total_sessions_analyzed === 'number') ? data.total_sessions_analyzed : 0;

  // 1. Overall Score & Confidence
  const overallScoreEl = document.getElementById('dnaOverallScore');
  if (overallScoreEl) {
    const rawVal = data.overall_score;
    overallScoreEl.innerText = (rawVal !== undefined && rawVal !== null && nSessions > 0)
      ? String(Math.round(Number(rawVal)))
      : '--';
  }

  const sessionCountEl = document.getElementById('dnaSessionsCount');
  if (sessionCountEl) {
    sessionCountEl.innerText = `${nSessions} ${nSessions === 1 ? 'Session' : 'Sessions'}`;
  }

  const confPill = document.getElementById('dnaConfidencePill');
  if (confPill) {
    if (nSessions === 0) {
      confPill.className = 'dna-conf-pill conf-baseline';
      confPill.innerHTML = '<i class="fa-solid fa-shield"></i> BASELINE NEEDED';
    } else {
      const conf = (data.confidence || 'medium').toLowerCase();
      confPill.className = `dna-conf-pill conf-${conf}`;
      confPill.innerHTML = `<i class="fa-solid fa-shield-halved"></i> ${(data.confidence || 'HIGH').toUpperCase()} CONFIDENCE`;
    }
  }

  const confReasonEl = document.getElementById('dnaConfidenceReason');
  if (confReasonEl) {
    confReasonEl.innerText = data.confidence_reason || (nSessions > 0 ? 'Calibrated from workout movement telemetry.' : 'Complete your first workout to decode your personal Movement DNA profile.');
  }

  // 2. Strongest Trait
  const strongestEl = document.getElementById('dnaStrongestTrait');
  const sDim = data.strongest_dimension || data.strongest_trait || {};
  if (strongestEl) {
    strongestEl.innerText = (nSessions > 0 && sDim.label && sDim.label !== 'None Yet') ? sDim.label : '--';
  }
  const strongestScoreEl = document.getElementById('dnaStrongestScore');
  if (strongestScoreEl) {
    const sScore = (typeof sDim.score === 'number' && sDim.score !== null && nSessions > 0) ? Math.round(sDim.score) : null;
    strongestScoreEl.innerText = sScore !== null ? `${sScore} / 100` : '-- / 100';
  }

  // 3. Needs Attention (Mapped to Primary Limiter)
  const limiterEl = document.getElementById('dnaPrimaryLimiter');
  const pLimiter = data.primary_limiter || data.needs_attention || {};
  if (limiterEl) {
    limiterEl.innerText = (nSessions > 0 && pLimiter.label && pLimiter.label !== 'None Yet') ? pLimiter.label : '--';
  }
  const limiterScoreEl = document.getElementById('dnaLimiterScore');
  if (limiterScoreEl) {
    const lScore = (typeof pLimiter.score === 'number' && pLimiter.score !== null && nSessions > 0) ? Math.round(pLimiter.score) : null;
    limiterScoreEl.innerText = lScore !== null ? `${lScore} / 100` : '-- / 100';
  }

  // 4. Trend Direction & Velocity
  const trendBadge = document.getElementById('dnaTrendBadge');
  if (trendBadge) {
    if (nSessions === 0 || !data.trend || data.trend.direction === 'INSUFFICIENT DATA') {
      trendBadge.className = 'dna-trend-pill trend-neutral';
      trendBadge.innerHTML = '<i class="fa-solid fa-minus"></i> INSUFFICIENT DATA';
    } else {
      trendBadge.className = `dna-trend-pill trend-${data.trend.direction.toLowerCase()}`;
      let tIcon = '<i class="fa-solid fa-minus"></i>';
      if (data.trend.direction === 'IMPROVING') tIcon = '<i class="fa-solid fa-arrow-trend-up"></i>';
      else if (data.trend.direction === 'DECLINING') tIcon = '<i class="fa-solid fa-arrow-trend-down"></i>';
      trendBadge.innerHTML = `${tIcon} ${data.trend.direction}`;
    }
  }

  const trendDeltaEl = document.getElementById('dnaTrendDelta');
  if (trendDeltaEl) {
    if (nSessions === 0 || !data.trend || data.trend.direction === 'INSUFFICIENT DATA') {
      trendDeltaEl.innerText = '--';
    } else {
      const sign = data.trend.delta >= 0 ? '+' : '';
      trendDeltaEl.innerText = `${sign}${data.trend.delta.toFixed(1)} pts (${sign}${data.trend.pct_change.toFixed(1)}%)`;
    }
  }

  const velocityEl = document.getElementById('dnaVelocityText');
  if (velocityEl) {
    if (nSessions === 0 || !data.trend) {
      velocityEl.innerText = 'Velocity: --';
    } else {
      velocityEl.innerText = `Velocity: ${data.trend.velocity_per_session >= 0 ? '+' : ''}${data.trend.velocity_per_session.toFixed(2)} pts/session`;
    }
  }

  // 5. Draw 5-Axis Native HTML5 Canvas Movement DNA Radar
  renderMovementDNARadar('dnaRadarCanvas', data.dimensions);

  // 6. Render 5 Dimension Cards
  renderDNADimensionCards(data.dimensions);

  // 7. Render AI Movement Limiter & "Why This Matters" Card
  renderDNALimiterCard(data.primary_limiter, data.secondary_limiter);

  // 8. Render Multi-Metric Timeline Spline Canvas
  renderMovementDNATimeline('dnaTimelineCanvas', data.timeline || [], activeDNATimelineFilter);

  // 9. Render Explainable AI Movement Report
  renderDNAAIReport(data.ai_report);
}

/**
 * Draws the 5-Axis Movement DNA Radar on Native HTML5 Canvas.
 * Supports dynamic 4-axis collapse if bilateral symmetry is null.
 * Strictly clamps canvas layout dimensions to wrapper container.
 */
function renderMovementDNARadar(canvasId, dimensions) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !dimensions) return;

  const wrap = canvas.parentElement;
  const rect = wrap ? wrap.getBoundingClientRect() : canvas.getBoundingClientRect();
  const isVisible = rect.width > 0 && rect.height > 0;
  const width = isVisible ? Math.round(rect.width) : 340;
  const height = isVisible ? Math.round(rect.height) : 340;

  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;

  // Lock CSS dimensions so canvas never balloons
  canvas.style.width = width + 'px';
  canvas.style.height = height + 'px';

  // Set internal drawing buffer
  const pixelWidth = Math.round(width * dpr);
  const pixelHeight = Math.round(height * dpr);
  if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
    canvas.width = pixelWidth;
    canvas.height = pixelHeight;
  }

  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);

  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(centerX, centerY) - 42;
  if (radius <= 10) return;

  // Check if symmetry is present
  const hasSymmetry = dimensions.bilateral_symmetry && dimensions.bilateral_symmetry.score !== null;

  // Define Axes Layout
  let axes = [];
  if (hasSymmetry) {
    axes = [
      { key: 'movement_stability', label: 'STABILITY', angle: -Math.PI / 2 },
      { key: 'tempo_control', label: 'TEMPO', angle: -Math.PI / 2 + (2 * Math.PI / 5) },
      { key: 'range_of_motion', label: 'ROM', angle: -Math.PI / 2 + (4 * Math.PI / 5) },
      { key: 'repetition_consistency', label: 'CONSISTENCY', angle: -Math.PI / 2 + (6 * Math.PI / 5) },
      { key: 'bilateral_symmetry', label: 'SYMMETRY', angle: -Math.PI / 2 + (8 * Math.PI / 5) }
    ];
  } else {
    axes = [
      { key: 'movement_stability', label: 'STABILITY', angle: -Math.PI / 2 },
      { key: 'tempo_control', label: 'TEMPO', angle: 0 },
      { key: 'range_of_motion', label: 'ROM', angle: Math.PI / 2 },
      { key: 'repetition_consistency', label: 'CONSISTENCY', angle: Math.PI }
    ];
  }

  const numAxes = axes.length;

  // 1. Draw Concentric Grid Rings (20%, 40%, 60%, 80%, 100%)
  const levels = 5;
  for (let l = 1; l <= levels; l++) {
    const r = (radius / levels) * l;
    ctx.beginPath();
    for (let i = 0; i < numAxes; i++) {
      const angle = axes[i].angle;
      const x = centerX + r * Math.cos(angle);
      const y = centerY + r * Math.sin(angle);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = (l === levels) ? '#cbd5e1' : '#e2e8f0';
    ctx.lineWidth = (l === levels) ? 1.5 : 1;
    ctx.stroke();

    // Scale numbers on vertical axis
    if (l > 1) {
      ctx.fillStyle = '#64748b';
      ctx.font = '9px Outfit, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(`${l * 20}`, centerX - 6, centerY - r + 3);
    }
  }

  // 2. Draw Spokes and Axis Labels
  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = 1;
  for (let i = 0; i < numAxes; i++) {
    const angle = axes[i].angle;
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);

    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.lineTo(x, y);
    ctx.stroke();

    // Axis Label
    const labelDist = radius + 22;
    const lx = centerX + labelDist * Math.cos(angle);
    const ly = centerY + labelDist * Math.sin(angle);

    const dim = dimensions[axes[i].key];
    const scoreVal = dim && dim.score !== null ? dim.score.toFixed(0) : '--';

    ctx.fillStyle = '#0f172a';
    ctx.font = 'bold 10px Outfit, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(axes[i].label, lx, ly - 5);

    ctx.fillStyle = '#0284c7';
    ctx.font = '900 11px Outfit, sans-serif';
    ctx.fillText(`${scoreVal}`, lx, ly + 8);
  }

  // 3. Draw Baseline Profile (Dashed Amber Polygon)
  ctx.beginPath();
  let hasValidBaseline = false;
  for (let i = 0; i < numAxes; i++) {
    const dim = dimensions[axes[i].key];
    const baseVal = (dim && dim.baseline !== null) ? dim.baseline : 0;
    if (baseVal > 0) hasValidBaseline = true;
    const r = (radius * (baseVal / 100));
    const x = centerX + r * Math.cos(axes[i].angle);
    const y = centerY + r * Math.sin(axes[i].angle);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  if (hasValidBaseline) {
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = '#d97706';
    ctx.lineWidth = 1.8;
    ctx.fillStyle = 'rgba(217, 119, 6, 0.08)';
    ctx.fill();
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // 4. Draw Recent/Current Profile (Cyan Polygon)
  ctx.beginPath();
  let hasValidRecent = false;
  for (let i = 0; i < numAxes; i++) {
    const dim = dimensions[axes[i].key];
    const recVal = (dim && dim.score !== null) ? dim.score : 0;
    if (recVal > 0) hasValidRecent = true;
    const r = (radius * (recVal / 100));
    const x = centerX + r * Math.cos(axes[i].angle);
    const y = centerY + r * Math.sin(axes[i].angle);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  if (hasValidRecent) {
    // Fill Gradient
    const grad = ctx.createRadialGradient(centerX, centerY, 10, centerX, centerY, radius);
    grad.addColorStop(0, 'rgba(2, 132, 199, 0.25)');
    grad.addColorStop(1, 'rgba(2, 132, 199, 0.05)');
    ctx.fillStyle = grad;
    ctx.fill();

    ctx.strokeStyle = '#0284c7';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Draw vertex points
    for (let i = 0; i < numAxes; i++) {
      const dim = dimensions[axes[i].key];
      const recVal = (dim && dim.score !== null) ? dim.score : 0;
      const r = (radius * (recVal / 100));
      const x = centerX + r * Math.cos(axes[i].angle);
      const y = centerY + r * Math.sin(axes[i].angle);

      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#0284c7';
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }
}

/**
 * Renders the 5 Dimension Cards grid with clean, compact progress bars and scores.
 */
function renderDNADimensionCards(dimensions) {
  const container = document.getElementById('dnaDimensionGrid');
  if (!container || !dimensions) return;

  const dimensionKeys = [
    'range_of_motion',
    'movement_stability',
    'tempo_control',
    'repetition_consistency',
    'bilateral_symmetry'
  ];

  const icons = {
    range_of_motion: 'fa-ruler-combined',
    movement_stability: 'fa-crosshairs',
    tempo_control: 'fa-stopwatch',
    repetition_consistency: 'fa-wave-square',
    bilateral_symmetry: 'fa-scale-balanced'
  };

  container.innerHTML = dimensionKeys.map(key => {
    const dim = dimensions[key];
    if (!dim) return '';

    const isNA = dim.score === null || dim.status === 'N/A';
    const scoreText = isNA ? 'N/A' : dim.score.toFixed(1);
    const statusClass = isNA ? 'status-na' : `status-${dim.status.toLowerCase().replace(/\s+/g, '-')}`;
    
    let trendIcon = '<i class="fa-solid fa-minus"></i>';
    let trendClass = 'trend-stable';
    if (dim.trend === 'IMPROVING') {
      trendIcon = '<i class="fa-solid fa-arrow-trend-up"></i>';
      trendClass = 'trend-improving';
    } else if (dim.trend === 'DECLINING') {
      trendIcon = '<i class="fa-solid fa-arrow-trend-down"></i>';
      trendClass = 'trend-declining';
    }

    const deltaSign = dim.delta >= 0 ? '+' : '';
    const deltaText = isNA ? '' : `${deltaSign}${dim.delta.toFixed(1)} (${deltaSign}${dim.pct_change.toFixed(1)}%)`;

    return `
      <div class="dna-dim-compact-row">
        <div class="dna-dim-compact-info">
          <span class="dna-dim-compact-label"><i class="fa-solid ${icons[key]}"></i> ${escapeHTML(dim.label)}</span>
          <span class="dna-dim-compact-status ${statusClass}">${dim.status}</span>
        </div>
        <div class="dna-dim-compact-bar-wrap">
          <div class="dna-dim-compact-bar ${statusClass}" style="width: ${isNA ? 0 : Math.min(100, Math.max(8, dim.score))}%;"></div>
        </div>
        <div class="dna-dim-compact-score">
          <span class="dna-dim-val">${scoreText}</span>
          ${deltaText ? `<span class="dna-dim-compact-delta ${trendClass}">${trendIcon} ${deltaText}</span>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Toggle progressive disclosure for Movement DNA secondary details and charts.
 */
function toggleDNADetails() {
  const content = document.getElementById('dnaDetailsContent');
  const toggleBtn = document.getElementById('dnaDetailsToggle');
  const toggleText = document.getElementById('dnaToggleText');
  const toggleIcon = document.getElementById('dnaToggleIcon');

  if (!content) return;
  const isHidden = content.style.display === 'none' || !content.classList.contains('open');

  if (isHidden) {
    content.style.display = 'flex';
    content.classList.add('open');
    if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');
    if (toggleText) toggleText.innerText = 'Hide Details & Visualizations';
    if (toggleIcon) {
      toggleIcon.classList.remove('fa-chevron-down');
      toggleIcon.classList.add('fa-chevron-up');
    }
    refreshMovementDNACanvases();
  } else {
    content.style.display = 'none';
    content.classList.remove('open');
    if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
    if (toggleText) toggleText.innerText = 'View Full Analysis & Visualizations';
    if (toggleIcon) {
      toggleIcon.classList.remove('fa-chevron-up');
      toggleIcon.classList.add('fa-chevron-down');
    }
  }
}
window.toggleDNADetails = toggleDNADetails;

/**
 * Renders the AI Movement Limiter & "Why This Matters" Card.
 */
function renderDNALimiterCard(primaryLimiter, secondaryLimiter) {
  const container = document.getElementById('dnaLimiterCard');
  if (!container || !primaryLimiter) return;

  const pLabel = primaryLimiter.label || 'Stability';
  const pScore = primaryLimiter.score !== null ? primaryLimiter.score.toFixed(1) : '--';
  const pWhy = primaryLimiter.why_it_matters || 'Technique refinement opportunity identified from recent kinematics.';
  const pResponse = primaryLimiter.ai_response || 'Adaptive training will prescribe targeted drills to reinforce this dimension.';

  const sLabel = secondaryLimiter ? secondaryLimiter.label : null;
  const sScore = secondaryLimiter && secondaryLimiter.score !== null ? secondaryLimiter.score.toFixed(1) : null;

  container.innerHTML = `
    <div class="dna-limiter-header">
      <div class="limiter-badge"><i class="fa-solid fa-bullseye" style="color: #ef4444;"></i> WHAT IS LIMITING YOUR PERFORMANCE?</div>
      <h3 class="limiter-title">${escapeHTML(pLabel)} <span class="limiter-score-pill">${pScore} / 100</span></h3>
    </div>

    <div class="dna-limiter-grid">
      <div class="dna-limiter-col">
        <span class="col-tag"><i class="fa-solid fa-circle-question" style="color: var(--accent-cyan);"></i> WHY THIS MATTERS</span>
        <p class="limiter-text">${escapeHTML(pWhy)}</p>
      </div>

      <div class="dna-limiter-col">
        <span class="col-tag"><i class="fa-solid fa-wand-magic-sparkles" style="color: var(--accent-lime);"></i> FITQUEST ADAPTIVE RESPONSE</span>
        <p class="limiter-text">${escapeHTML(pResponse)}</p>
      </div>
    </div>

    ${sLabel && sLabel !== pLabel ? `
      <div class="secondary-limiter-callout">
        <span>Secondary Limiting Factor: <strong>${escapeHTML(sLabel)}</strong> (${sScore}/100)</span>
      </div>
    ` : ''}
  `;
}

/**
 * Renders the Multi-Metric Evolution Timeline Spline Canvas.
 * Strictly clamps canvas layout dimensions to wrapper container.
 */
function renderMovementDNATimeline(canvasId, timeline, filter = 'all') {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const wrap = canvas.parentElement;
  const rect = wrap ? wrap.getBoundingClientRect() : canvas.getBoundingClientRect();
  const isVisible = rect.width > 0 && rect.height > 0;
  const width = isVisible ? Math.round(rect.width) : 700;
  const height = isVisible ? Math.round(rect.height) : 260;

  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;

  // Lock CSS dimensions so canvas never balloons
  canvas.style.width = width + 'px';
  canvas.style.height = height + 'px';

  // Set internal drawing buffer
  const pixelWidth = Math.round(width * dpr);
  const pixelHeight = Math.round(height * dpr);
  if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
    canvas.width = pixelWidth;
    canvas.height = pixelHeight;
  }

  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);

  if (!timeline || timeline.length === 0) {
    ctx.fillStyle = '#64748b';
    ctx.font = '13px Outfit, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('No historical sessions recorded yet. Complete workouts to populate timeline.', width / 2, height / 2);
    return;
  }

  const paddingLeft = 40;
  const paddingRight = 30;
  const paddingTop = 25;
  const paddingBottom = 40;

  const plotW = width - paddingLeft - paddingRight;
  const plotH = height - paddingTop - paddingBottom;
  if (plotW <= 10 || plotH <= 10) return;

  // 1. Draw Grid Lines
  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = 1;
  for (let s = 0; s <= 100; s += 25) {
    const y = paddingTop + plotH - (s / 100) * plotH;
    ctx.beginPath();
    ctx.moveTo(paddingLeft, y);
    ctx.lineTo(width - paddingRight, y);
    ctx.stroke();

    ctx.fillStyle = '#64748b';
    ctx.font = '10px Outfit, sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(`${s}`, paddingLeft - 8, y + 3);
  }

  // 2. Define Series Colors
  const seriesConfig = {
    overall: { label: 'Overall Quality', color: '#0284c7', width: 3 },
    range_of_motion: { label: 'ROM', color: '#7c3aed', width: 1.8 },
    movement_stability: { label: 'Stability', color: '#16a34a', width: 1.8 },
    tempo_control: { label: 'Tempo', color: '#d97706', width: 1.8 },
    repetition_consistency: { label: 'Consistency', color: '#2563eb', width: 1.8 },
    bilateral_symmetry: { label: 'Symmetry', color: '#db2777', width: 1.8 }
  };

  const nPoints = timeline.length;
  const getX = (i) => nPoints === 1 ? paddingLeft + plotW / 2 : paddingLeft + (i / (nPoints - 1)) * plotW;
  const getY = (val) => paddingTop + plotH - (Math.max(0, Math.min(100, val)) / 100) * plotH;

  // Render Series
  const seriesToDraw = filter === 'all'
    ? ['overall', 'range_of_motion', 'movement_stability', 'tempo_control', 'repetition_consistency']
    : [filter];

  seriesToDraw.forEach(sKey => {
    const cfg = seriesConfig[sKey];
    if (!cfg) return;

    ctx.beginPath();
    let started = false;

    for (let i = 0; i < nPoints; i++) {
      const val = timeline[i][sKey];
      if (val === null || val === undefined) continue;

      const x = getX(i);
      const y = getY(val);

      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else {
        // Draw smooth Bézier curve
        const prevX = getX(i - 1);
        const prevVal = timeline[i - 1][sKey] || val;
        const prevY = getY(prevVal);
        const cpx1 = prevX + (x - prevX) / 2;
        const cpy1 = prevY;
        const cpx2 = prevX + (x - prevX) / 2;
        const cpy2 = y;
        ctx.bezierCurveTo(cpx1, cpy1, cpx2, cpy2, x, y);
      }
    }

    ctx.strokeStyle = cfg.color;
    ctx.lineWidth = cfg.width;
    if (sKey === 'overall') {
      ctx.shadowColor = cfg.color;
      ctx.shadowBlur = 8;
    }
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Draw Points
    for (let i = 0; i < nPoints; i++) {
      const val = timeline[i][sKey];
      if (val === null || val === undefined) continue;
      const x = getX(i);
      const y = getY(val);

      ctx.beginPath();
      ctx.arc(x, y, sKey === 'overall' ? 4.5 : 3, 0, Math.PI * 2);
      ctx.fillStyle = cfg.color;
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  });

  // 3. X-Axis Labels (Sessions)
  for (let i = 0; i < nPoints; i++) {
    const x = getX(i);
    ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.font = '10px Outfit, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`S${i + 1}`, x, height - 12);
  }
}

/**
 * Filter handler for Timeline series toggles
 */
function setDNATimelineFilter(filterKey) {
  activeDNATimelineFilter = filterKey;
  const buttons = document.querySelectorAll('.dna-filter-btn');
  buttons.forEach(btn => {
    if (btn.dataset.filter === filterKey) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  if (currentMovementDNAData) {
    renderMovementDNATimeline('dnaTimelineCanvas', currentMovementDNAData.timeline, activeDNATimelineFilter);
  }
}

/**
 * Renders the Explainable AI Movement Report.
 */
function renderDNAAIReport(aiReport) {
  const container = document.getElementById('dnaReportGrid');
  if (!container || !aiReport) return;

  container.innerHTML = `
    <div class="dna-report-item">
      <div class="rep-tag tag-green"><i class="fa-solid fa-circle-check"></i> WHAT YOU DO WELL</div>
      <p class="rep-text">${escapeHTML(aiReport.what_you_do_well)}</p>
    </div>

    <div class="dna-report-item">
      <div class="rep-tag tag-red"><i class="fa-solid fa-triangle-exclamation"></i> WHAT IS LIMITING YOU</div>
      <p class="rep-text">${escapeHTML(aiReport.what_is_limiting_you)}</p>
    </div>

    <div class="dna-report-item">
      <div class="rep-tag tag-cyan"><i class="fa-solid fa-chart-line"></i> WHAT CHANGED</div>
      <p class="rep-text">${escapeHTML(aiReport.what_changed)}</p>
    </div>

    <div class="dna-report-item">
      <div class="rep-tag tag-purple"><i class="fa-solid fa-lightbulb"></i> WHAT FITQUEST RECOMMENDS</div>
      <p class="rep-text">${escapeHTML(aiReport.what_fitquest_recommends)}</p>
    </div>

    <div class="dna-report-item full-width">
      <div class="rep-tag tag-amber"><i class="fa-solid fa-arrow-right"></i> NEXT STEP</div>
      <p class="rep-text">${escapeHTML(aiReport.next_step)}</p>
    </div>
  `;
}

/**
 * Action: Generates and launches an Adaptive Workout based on Movement DNA.
 */
async function generateMovementDNAWorkout() {
  const btn = document.getElementById('dnaGenerateBtn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> GENERATING CALIBRATED ROUTINE...';
  }

  try {
    if (typeof generateAdaptiveWorkout === 'function') {
      await generateAdaptiveWorkout();
      switchTab('adaptiveTrainingView');
    }
  } catch (e) {
    console.error('[FitQuest DNA]: Failed to launch adaptive workout:', e);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> GENERATE MY ADAPTIVE WORKOUT';
    }
  }
}

/**
 * Empty state renderer
 */
function renderDNAEmptyState(msg) {
  const container = document.getElementById('movementDnaView');
  if (!container) return;
  console.warn('[FitQuest DNA]:', msg);
}

// Auto-mount and populate Movement DNA on page load
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('movementDnaView')) {
    populateDNAExerciseSelector();
    loadMovementDNA();
  }
});

window.loadMovementDNA = loadMovementDNA;
window.populateDNAExerciseSelector = populateDNAExerciseSelector;
window.refreshMovementDNACanvases = refreshMovementDNACanvases;

