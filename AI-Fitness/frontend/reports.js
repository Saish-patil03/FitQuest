/**
 * FitQuest Progress Reports Manager
 * Handles fetching report availability, rendering report cards in Profile view,
 * displaying interactive in-app report preview modals, and downloading branded PDF reports.
 */

let currentReportPeriod = null;

function getReportsApiBase() {
  return window.getFitQuestApiBase ? window.getFitQuestApiBase() : (window.API_BASE || 'https://fitquest-backend-1brv.onrender.com/api/v1');
}

document.addEventListener('DOMContentLoaded', () => {
  // If user is already authenticated, load initial report availability
  if (typeof authToken !== 'undefined' && authToken) {
    loadProgressReports();
  }
});

/**
 * Fetches available reporting periods (15, 30, 60, 90 days) and renders them in the Profile view.
 */
async function loadProgressReports() {
  const container = document.getElementById('profReportsGrid');
  if (!container) return;

  if (typeof authToken === 'undefined' || !authToken) {
    container.innerHTML = `
      <div class="report-empty-state">
        <i class="fa-solid fa-lock"></i>
        <p>Log in to view and download your FitQuest Progress Reports.</p>
      </div>
    `;
    return;
  }

  const apiBase = getReportsApiBase();

  try {
    const res = await fetch(`${apiBase}/reports/available`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    });

    if (!res.ok) {
      throw new Error('Could not load progress reports');
    }

    const data = await res.json();
    renderReportCards(data.reports);
  } catch (err) {
    container.innerHTML = `
      <div class="report-empty-state error">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <p>Unable to load progress reports. Please check your connection.</p>
        <button class="btn btn-secondary" onclick="loadUserReports()" style="margin-top: 12px;">
          <i class="fa-solid fa-rotate-right"></i> Retry
        </button>
      </div>
    `;
  }
}

/**
 * Renders the 4 reporting cards (15d, 30d, 60d, 90d) into the DOM.
 */
function renderReportCards(reports) {
  const container = document.getElementById('profReportsGrid');
  if (!container) return;

  if (!reports || reports.length === 0) {
    container.innerHTML = '<p class="report-empty-text">No report periods configured.</p>';
    return;
  }

  container.innerHTML = reports.map(r => {
    const isAvail = r.is_available;
    const badgeClass = isAvail ? 'badge-available' : 'badge-locked';
    const badgeIcon = isAvail ? '<i class="fa-solid fa-circle-check"></i>' : '<i class="fa-solid fa-lock"></i>';
    const badgeText = isAvail ? 'Available' : 'Locked';

    return `
      <div class="report-card ${isAvail ? 'available' : 'locked'}">
        <div class="report-card-header">
          <div class="report-period-badge">${r.period_days} DAYS</div>
          <div class="report-status-badge ${badgeClass}">${badgeIcon} ${badgeText}</div>
        </div>
        <h4 class="report-card-title">${escapeHtml(r.title)}</h4>
        <p class="report-card-subtitle">${escapeHtml(r.subtitle)}</p>
        <div class="report-card-meta">
          <i class="fa-solid fa-calendar-days"></i>
          <span>${r.formatted_date_range || `${r.period_days} Days History`}</span>
        </div>
        <div class="report-card-status-msg">
          ${escapeHtml(r.status_message)}
        </div>
        <div class="report-card-actions">
          <button class="btn btn-secondary report-btn-view" 
                  ${!isAvail ? 'disabled' : ''} 
                  onclick="openReportPreview(${r.period_days})">
            <i class="fa-solid fa-eye"></i> View Report
          </button>
          <button class="btn btn-primary report-btn-download" 
                  id="btnDownloadReport${r.period_days}"
                  ${!isAvail ? 'disabled' : ''} 
                  onclick="downloadReportPdf(${r.period_days})">
            <i class="fa-solid fa-file-pdf"></i> Download PDF
          </button>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Opens the interactive in-app Report Preview Modal and loads structured report data.
 */
async function openReportPreview(periodDays) {
  const modal = document.getElementById('reportPreviewModal');
  const content = document.getElementById('reportPreviewContent');
  const title = document.getElementById('reportPreviewTitle');
  if (!modal || !content) return;

  currentReportPeriod = periodDays;
  modal.style.display = 'flex';
  document.body.classList.add('modal-open');

  if (title) {
    title.innerHTML = `<i class="fa-solid fa-file-waveform"></i> ${periodDays}-Day FitQuest Progress Report`;
  }

  // Show loading skeleton
  content.innerHTML = `
    <div class="report-preview-loading">
      <div class="spinner-border" style="width: 2.5rem; height: 2.5rem; border: 3px solid #e2e8f0; border-top-color: #84cc16; border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
      <p style="margin-top: 14px; font-weight: 600; color: var(--text-secondary);">Preparing your ${periodDays}-day progress report...</p>
    </div>
  `;

  const apiBase = getReportsApiBase();

  try {
    const res = await fetch(`${apiBase}/reports/${periodDays}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Failed to generate progress report');
    }

    const report = await res.json();
    renderReportPreviewContent(report);
  } catch (err) {
    content.innerHTML = `
      <div class="report-empty-state error" style="padding: 40px 20px;">
        <i class="fa-solid fa-triangle-exclamation" style="font-size: 2.5rem; color: #ef4444; margin-bottom: 12px;"></i>
        <h4 style="margin-bottom: 6px;">Could Not Load Report</h4>
        <p style="color: var(--text-secondary); max-width: 420px; margin: 0 auto 16px;">${escapeHtml(err.message)}</p>
        <button class="btn btn-secondary" onclick="openReportPreview(${periodDays})">Try Again</button>
      </div>
    `;
  }
}

/**
 * Renders the structured progress report inside the preview modal.
 */
function renderReportPreviewContent(report) {
  const content = document.getElementById('reportPreviewContent');
  if (!content) return;

  const ov = report.overview;
  const wp = report.workout_progress;
  const mp = report.movement_progress;
  const rr = report.readiness_recovery;
  const nut = report.nutrition;
  const ach = report.achievements;
  const wc = report.what_changed;

  const formQualityText = ov.avg_form_score ? `${ov.avg_form_score}%` : '--';
  const strongestText = (mp.strongest_areas && mp.strongest_areas.length > 0) ? mp.strongest_areas.join(', ') : 'General movement control';
  const focusText = (mp.focus_areas && mp.focus_areas.length > 0) ? mp.focus_areas.join(', ') : 'Maintain smooth repetitions';

  let exercisesHtml = '';
  if (wp.top_exercises && wp.top_exercises.length > 0) {
    exercisesHtml = `
      <div class="report-exercises-table-box">
        <table class="report-table">
          <thead>
            <tr>
              <th>Exercise</th>
              <th>Muscle Focus</th>
              <th style="text-align: center;">Sets</th>
              <th style="text-align: center;">Reps</th>
              <th style="text-align: center;">Avg Form</th>
            </tr>
          </thead>
          <tbody>
            ${wp.top_exercises.map(e => `
              <tr>
                <td style="font-weight: 700;">${escapeHtml(e.exercise_name)}</td>
                <td style="color: var(--text-secondary);">${escapeHtml(e.muscle_group || 'Compound')}</td>
                <td style="text-align: center;">${e.total_sets}</td>
                <td style="text-align: center;">${e.total_reps}</td>
                <td style="text-align: center;"><span class="report-form-pill">${e.avg_form_score > 0 ? e.avg_form_score + '%' : '--'}</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  content.innerHTML = `
    <div class="report-preview-sheet">
      
      <!-- REPORT HEADER -->
      <div class="report-sheet-header">
        <div class="report-sheet-brand">
          <span class="report-brand-name"><i class="fa-solid fa-dumbbell"></i> FITQUEST</span>
          <span class="report-sheet-date">${escapeHtml(report.header.formatted_date_range)}</span>
        </div>
        <h2 class="report-sheet-title">${escapeHtml(report.header.report_title)}</h2>
        <div class="report-sheet-user">
          <span><b>Athlete:</b> ${escapeHtml(report.header.user_name)}</span>
          <span class="dot-separator">•</span>
          <span><b>Status:</b> ${ov.workouts_completed > 0 ? 'Active Athlete' : 'New Journey'}</span>
        </div>
      </div>

      <!-- OVERVIEW STATS GRID (6 TILES) -->
      <div class="report-sheet-stats-grid">
        <div class="report-stat-tile">
          <div class="report-stat-lbl">Workouts</div>
          <div class="report-stat-num highlight">${ov.workouts_completed}</div>
        </div>
        <div class="report-stat-tile">
          <div class="report-stat-lbl">Active Days</div>
          <div class="report-stat-num">${ov.total_active_days}</div>
        </div>
        <div class="report-stat-tile">
          <div class="report-stat-lbl">Training Time</div>
          <div class="report-stat-num">${ov.total_duration_min} <span style="font-size: 0.8rem; font-weight: normal;">min</span></div>
        </div>
        <div class="report-stat-tile">
          <div class="report-stat-lbl">Total Reps</div>
          <div class="report-stat-num highlight">${ov.total_reps}</div>
        </div>
        <div class="report-stat-tile">
          <div class="report-stat-lbl">Avg Form Quality</div>
          <div class="report-stat-num highlight-lime">${formQualityText}</div>
        </div>
        <div class="report-stat-tile">
          <div class="report-stat-lbl">Longest Streak</div>
          <div class="report-stat-num">${ov.longest_streak}d</div>
        </div>
      </div>

      <!-- SECTION: AI COACH SUMMARY BANNER -->
      <div class="report-sheet-ai-card">
        <div class="report-ai-header">
          <i class="fa-solid fa-wand-magic-sparkles"></i>
          <span>FitQuest AI Coach Summary</span>
        </div>
        <p class="report-ai-text">"${escapeHtml(report.ai_summary)}"</p>
      </div>

      <!-- SECTION: WORKOUT PROGRESS -->
      <div class="report-section-card">
        <div class="report-sec-title">
          <i class="fa-solid fa-person-running"></i>
          <h3>Workout Progress</h3>
        </div>
        <p class="report-sec-desc">${escapeHtml(wp.summary_message)} Consistency: <b>${escapeHtml(wp.consistency_trend)}</b> (${ov.consistency_percentage}% of days active).</p>
        ${exercisesHtml}
      </div>

      <!-- TWO-COLUMN GRID: MOVEMENT & READINESS -->
      <div class="report-two-column-grid">
        
        <!-- MOVEMENT / FORM PROGRESS -->
        <div class="report-section-card">
          <div class="report-sec-title">
            <i class="fa-solid fa-bullseye"></i>
            <h3>Movement & Form Quality</h3>
          </div>
          <p class="report-sec-desc">${escapeHtml(mp.control_summary)}</p>
          <div class="report-info-pair">
            <span class="pair-lbl">Strongest Areas:</span>
            <span class="pair-val">${escapeHtml(strongestText)}</span>
          </div>
          <div class="report-info-pair">
            <span class="pair-lbl">Focus Areas:</span>
            <span class="pair-val">${escapeHtml(focusText)}</span>
          </div>
        </div>

        <!-- READINESS & RECOVERY -->
        <div class="report-section-card">
          <div class="report-sec-title">
            <i class="fa-solid fa-heart-pulse"></i>
            <h3>Readiness & Recovery</h3>
          </div>
          <p class="report-sec-desc">${escapeHtml(rr.observation)}</p>
          <div class="report-info-pair">
            <span class="pair-lbl">Readiness Status:</span>
            <span class="pair-val highlight">${escapeHtml(rr.readiness_status.replace(/_/g, ' '))} ${rr.readiness_score ? `(${rr.readiness_score}/100)` : ''}</span>
          </div>
          <div class="report-info-pair">
            <span class="pair-lbl">Training Load Zone:</span>
            <span class="pair-val">${escapeHtml(rr.training_load_zone.replace(/_/g, ' '))}</span>
          </div>
        </div>

      </div>

      <!-- WHAT CHANGED THIS PERIOD -->
      <div class="report-section-card">
        <div class="report-sec-title">
          <i class="fa-solid fa-chart-line"></i>
          <h3>What Changed This Period</h3>
        </div>
        <p class="report-sec-desc"><b>Progression:</b> ${escapeHtml(wc.comparison_summary)}</p>
        ${wc.has_sufficient_comparison_data ? `
          <div class="report-comparison-bar">
            <div class="comp-box">
              <span class="comp-lbl">First Half:</span>
              <span class="comp-val"><b>${wc.first_half_workouts}</b> workouts (Avg Form: ${wc.first_half_avg_form ? wc.first_half_avg_form + '%' : '--'})</span>
            </div>
            <div class="comp-arrow"><i class="fa-solid fa-arrow-right"></i></div>
            <div class="comp-box">
              <span class="comp-lbl">Second Half:</span>
              <span class="comp-val"><b>${wc.second_half_workouts}</b> workouts (Avg Form: ${wc.second_half_avg_form ? wc.second_half_avg_form + '%' : '--'})</span>
            </div>
          </div>
        ` : ''}
      </div>

      <!-- NUTRITION & ACHIEVEMENTS TWO-COLUMN -->
      <div class="report-two-column-grid">
        
        <!-- NUTRITION -->
        <div class="report-section-card">
          <div class="report-sec-title">
            <i class="fa-solid fa-apple-whole"></i>
            <h3>Nutrition Tracking</h3>
          </div>
          <p class="report-sec-desc">${escapeHtml(nut.adherence_summary)}</p>
          ${nut.has_nutrition_profile ? `
            <div class="report-info-pair">
              <span class="pair-lbl">Daily Target:</span>
              <span class="pair-val">${nut.daily_calories_target} kcal (${nut.protein_g_target || 0}g protein)</span>
            </div>
          ` : ''}
        </div>

        <!-- ACHIEVEMENTS -->
        <div class="report-section-card">
          <div class="report-sec-title">
            <i class="fa-solid fa-trophy"></i>
            <h3>Milestones & Highlights</h3>
          </div>
          <p class="report-sec-desc">${escapeHtml(ach.highlights_summary)}</p>
          <div class="report-info-pair">
            <span class="pair-lbl">Longest Streak:</span>
            <span class="pair-val highlight">${ach.longest_streak} Days Active</span>
          </div>
        </div>

      </div>

      <!-- YOUR NEXT STEPS -->
      <div class="report-section-card next-steps-card">
        <div class="report-sec-title">
          <i class="fa-solid fa-list-check"></i>
          <h3>Your Next Steps</h3>
        </div>
        <div class="report-steps-list">
          ${report.next_steps.map((step, idx) => `
            <div class="report-step-item">
              <span class="step-num">${idx + 1}</span>
              <span class="step-text">${escapeHtml(step)}</span>
            </div>
          `).join('')}
        </div>
      </div>

    </div>
  `;
}

/**
 * Downloads the progress report as a branded PDF file.
 */
async function downloadReportPdf(periodDays) {
  const period = periodDays || currentReportPeriod;
  if (!period) return;

  const btn = document.getElementById(`btnDownloadReport${period}`);
  const modalBtn = document.getElementById('reportDownloadPdfBtn');

  const origBtnText = btn ? btn.innerHTML : '';
  const origModalBtnText = modalBtn ? modalBtn.innerHTML : '';

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Generating...';
  }
  if (modalBtn) {
    modalBtn.disabled = true;
    modalBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Generating PDF...';
  }

  const apiBase = getReportsApiBase();

  try {
    const response = await fetch(`${apiBase}/reports/${period}/pdf`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    if (!response.ok) {
      const errJson = await response.json().catch(() => ({}));
      throw new Error(errJson.detail || 'Failed to download PDF report');
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = `fitquest_${period}day_progress_report.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } catch (err) {
    alert(err.message || 'Error generating PDF report');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origBtnText;
    }
    if (modalBtn) {
      modalBtn.disabled = false;
      modalBtn.innerHTML = origModalBtnText;
    }
  }
}

/**
 * Modal helper to download from inside the open preview modal.
 */
function downloadCurrentReportPdf() {
  if (currentReportPeriod) {
    downloadReportPdf(currentReportPeriod);
  }
}

/**
 * Closes the in-app report preview modal.
 */
function closeReportPreview() {
  const modal = document.getElementById('reportPreviewModal');
  if (modal) {
    modal.style.display = 'none';
  }
  document.body.classList.remove('modal-open');
}

/**
 * HTML escape helper to prevent XSS injection.
 */
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.innerText = text;
  return div.innerHTML;
}
