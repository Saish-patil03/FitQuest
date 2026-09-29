/**
 * FitQuest Recovery & Training Load Insights Module
 * Fetches software-based training load ratio (ATL/CTL) and recovery status metrics from GET /api/v1/training-load/me.
 */

document.addEventListener('DOMContentLoaded', () => {
  initTrainingLoadObserver();
});

/**
 * Observes navigation switches to load training load metrics whenever progressView is displayed.
 */
function initTrainingLoadObserver() {
  const navTabs = document.querySelectorAll('.nav-tab');
  navTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      if (tab.getAttribute('data-view') === 'progressView') {
        loadTrainingLoadInsights();
      }
    });
  });
}

/**
 * Fetches recovery & training load metrics from GET /api/v1/training-load/me
 */
async function loadTrainingLoadInsights() {
  const token = localStorage.getItem('fitquest_token');
  const headers = { 'Accept': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_BASE}/training-load/me`, {
      method: 'GET',
      headers: headers
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    renderTrainingLoadCard(data);

  } catch (error) {
    console.error('[FitQuest Training Load Error]: Failed to fetch recovery insights:', error);
  }
}

/**
 * Renders Training Load Card UI
 */
function renderTrainingLoadCard(data) {
  const scoreEl = document.getElementById('loadRecoveryScore');
  const statusEl = document.getElementById('loadRecoveryStatus');
  const ratioEl = document.getElementById('loadRatioVal');
  const zoneEl = document.getElementById('loadZoneBadge');
  const acuteEl = document.getElementById('loadAcuteVal');
  const chronicEl = document.getElementById('loadChronicVal');
  const formEl = document.getElementById('loadAvgForm');
  const restEl = document.getElementById('loadRestGap');
  const explanationEl = document.getElementById('loadExplanation');

  if (!statusEl) return;

  // 1. Insufficient Data State
  if (data.recovery_status === 'INSUFFICIENT_DATA' || data.recovery_score === null) {
    if (scoreEl) scoreEl.innerText = 'N/A';
    statusEl.innerText = 'INSUFFICIENT DATA';
    statusEl.style.color = 'var(--text-muted)';
    if (ratioEl) ratioEl.innerText = '--';
    if (zoneEl) {
      zoneEl.innerText = 'NO WORKOUTS';
      zoneEl.style.color = 'var(--text-muted)';
    }
    if (acuteEl) acuteEl.innerText = '0.0 pts';
    if (chronicEl) chronicEl.innerText = '0.0 pts';
    if (formEl) formEl.innerText = 'N/A';
    if (restEl) restEl.innerText = 'N/A';
    if (explanationEl) {
      explanationEl.innerText = data.explanation || 'Complete your first valid workout to unlock Recovery & Training Load Insights.';
    }
    return;
  }

  // 2. Valid Recovery & Load Data
  const score = data.recovery_score;
  if (scoreEl) scoreEl.innerText = `${score}%`;

  let statusColor = 'var(--accent-cyan)';
  let readableStatus = data.recovery_status.replace(/_/g, ' ');

  if (data.recovery_status === 'FULLY_RECOVERED') {
    statusColor = 'var(--accent-cyan)';
  } else if (data.recovery_status === 'MODERATELY_RECOVERED') {
    statusColor = 'var(--accent-green)';
  } else if (data.recovery_status === 'PARTIALLY_RECOVERED') {
    statusColor = '#f59e0b';
  } else if (data.recovery_status === 'FATIGUE_ACCUMULATED') {
    statusColor = '#ef4444';
  }

  statusEl.innerText = readableStatus;
  statusEl.style.color = statusColor;
  if (scoreEl) scoreEl.style.color = statusColor;

  // Training Load Ratio & Zone
  if (ratioEl) ratioEl.innerText = data.training_load_ratio.toFixed(2);
  if (zoneEl) {
    const rawZone = data.training_load_zone.replace(/_/g, ' ');
    let zoneColor = 'var(--accent-purple)';
    if (data.training_load_zone === 'OPTIMAL') zoneColor = 'var(--accent-green)';
    else if (data.training_load_zone === 'HIGH_LOAD') zoneColor = '#f59e0b';
    else if (data.training_load_zone === 'OVER_REACHING') zoneColor = '#ef4444';

    zoneEl.innerText = rawZone;
    zoneEl.style.color = zoneColor;
  }

  // Supporting metrics
  if (acuteEl) acuteEl.innerText = `${data.acute_load_7d} pts`;
  if (chronicEl) chronicEl.innerText = `${data.chronic_load_28d} pts`;
  if (formEl) {
    const avgForm = data.supporting_metrics?.recent_avg_form;
    formEl.innerText = avgForm !== null ? `${avgForm}%` : 'N/A';
  }
  if (restEl) {
    const daysSince = data.supporting_metrics?.days_since_last_workout;
    restEl.innerText = daysSince !== null ? `${daysSince} Day${daysSince !== 1 ? 's' : ''}` : 'N/A';
  }

  // Explanation
  if (explanationEl) {
    explanationEl.innerText = data.explanation || '';
  }
}
