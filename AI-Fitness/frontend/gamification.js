/**
 * FitQuest Gamification Manager (Streaks, Activity Calendar & Badges)
 * Fetches and renders streak metrics, weekly/monthly activity calendars, achievement badges, and toast notifications.
 */

const STREAK_API_BASE = (window.getFitQuestApiBase ? window.getFitQuestApiBase() : (window.API_BASE || 'https://fitquest-backend-1brv.onrender.com/api/v1')) + '/streaks';
const ACH_API_BASE = (window.getFitQuestApiBase ? window.getFitQuestApiBase() : (window.API_BASE || 'https://fitquest-backend-1brv.onrender.com/api/v1')) + '/achievements';

let activeStreakData = null;
let activeAchievementsData = null;

document.addEventListener('DOMContentLoaded', () => {
  // If user is already authenticated, load initial gamification data
  if (typeof authToken !== 'undefined' && authToken) {
    loadGamificationData();
  }
});

/**
 * Loads streak metrics and achievements from backend APIs
 */
async function loadGamificationData() {
  if (typeof authToken === 'undefined' || !authToken) return;

  try {
    const [streakRes, achRes] = await Promise.all([
      fetch(`${STREAK_API_BASE}/me`, { headers: { 'Authorization': `Bearer ${authToken}` } }),
      fetch(`${ACH_API_BASE}/me`, { headers: { 'Authorization': `Bearer ${authToken}` } })
    ]);

    if (streakRes.ok) {
      activeStreakData = await streakRes.json();
      renderHomeStreakWidget(activeStreakData);
      renderProfileStreakAndCalendar(activeStreakData);
    }

    if (achRes.ok) {
      activeAchievementsData = await achRes.json();
      renderProfileAchievements(activeAchievementsData);
    }
  } catch (err) {
    console.warn('[FitQuest Gamification]: Failed to load streaks/achievements:', err);
  }
}

/**
 * Renders compact streak card & weekly calendar strip on Home Dashboard (#homeView)
 */
function renderHomeStreakWidget(streak) {
  const container = document.getElementById('homeStreakWidget');
  if (!container || !streak) return;

  const currentStreak = streak.current_streak;
  const longestStreak = streak.longest_streak;

  // Build weekly calendar strip (last 7 days including today)
  const today = new Date();
  const weekDays = [];
  const activeDateSet = new Set(streak.active_dates || []);

  for (let i = 6; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const isoDate = d.toISOString().split('T')[0];
    const dayName = d.toLocaleDateString('en-US', { weekday: 'narrow' });
    const isActive = activeDateSet.has(isoDate);

    weekDays.push(`
      <div class="weekly-dot-col ${isActive ? 'active' : ''}" title="${isoDate}">
        <span class="day-lbl">${dayName}</span>
        <div class="dot-icon">
          ${isActive ? '<i class="fa-solid fa-fire"></i>' : '⚪'}
        </div>
      </div>
    `);
  }

  container.innerHTML = `
    <div class="dash-card streak-dash-card">
      <div class="streak-card-header">
        <div class="dash-card-icon orange">
          <i class="fa-solid fa-fire"></i>
        </div>
        <div class="streak-header-info">
          <span class="streak-small-title">YOUR STREAK</span>
          <h2 class="streak-count-title">${currentStreak} ${currentStreak === 1 ? 'DAY' : 'DAYS'}</h2>
        </div>
      </div>

      <div class="weekly-strip-container">
        ${weekDays.join('')}
      </div>

      <div class="streak-card-footer">
        <span class="best-streak-lbl">Best Streak: <strong>${longestStreak} days</strong></span>
        <button class="btn btn-sm btn-secondary" onclick="openProfileAchievementsTab()">
          <i class="fa-solid fa-trophy"></i> View Badges
        </button>
      </div>
    </div>
  `;
}

/**
 * Renders Streak metrics and Monthly Workout Calendar on Profile View (#profileView)
 */
function renderProfileStreakAndCalendar(streak) {
  const statsContainer = document.getElementById('profStreakStatsContainer');
  const calendarContainer = document.getElementById('profCalendarContainer');
  if (!streak) return;

  if (statsContainer) {
    statsContainer.innerHTML = `
      <div class="prof-metric-box highlight-box">
        <div class="prof-metric-lbl"><i class="fa-solid fa-fire"></i> Current Streak</div>
        <div class="prof-metric-val fire">${streak.current_streak} Days</div>
      </div>
      <div class="prof-metric-box">
        <div class="prof-metric-lbl"><i class="fa-solid fa-crown"></i> Best Streak</div>
        <div class="prof-metric-val">${streak.longest_streak} Days</div>
      </div>
      <div class="prof-metric-box">
        <div class="prof-metric-lbl"><i class="fa-solid fa-calendar-check"></i> Total Active Days</div>
        <div class="prof-metric-val">${streak.total_workout_days} Days</div>
      </div>
      <div class="prof-metric-box">
        <div class="prof-metric-lbl"><i class="fa-solid fa-dumbbell"></i> Total Valid Workouts</div>
        <div class="prof-metric-val">${streak.total_valid_workouts} Sets</div>
      </div>
    `;
  }

  if (calendarContainer) {
    renderMonthlyCalendarGrid(calendarContainer, streak.active_dates || []);
  }
}

/**
 * Renders interactive monthly workout activity grid
 */
function renderMonthlyCalendarGrid(container, activeDates) {
  const activeSet = new Set(activeDates);
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();

  const monthName = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const firstDay = new Date(year, month, 1).getDay(); // 0 = Sun, 1 = Mon...
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  // Shift to Mon-Sun index (0 = Mon, 6 = Sun)
  const startOffset = (firstDay + 6) % 7;

  const daysHeader = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  let cells = [];

  for (let i = 0; i < startOffset; i++) {
    cells.push('<div class="cal-cell empty"></div>');
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const monthStr = String(month + 1).padStart(2, '0');
    const dayStr = String(day).padStart(2, '0');
    const dateKey = `${year}-${monthStr}-${dayStr}`;
    const isActive = activeSet.has(dateKey);
    const isToday = day === now.getDate();

    cells.push(`
      <div class="cal-cell ${isActive ? 'active' : ''} ${isToday ? 'today' : ''}" title="${dateKey}">
        <span class="cal-day-num">${day}</span>
        <span class="cal-status-icon">${isActive ? '<i class="fa-solid fa-fire"></i>' : ''}</span>
      </div>
    `);
  }

  container.innerHTML = `
    <div class="calendar-card">
      <div class="calendar-header">
        <h3><i class="fa-solid fa-calendar-days"></i> Activity Calendar — ${monthName}</h3>
      </div>
      <div class="calendar-grid-header">
        ${daysHeader.map(d => `<span>${d}</span>`).join('')}
      </div>
      <div class="calendar-grid-body">
        ${cells.join('')}
      </div>
    </div>
  `;
}

/**
 * Renders the 8 FitQuest Achievements & Badges grid on Profile View
 */
function renderProfileAchievements(achievements) {
  const container = document.getElementById('profAchievementsGrid');
  if (!container || !achievements) return;

  const cardsHtml = achievements.map(ach => {
    const isEarned = ach.earned;
    const progressPct = Math.min(100, Math.round((ach.progress / ach.target) * 100));

    return `
      <div class="achievement-card ${isEarned ? 'earned' : 'locked'}">
        <div class="ach-icon-wrapper">
          <i class="fa-solid ${ach.icon}"></i>
          ${isEarned ? '<span class="check-badge"><i class="fa-solid fa-check"></i></span>' : '<span class="lock-badge"><i class="fa-solid fa-lock"></i></span>'}
        </div>
        <div class="ach-info">
          <h4>${escapeHTML(ach.title)}</h4>
          <p>${escapeHTML(ach.description)}</p>
          <div class="ach-progress-bar">
            <div class="ach-progress-fill" style="width: ${progressPct}%;"></div>
          </div>
          <div class="ach-footer-meta">
            <span class="ach-progress-text">${ach.progress} / ${ach.target}</span>
            ${isEarned ? `<span class="ach-earned-tag">Unlocked</span>` : `<span class="ach-locked-tag">Locked</span>`}
          </div>
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = cardsHtml;
}

/**
 * Triggers non-intrusive Toast notification for extended streaks or unlocked achievements
 */
function showGamificationNotification(title, message, icon = 'fa-fire') {
  const toast = document.createElement('div');
  toast.className = 'fitquest-toast-notification';
  toast.innerHTML = `
    <div class="toast-icon">
      <i class="fa-solid ${icon}"></i>
    </div>
    <div class="toast-body">
      <strong>${escapeHTML(title)}</strong>
      <span>${escapeHTML(message)}</span>
    </div>
    <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
  `;

  document.body.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('show');
  }, 50);

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 400);
  }, 5000);
}

/**
 * Navigates directly to Achievements section in Profile tab
 */
function openProfileAchievementsTab() {
  if (typeof switchTab === 'function') {
    switchTab('profileView');
  }
}

function escapeHTML(str) {
  if (!str) return '';
  return String(str).replace(/[&<>'"]/g, tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
}
