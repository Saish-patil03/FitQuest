/**
 * FitQuest Progress & Analytics Dashboard Module
 * Manages fetching, rendering, filtering, and Chart.js visualization for verified user workout metrics.
 */

let activeAnalyticsTimeRange = 'all';
let formChartInstance = null;
let repChartInstance = null;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  initProgressTabObserver();
});

/**
 * Observes navigation tab switches to load analytics automatically when progressView is opened.
 */
function initProgressTabObserver() {
  const navTabs = document.querySelectorAll('.nav-tab');
  navTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      if (tab.getAttribute('data-view') === 'progressView') {
        loadProgressAnalytics(activeAnalyticsTimeRange);
      }
    });
  });
}

/**
 * Switches time range filter (all, 90d, 30d, 7d)
 */
function setAnalyticsTimeRange(timeRange, event) {
  if (event) {
    const chips = document.querySelectorAll('.filter-chips-group .chip-filter');
    chips.forEach(c => c.classList.remove('active'));
    event.currentTarget.classList.add('active');
  }
  activeAnalyticsTimeRange = timeRange;
  loadProgressAnalytics(timeRange);
}

/**
 * Fetches analytics metrics from GET /api/v1/analytics/progress?time_range=...
 */
async function loadProgressAnalytics(timeRange = 'all') {
  const token = localStorage.getItem('fitquest_token');
  const headers = { 'Accept': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_BASE}/analytics/progress?time_range=${timeRange}`, {
      method: 'GET',
      headers: headers
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    renderOverviewCards(data.overview);
    renderProgressCharts(data.progress_trends);
    renderPersonalRecords(data.personal_records);
    renderExercisePerformance(data.exercise_performance);

  } catch (error) {
    console.error('[FitQuest Analytics Error]: Failed to fetch progress analytics:', error);
  }
}

/**
 * Renders Top Overview Stat Cards
 */
function renderOverviewCards(overview) {
  if (!overview) return;

  const totalWorkoutsEl = document.getElementById('progTotalWorkouts');
  const totalRepsEl = document.getElementById('progTotalReps');
  const avgFormEl = document.getElementById('progAvgForm');
  const streakEl = document.getElementById('progCurrentStreak');
  const bestFormEl = document.getElementById('progBestForm');
  const maxRepsEl = document.getElementById('progMaxReps');

  if (totalWorkoutsEl) totalWorkoutsEl.innerText = overview.total_valid_workouts || 0;
  if (totalRepsEl) totalRepsEl.innerText = (overview.total_repetitions || 0).toLocaleString();
  if (avgFormEl) avgFormEl.innerText = overview.total_valid_workouts > 0 ? `${overview.average_form_score.toFixed(1)}%` : 'N/A';
  if (streakEl) streakEl.innerText = `${overview.current_streak || 0} Days`;
  if (bestFormEl) bestFormEl.innerText = overview.total_valid_workouts > 0 ? `${overview.best_form_score.toFixed(1)}%` : 'N/A';
  if (maxRepsEl) maxRepsEl.innerText = overview.highest_repetition_count || 0;
}

/**
 * Renders Chart.js Form Score & Repetition Volume Trend Charts
 */
function renderProgressCharts(trends) {
  const formCanvas = document.getElementById('formTrendChart');
  const repCanvas = document.getElementById('repTrendChart');

  if (!formCanvas || !repCanvas || typeof Chart === 'undefined') return;

  const labels = (trends || []).map(t => {
    if (!t.date) return '';
    const d = new Date(t.date + 'T00:00:00');
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  });

  const formScores = (trends || []).map(t => t.avg_form_score);
  const repVolumes = (trends || []).map(t => t.total_reps);

  // 1. Destroy prior Chart instances if re-rendering
  if (formChartInstance) formChartInstance.destroy();
  if (repChartInstance) repChartInstance.destroy();

  // 2. Render Form Accuracy Score Line Chart
  const ctxForm = formCanvas.getContext('2d');
  const gradientForm = ctxForm.createLinearGradient(0, 0, 0, 260);
  gradientForm.addColorStop(0, 'rgba(132, 204, 22, 0.25)');
  gradientForm.addColorStop(1, 'rgba(132, 204, 22, 0.0)');

  formChartInstance = new Chart(ctxForm, {
    type: 'line',
    data: {
      labels: labels.length > 0 ? labels : ['No Data'],
      datasets: [{
        label: 'Avg Form Accuracy (%)',
        data: formScores.length > 0 ? formScores : [0],
        borderColor: '#65a30d',
        borderWidth: 2,
        backgroundColor: gradientForm,
        fill: true,
        tension: 0.3,
        pointBackgroundColor: '#65a30d',
        pointRadius: 4,
        pointHoverRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          min: 0,
          max: 100,
          grid: { color: '#e2e8f0' },
          ticks: { color: '#64748b', font: { family: 'Inter' } }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#64748b', font: { family: 'Inter' } }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#ffffff',
          titleColor: '#0f172a',
          bodyColor: '#4d7c0f',
          borderColor: '#e2e8f0',
          borderWidth: 1,
          padding: 10
        }
      }
    }
  });

  // 3. Render Repetition Volume Bar Chart
  const ctxRep = repCanvas.getContext('2d');

  repChartInstance = new Chart(ctxRep, {
    type: 'bar',
    data: {
      labels: labels.length > 0 ? labels : ['No Data'],
      datasets: [{
        label: 'Total Repetitions',
        data: repVolumes.length > 0 ? repVolumes : [0],
        backgroundColor: '#84cc16',
        borderRadius: 4,
        borderSkipped: false
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: '#e2e8f0' },
          ticks: { color: '#64748b', font: { family: 'Inter' } }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#64748b', font: { family: 'Inter' } }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#ffffff',
          titleColor: '#0f172a',
          bodyColor: '#4d7c0f',
          borderColor: '#e2e8f0',
          borderWidth: 1,
          padding: 10
        }
      }
    }
  });
}

/**
 * Renders Personal Records (PR) Wall Cards
 */
function renderPersonalRecords(records) {
  const container = document.getElementById('personalRecordsGrid');
  if (!container) return;

  if (!records || records.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 24px; text-align: center; color: var(--text-muted); background: var(--bg-surface); border-radius: var(--radius-sm); border: 1px dashed var(--border-color);">
        <i class="fa-solid fa-crown" style="font-size: 1.8rem; color: var(--text-muted); margin-bottom: 8px;"></i><br>
        No personal records achieved yet. Complete valid exercise sets to earn PR badges!
      </div>
    `;
    return;
  }

  container.innerHTML = records.map(pr => {
    const achievedDate = pr.achieved_at ? new Date(pr.achieved_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : '';
    return `
      <div class="pr-card" style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 18px; position: relative; overflow: hidden; transition: transform 0.2s ease;">
        <div style="position: absolute; top: -10px; right: -10px; width: 42px; height: 42px; background: var(--bg-surface-secondary); border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 1px solid var(--border-color);">
          <i class="fa-solid fa-crown" style="color: var(--accent-lime); font-size: 0.85rem;"></i>
        </div>
        <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--accent-lime); margin-bottom: 4px;">PR Badge</div>
        <h4 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin-bottom: 10px;">${escapeHTML(pr.exercise_name)}</h4>
        <div style="display: flex; align-items: baseline; gap: 6px; margin-bottom: 6px;">
          <span style="font-size: 1.8rem; font-weight: 800; color: var(--text-primary);">${pr.max_reps}</span>
          <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 500;">reps (Best Set)</span>
        </div>
        <div style="font-size: 0.82rem; color: var(--status-success); font-weight: 600; margin-bottom: 6px;">
          <i class="fa-solid fa-circle-check"></i> ${pr.best_form_score}% Form Rating
        </div>
        ${achievedDate ? `<div style="font-size: 0.75rem; color: var(--text-muted);"><i class="fa-solid fa-calendar-check"></i> ${achievedDate}</div>` : ''}
      </div>
    `;
  }).join('');
}

/**
 * Renders Exercise Performance Breakdown Cards
 */
function renderExercisePerformance(exercises) {
  const container = document.getElementById('exercisePerformanceContainer');
  if (!container) return;

  if (!exercises || exercises.length === 0) {
    container.innerHTML = `
      <div style="padding: 24px; text-align: center; color: var(--text-muted); background: var(--bg-surface); border-radius: var(--radius-sm); border: 1px dashed var(--border-color);">
        No completed exercise performance records found.
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px;">
      ${exercises.map(ex => `
        <div class="ex-perf-card" style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 18px;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
            <div>
              <h4 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary);">${escapeHTML(ex.exercise_name)}</h4>
              ${ex.muscle_group ? `<span style="font-size: 0.75rem; color: var(--accent-lime); background: var(--accent-lime-muted); border: 1px solid var(--accent-lime-border); padding: 2px 8px; border-radius: 4px; font-weight: 600; margin-top: 4px; display: inline-block;">${escapeHTML(ex.muscle_group)}</span>` : ''}
            </div>
            <div style="text-align: right;">
              <span style="font-size: 1.2rem; font-weight: 800; color: var(--text-primary);">${ex.workout_count}</span>
              <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">sets</div>
            </div>
          </div>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background: var(--bg-surface-secondary); padding: 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            <div>
              <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Total Reps</div>
              <div style="font-size: 1.1rem; font-weight: 800; color: var(--text-primary);">${ex.total_reps}</div>
            </div>
            <div>
              <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Avg Form</div>
              <div style="font-size: 1.1rem; font-weight: 800; color: var(--status-success);">${ex.average_form_score}%</div>
            </div>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

/**
 * Escapes unsafe HTML characters to prevent XSS
 */
function escapeHTML(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
