/**
 * FitQuest Personalized Goals & Targets Module
 * Manages goal listing, live progress rendering, goal creation modal, dynamic form fields, and deletion.
 */

document.addEventListener('DOMContentLoaded', () => {
  initGoalsTabObserver();
});

/**
 * Observes navigation switches to load goals whenever progressView is displayed.
 */
function initGoalsTabObserver() {
  const navTabs = document.querySelectorAll('.nav-tab');
  navTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      if (tab.getAttribute('data-view') === 'progressView') {
        loadUserGoals();
      }
    });
  });
}

/**
 * Fetches authenticated user goals with live progress from GET /api/v1/goals/me
 */
async function loadUserGoals() {
  const token = localStorage.getItem('fitquest_token');
  const headers = { 'Accept': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_BASE}/goals/me`, {
      method: 'GET',
      headers: headers
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const goals = await response.json();
    renderGoalCards(goals);

  } catch (error) {
    console.error('[FitQuest Goals Error]: Failed to fetch user goals:', error);
  }
}

/**
 * Renders goal cards with live backend progress
 */
function renderGoalCards(goals) {
  const container = document.getElementById('userGoalsGrid');
  if (!container) return;

  if (!goals || goals.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 28px; text-align: center; color: var(--text-muted); background: var(--bg-surface); border-radius: var(--radius-sm); border: 1px dashed var(--border-color);">
        <i class="fa-solid fa-bullseye" style="font-size: 2.2rem; color: var(--text-muted); margin-bottom: 12px;"></i>
        <h4 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">No Active Goals Yet</h4>
        <p style="font-size: 0.88rem; margin-bottom: 16px;">Set your first personal fitness target to track your progress live!</p>
        <button class="btn btn-primary" onclick="openCreateGoalModal()" style="font-size: 0.85rem; padding: 8px 18px;">
          <i class="fa-solid fa-plus"></i> Set Your First Goal
        </button>
      </div>
    `;
    return;
  }

  container.innerHTML = goals.map(goal => {
    const isCompleted = goal.is_completed;
    const progressPct = goal.progress_percentage || 0;
    const currentVal = goal.current_value || 0;
    const targetVal = goal.target_value || 0;
    
    // Formatting title & metrics based on goal type
    let title = 'Personal Goal';
    let unitLabel = 'units';
    let icon = 'fa-bullseye';
    let iconColor = 'var(--accent-lime)';

    if (goal.goal_type === 'REPETITION') {
      title = goal.exercise_name ? `Target ${goal.exercise_name} Reps` : 'Total Repetitions';
      unitLabel = 'reps';
      icon = 'fa-dumbbell';
      iconColor = 'var(--accent-lime)';
    } else if (goal.goal_type === 'FREQUENCY') {
      title = 'Weekly Workout Days';
      unitLabel = 'days';
      icon = 'fa-calendar-check';
      iconColor = 'var(--status-warning)';
    } else if (goal.goal_type === 'FORM_SCORE') {
      title = goal.exercise_name ? `${goal.exercise_name} Form Score` : 'Average Form Score';
      unitLabel = '% form';
      icon = 'fa-chart-pie';
      iconColor = 'var(--status-success)';
    } else if (goal.goal_type === 'EXERCISE_PR') {
      title = goal.exercise_name ? `${goal.exercise_name} PR Target` : 'Single-Set PR Target';
      unitLabel = 'reps (1 set)';
      icon = 'fa-trophy';
      iconColor = 'var(--status-warning)';
    }

    const timeframeBadge = (goal.time_frame || 'WEEKLY').toLowerCase();

    return `
      <div class="goal-card" style="background: var(--bg-surface); border: 1px solid ${isCompleted ? 'var(--status-success)' : 'var(--border-color)'}; border-radius: var(--radius-sm); padding: 20px; position: relative; transition: transform 0.2s ease;">
        <button onclick="confirmDeleteGoal(${goal.id})" style="position: absolute; top: 16px; right: 16px; background: transparent; border: none; color: var(--text-muted); cursor: pointer; font-size: 0.9rem; transition: color 0.2s;" title="Delete Goal">
          <i class="fa-solid fa-trash-can"></i>
        </button>

        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
          <div style="width: 36px; height: 36px; background: var(--bg-surface-secondary); border-radius: var(--radius-sm); border: 1px solid var(--border-color); display: flex; align-items: center; justify-content: center;">
            <i class="fa-solid ${icon}" style="color: ${iconColor}; font-size: 1rem;"></i>
          </div>
          <div>
            <h4 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); line-height: 1.2;">${escapeHTML(title)}</h4>
            <span style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); font-weight: 600;">${timeframeBadge} target</span>
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
          <div style="font-size: 1.4rem; font-weight: 800; color: ${isCompleted ? 'var(--status-success)' : 'var(--text-primary)'};">
            ${currentVal} <span style="font-size: 0.85rem; font-weight: 500; color: var(--text-muted);">/ ${targetVal} ${unitLabel}</span>
          </div>
          <div style="font-size: 0.9rem; font-weight: 700; color: ${isCompleted ? 'var(--status-success)' : 'var(--accent-lime)'};">
            ${progressPct}%
          </div>
        </div>

        <!-- PROGRESS BAR -->
        <div style="width: 100%; height: 6px; background: var(--bg-surface-secondary); border-radius: var(--radius-pill); overflow: hidden; margin-bottom: 12px; border: 1px solid var(--border-color);">
          <div style="width: ${progressPct}%; height: 100%; background: ${isCompleted ? 'var(--status-success)' : 'var(--accent-lime)'}; border-radius: var(--radius-pill); transition: width 0.4s ease;"></div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; color: var(--text-muted);">
          <span>
            ${isCompleted ? '<span style="color: var(--status-success); font-weight: 600;"><i class="fa-solid fa-circle-check"></i> Completed</span>' : (goal.days_remaining !== null ? `<i class="fa-solid fa-clock"></i> ${goal.days_remaining} days left` : '<i class="fa-solid fa-infinity"></i> Active Goal')}
          </span>
          ${goal.completed_at ? `<span><i class="fa-solid fa-flag-checkered"></i> ${new Date(goal.completed_at).toLocaleDateString()}</span>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Open Create Goal Modal Overlay
 */
function openCreateGoalModal() {
  const modal = document.getElementById('createGoalModal');
  const errBox = document.getElementById('goalErrorBox');
  if (errBox) errBox.style.display = 'none';

  handleGoalTypeChange();
  if (modal) modal.style.display = 'flex';
}

/**
 * Close Create Goal Modal Overlay
 */
function closeCreateGoalModal() {
  const modal = document.getElementById('createGoalModal');
  if (modal) modal.style.display = 'none';
}

/**
 * Adapts modal inputs based on selected Goal Type
 */
function handleGoalTypeChange() {
  const typeSelect = document.getElementById('goalTypeSelect');
  const exGroup = document.getElementById('goalExerciseGroup');
  const targetLabel = document.getElementById('goalTargetLabel');
  const targetInput = document.getElementById('goalTargetInput');

  if (!typeSelect || !exGroup || !targetLabel || !targetInput) return;

  const val = typeSelect.value;
  if (val === 'REPETITION') {
    exGroup.style.display = 'block';
    targetLabel.innerText = 'Target Repetitions';
    targetInput.placeholder = 'e.g. 100';
    targetInput.min = '1';
    targetInput.step = '1';
  } else if (val === 'FREQUENCY') {
    exGroup.style.display = 'none';
    targetLabel.innerText = 'Target Workout Days / Week';
    targetInput.placeholder = 'e.g. 4';
    targetInput.min = '1';
    targetInput.max = '7';
    targetInput.step = '1';
  } else if (val === 'FORM_SCORE') {
    exGroup.style.display = 'block';
    targetLabel.innerText = 'Target Form Score (%)';
    targetInput.placeholder = 'e.g. 90';
    targetInput.min = '1';
    targetInput.max = '100';
    targetInput.step = '1';
  } else if (val === 'EXERCISE_PR') {
    exGroup.style.display = 'block';
    targetLabel.innerText = 'Target Single-Set Reps (PR)';
    targetInput.placeholder = 'e.g. 25';
    targetInput.min = '1';
    targetInput.step = '1';
  }
}

/**
 * Handles Goal Creation Form Submission (POST /api/v1/goals)
 */
async function handleCreateGoalSubmit(event) {
  event.preventDefault();
  const token = localStorage.getItem('fitquest_token');
  const errBox = document.getElementById('goalErrorBox');
  if (errBox) errBox.style.display = 'none';

  const typeSelect = document.getElementById('goalTypeSelect');
  const exSelect = document.getElementById('goalExerciseSelect');
  const targetInput = document.getElementById('goalTargetInput');
  const tfSelect = document.getElementById('goalTimeframeSelect');

  const payload = {
    goal_type: typeSelect.value,
    target_value: parseFloat(targetInput.value),
    time_frame: tfSelect.value,
    exercise_id: (typeSelect.value !== 'FREQUENCY' && exSelect.value) ? parseInt(exSelect.value) : null
  };

  try {
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/goals`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Failed to create goal (HTTP ${response.status})`);
    }

    closeCreateGoalModal();
    loadUserGoals();

  } catch (error) {
    console.error('[FitQuest Goals Error]:', error);
    if (errBox) {
      errBox.innerText = error.message;
      errBox.style.display = 'block';
    }
  }
}

/**
 * Deletes a goal (DELETE /api/v1/goals/{id})
 */
async function confirmDeleteGoal(goalId) {
  if (!confirm('Are you sure you want to delete this goal?')) return;

  const token = localStorage.getItem('fitquest_token');
  const headers = { 'Accept': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_BASE}/goals/${goalId}`, {
      method: 'DELETE',
      headers: headers
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    loadUserGoals();

  } catch (error) {
    console.error('[FitQuest Goals Error]: Failed to delete goal:', error);
  }
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
