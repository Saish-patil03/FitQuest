/**
 * FitQuest — Closed-Loop Adaptive AI Training Engine (Phase 3)
 * Frontend Controller for Adaptive Movement Profile, Weakness-Targeted Exercise
 * Recommendations, and Personalized Workout Plan Generation.
 */

let currentAdaptiveProfile = null;
let currentAdaptivePlan = null;

/**
 * Loads and renders the user's derived Adaptive Movement Profile
 */
async function loadAdaptiveProfile() {
  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
  const container = document.getElementById('adaptiveContainer');

  if (!token) {
    if (container) {
      container.innerHTML = `
        <div class="empty-state-card">
          <i class="fa-solid fa-lock" style="font-size: 2.5rem; color: var(--accent-cyan); margin-bottom: 12px;"></i>
          <h3>Authentication Required</h3>
          <p>Please log in to view your personalized Adaptive Movement Intelligence profile.</p>
        </div>
      `;
    }
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/adaptive-training/profile`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json'
      }
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    currentAdaptiveProfile = await res.json();
    renderAdaptiveProfile(currentAdaptiveProfile);

    // Also fetch latest adaptive workout recommendation
    fetchLatestAdaptiveWorkout();

  } catch (err) {
    console.error('[FitQuest Error]: Failed to load adaptive profile:', err);
  }
}

/**
 * Renders the Adaptive Training Center Dashboard
 */
function renderAdaptiveProfile(profile) {
  if (!profile) return;

  // 1. Hero Focus & Confidence
  const primaryEl = document.getElementById('adaptPrimaryFocus');
  const secondaryEl = document.getElementById('adaptSecondaryFocus');
  const confPill = document.getElementById('adaptConfidencePill');
  const confReason = document.getElementById('adaptConfidenceReason');
  const sessCountEl = document.getElementById('adaptSessionsCount');

  if (primaryEl) primaryEl.innerText = (profile.primary_focus_label || 'Movement Stability').toUpperCase();
  if (secondaryEl) secondaryEl.innerText = (profile.secondary_focus_label || 'Tempo Control').toUpperCase();
  if (sessCountEl) sessCountEl.innerText = `${profile.total_sessions_analyzed || 0} Sessions Analyzed`;

  if (confPill) {
    const conf = (profile.confidence || 'Low').toLowerCase();
    confPill.className = `adapt-conf-pill conf-${conf}`;
    let icon = '<i class="fa-solid fa-shield"></i>';
    if (conf === 'high') icon = '<i class="fa-solid fa-shield-halved" style="color: var(--accent-lime);"></i>';
    confPill.innerHTML = `${icon} ${profile.confidence.toUpperCase()} CONFIDENCE`;
  }

  if (confReason) {
    confReason.innerText = profile.confidence_reason || 'Derived from your longitudinal movement kinematics.';
  }

  // 2. AI Movement Insight & Response
  const insightEl = document.getElementById('adaptInsightBody');
  const responseEl = document.getElementById('adaptResponseBody');

  if (insightEl) insightEl.innerText = profile.summary_insight || 'Observing biomechanical stability and movement cadence.';
  if (responseEl) responseEl.innerText = profile.fitquest_response || 'Adaptive workout will optimize for controlled eccentric pacing.';

  // 3. Biomechanical Dimension Meters Grid
  renderAdaptiveDimensionMeters(profile);
}

/**
 * Renders 5 Biomechanical Dimension status meters
 */
function renderAdaptiveDimensionMeters(profile) {
  const grid = document.getElementById('adaptiveDimensionGrid');
  if (!grid) return;

  const avgs = profile.metric_averages || {};
  const statuses = profile.metric_status || {};

  const dimensions = [
    { key: 'range_of_motion', label: 'Range of Motion', icon: 'fa-arrows-up-down-left-right', color: '#0284c7' },
    { key: 'movement_stability', label: 'Movement Stability', icon: 'fa-shield-heart', color: '#16a34a' },
    { key: 'tempo_control', label: 'Tempo Control', icon: 'fa-stopwatch', color: '#d97706' },
    { key: 'repetition_consistency', label: 'Rep Consistency', icon: 'fa-rotate', color: '#4f46e5' },
    { key: 'bilateral_symmetry', label: 'Bilateral Symmetry', icon: 'fa-scale-balanced', color: '#db2777' },
  ];

  grid.innerHTML = dimensions.map(d => {
    const val = avgs[d.key];
    const status = statuses[d.key] || 'N/A';
    const isNA = (val === null || val === undefined);
    const scoreText = isNA ? 'N/A' : `${val}%`;
    const fillWidth = isNA ? 0 : Math.min(100, Math.max(5, val));

    let statusClass = 'status-na';
    if (status === 'STRONG') statusClass = 'status-strong';
    else if (status === 'ADEQUATE') statusClass = 'status-adequate';
    else if (status === 'NEEDS ATTENTION') statusClass = 'status-attention';
    else if (status === 'HIGH PRIORITY') statusClass = 'status-priority';

    return `
      <div class="adapt-dim-compact-row">
        <div class="adapt-dim-compact-info">
          <span class="adapt-dim-compact-label"><i class="fa-solid ${d.icon}" style="color: ${d.color};"></i> ${d.label}</span>
          <span class="dim-status-pill ${statusClass}">${status}</span>
        </div>
        <div class="adapt-dim-compact-bar-wrap">
          <div class="adapt-dim-compact-bar" style="width: ${fillWidth}%; background: ${d.color};"></div>
        </div>
        <div class="adapt-dim-compact-score">
          <span class="dim-score-val">${scoreText}</span>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Triggers on-demand generation of a personalized adaptive workout
 */
async function generateAdaptiveWorkout() {
  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
  const genBtn = document.getElementById('generateAdaptiveBtn');
  const planContainer = document.getElementById('adaptivePlanContainer');

  if (!token) {
    alert('Please log in to generate an adaptive workout.');
    return;
  }

  if (genBtn) {
    genBtn.disabled = true;
    genBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Synthesizing Biomechanical Prescription...`;
  }

  try {
    const res = await fetch(`${API_BASE}/adaptive-training/generate`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json'
      }
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const plan = await res.json();
    currentAdaptivePlan = plan;
    window.currentAdaptivePlan = plan;
    renderGeneratedAdaptivePlan(plan);

  } catch (err) {
    console.error('[FitQuest Error]: Failed to generate adaptive workout:', err);
    if (planContainer) {
      planContainer.innerHTML = `<div class="empty-state-card">Error generating adaptive workout. Please verify the backend server is running.</div>`;
    }
  } finally {
    if (genBtn) {
      genBtn.disabled = false;
      genBtn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> GENERATE ADAPTIVE WORKOUT`;
    }
  }
}

/**
 * Fetches latest adaptive workout if available
 */
async function fetchLatestAdaptiveWorkout() {
  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
  if (!token) return;

  try {
    const res = await fetch(`${API_BASE}/adaptive-training/latest`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json'
      }
    });
    if (res.ok) {
      const plan = await res.json();
      currentAdaptivePlan = plan;
      window.currentAdaptivePlan = plan;
      renderGeneratedAdaptivePlan(plan);
    }
  } catch (e) {
    // Non-critical background fetch
  }
}

/**
 * Renders the generated Adaptive Workout Plan Card and Exercise Sequence
 */
function renderGeneratedAdaptivePlan(plan) {
  const container = document.getElementById('adaptivePlanContainer');
  if (!container || !plan) return;

  container.innerHTML = `
    <div class="adaptive-plan-card">
      <div class="adapt-plan-top">
        <div>
          <span class="adapt-plan-badge"><i class="fa-solid fa-dna"></i> PERSONALIZED WORKOUT PRESCRIPTION</span>
          <h3 class="adapt-plan-title">${plan.title}</h3>
          <p class="adapt-plan-desc">${plan.why_this_workout}</p>
        </div>
        <div class="adapt-plan-meta">
          <div class="meta-stat">
            <span class="meta-val">${plan.estimated_duration_min} MIN</span>
            <span class="meta-lbl">Est. Duration</span>
          </div>
          <div class="meta-stat">
            <span class="meta-val">${plan.total_exercises}</span>
            <span class="meta-lbl">Exercises</span>
          </div>
          <div class="meta-stat">
            <span class="meta-val">${plan.total_sets}</span>
            <span class="meta-lbl">Total Sets</span>
          </div>
        </div>
      </div>

      <div class="adapt-exercise-list">
        ${plan.exercises.map((ex, i) => `
          <div class="adapt-ex-card">
            <div class="adapt-ex-num">0${i + 1}</div>
            <div class="adapt-ex-content">
              <div class="adapt-ex-header-row">
                <h4 class="adapt-ex-name">${ex.exercise_name}</h4>
                <div class="adapt-ex-tags">
                  <span class="tempo-tag"><i class="fa-solid fa-stopwatch"></i> TEMPO ${ex.target_tempo}</span>
                  <span class="focus-tag"><i class="fa-solid fa-crosshairs"></i> ${ex.focus}</span>
                </div>
              </div>
              <div class="adapt-ex-volume-row">
                <span class="volume-badge"><i class="fa-solid fa-layer-group"></i> ${ex.target_sets} Sets × ${ex.target_reps} Reps</span>
                <span class="rest-badge"><i class="fa-solid fa-bed"></i> ${ex.rest_duration_sec}s Rest</span>
              </div>
              <div class="adapt-ex-reason-box">
                <i class="fa-solid fa-circle-info" style="color: var(--accent-cyan); margin-top: 2px;"></i>
                <span><strong>Why selected:</strong> ${ex.selection_reason || ex.reason || 'Targeted biomechanical development'}</span>
              </div>
            </div>
          </div>
        `).join('')}
      </div>

      <div class="adapt-plan-action-bar">
        <button class="btn btn-primary btn-xl" onclick="startAdaptiveWorkoutSession()" style="width: 100%; justify-content: center; font-size: 1.05rem; letter-spacing: 0.06em;">
          <i class="fa-solid fa-play"></i> START ADAPTIVE WORKOUT SESSION
        </button>
      </div>
    </div>
  `;
}

/**
 * Seamlessly transitions the generated Adaptive Workout into FitQuest's live workout lifecycle
 */
function startAdaptiveWorkoutSession() {
  if (!currentAdaptivePlan || !currentAdaptivePlan.exercises || currentAdaptivePlan.exercises.length === 0) {
    alert('Please generate an adaptive workout plan first.');
    return;
  }

  // Ensure window reference is set
  window.currentAdaptivePlan = currentAdaptivePlan;

  // Determine the first prescribed adaptive exercise
  const firstEx = currentAdaptivePlan.exercises[0];
  const targetExId = firstEx.exercise_id || firstEx.id;

  if (!targetExId) {
    console.error('[FitQuest Error]: Could not resolve first adaptive exercise ID from plan:', currentAdaptivePlan);
    alert('Could not find the prescribed exercise. Please try generating a new adaptive plan.');
    return;
  }

  // 1. Automatically switch active view to Workout view
  if (typeof switchTab === 'function') {
    switchTab('workoutView');
  }

  // 2. Automatically load first exercise into existing Workout flow (showing Stage 1: LEARN)
  if (typeof selectExercise === 'function') {
    if (typeof allExercises !== 'undefined' && Array.isArray(allExercises) && allExercises.length > 0) {
      selectExercise(targetExId);
    } else if (typeof loadExerciseCatalogue === 'function') {
      loadExerciseCatalogue().then(() => {
        selectExercise(targetExId);
      });
    } else {
      selectExercise(targetExId);
    }
  } else {
    console.error('[FitQuest Error]: selectExercise function not found in workout.js');
  }
}

// Export to window
window.startAdaptiveWorkoutSession = startAdaptiveWorkoutSession;
