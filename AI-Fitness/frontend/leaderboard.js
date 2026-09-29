/**
 * FitQuest Leaderboard V1 Controller
 * Manages fetching, period switching, and rendering for the Leaderboard view.
 * Features:
 *  - Weekly, Monthly, and All-Time modes
 *  - 5-Component FitQuest Score display
 *  - Top 3 Podium treatment
 *  - User's own standing card with rank change & points to next rank
 *  - Empty, Loading, and Error states
 *  - Deterministic and real data only
 */

const LEADERBOARD_API_BASE = (window.getFitQuestApiBase ? window.getFitQuestApiBase() : (window.API_BASE || 'https://fitquest-backend-1brv.onrender.com/api/v1')) + '/leaderboard';
let activeLeaderboardPeriod = 'weekly';
let isLeaderboardLoading = false;

document.addEventListener('DOMContentLoaded', () => {
  initLeaderboardUI();
});

/**
 * Initializes UI event listeners for Leaderboard mode switcher
 */
function initLeaderboardUI() {
  const periodBtns = document.querySelectorAll('.leaderboard-period-btn');
  periodBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const selectedPeriod = btn.getAttribute('data-period');
      if (selectedPeriod && selectedPeriod !== activeLeaderboardPeriod) {
        switchLeaderboardPeriod(selectedPeriod);
      }
    });
  });
}

/**
 * Switches the active period tab and fetches corresponding data
 */
function switchLeaderboardPeriod(period) {
  activeLeaderboardPeriod = period;

  // Update button active state
  const periodBtns = document.querySelectorAll('.leaderboard-period-btn');
  periodBtns.forEach((btn) => {
    if (btn.getAttribute('data-period') === period) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  loadLeaderboardView(period);
}

/**
 * Primary loader function called when navigating to Leaderboard tab
 */
async function loadLeaderboardView(period = null) {
  if (period) {
    activeLeaderboardPeriod = period;
  }

  const token = typeof getAuthToken === 'function' ? getAuthToken() : (localStorage.getItem('fitquest_token') || null);
  if (!token) {
    renderLeaderboardError('Please log in to view the FitQuest Leaderboard.');
    return;
  }

  setLeaderboardLoading(true);

  try {
    const response = await fetch(`${LEADERBOARD_API_BASE}?period=${activeLeaderboardPeriod}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Failed to load leaderboard (${response.status})`);
    }

    const data = await response.json();
    renderLeaderboard(data);
  } catch (err) {
    console.error('[Leaderboard] Error fetching data:', err);
    renderLeaderboardError(err.message || 'Unable to connect to leaderboard server.');
  } finally {
    setLeaderboardLoading(false);
  }
}

/**
 * Toggles loading skeleton / indicator
 */
function setLeaderboardLoading(isLoading) {
  isLeaderboardLoading = isLoading;
  const skeleton = document.getElementById('leaderboardLoadingSkeleton');
  const content = document.getElementById('leaderboardContentArea');
  const errorBox = document.getElementById('leaderboardErrorState');

  if (skeleton) skeleton.style.display = isLoading ? 'block' : 'none';
  if (content && isLoading) content.style.display = 'none';
  if (errorBox && isLoading) errorBox.style.display = 'none';
}

/**
 * Displays error box with retry button
 */
function renderLeaderboardError(message) {
  const skeleton = document.getElementById('leaderboardLoadingSkeleton');
  const content = document.getElementById('leaderboardContentArea');
  const errorBox = document.getElementById('leaderboardErrorState');
  const errorMsg = document.getElementById('leaderboardErrorMessage');

  if (skeleton) skeleton.style.display = 'none';
  if (content) content.style.display = 'none';
  if (errorBox) {
    errorBox.style.display = 'block';
    if (errorMsg) errorMsg.innerText = message;
  }
}

/**
 * Renders the complete leaderboard view
 */
function renderLeaderboard(data) {
  const skeleton = document.getElementById('leaderboardLoadingSkeleton');
  const content = document.getElementById('leaderboardContentArea');
  const errorBox = document.getElementById('leaderboardErrorState');

  if (skeleton) skeleton.style.display = 'none';
  if (errorBox) errorBox.style.display = 'none';
  if (content) content.style.display = 'block';

  // 1. Render Current User's Standing Card
  renderCurrentUserStanding(data.current_user);

  // 2. Render Leaderboard Entries or Empty State
  const entriesContainer = document.getElementById('leaderboardListContainer');
  const emptyStateContainer = document.getElementById('leaderboardEmptyState');

  if (!entriesContainer) return;

  const entries = data.entries || [];

  if (entries.length === 0) {
    entriesContainer.innerHTML = '';
    if (emptyStateContainer) {
      emptyStateContainer.style.display = 'block';
      const emptyMsg = document.getElementById('leaderboardEmptyMessage');
      if (emptyMsg) {
        if (data.current_user && !data.current_user.is_visible) {
          emptyMsg.innerText = 'Leaderboard is currently empty. You are also set to private mode in your Profile.';
        } else {
          emptyMsg.innerText = 'No workout activity recorded yet for this period. Be the first to train and claim the #1 spot!';
        }
      }
    }
    return;
  }

  if (emptyStateContainer) {
    emptyStateContainer.style.display = 'none';
  }

  // Check if single athlete community message is needed
  const singleNotice = document.getElementById('leaderboardSingleAthleteNotice');
  if (singleNotice) {
    if (entries.length === 1 && data.current_user && data.current_user.rank === 1) {
      singleNotice.style.display = 'flex';
    } else {
      singleNotice.style.display = 'none';
    }
  }

  // Render list of athletes
  let html = '';
  entries.forEach((entry) => {
    const isTop1 = entry.rank === 1;
    const isTop2 = entry.rank === 2;
    const isTop3 = entry.rank === 3;
    const isCurrentUser = data.current_user && data.current_user.user_id === entry.user_id;

    let rankBadgeClass = 'rank-regular';
    let rankIcon = entry.rank;
    if (isTop1) {
      rankBadgeClass = 'rank-gold';
      rankIcon = '<span class="medal-emoji">🥇</span> 1';
    } else if (isTop2) {
      rankBadgeClass = 'rank-silver';
      rankIcon = '<span class="medal-emoji">🥈</span> 2';
    } else if (isTop3) {
      rankBadgeClass = 'rank-bronze';
      rankIcon = '<span class="medal-emoji">🥉</span> 3';
    }

    // Format badges
    let badgesHtml = '';
    if (entry.badges && entry.badges.length > 0) {
      badgesHtml = '<div class="lb-athlete-badges">';
      entry.badges.forEach((b) => {
        badgesHtml += `<span class="lb-badge-icon" title="${escapeHTML(b.title)}"><i class="fa-solid ${escapeHTML(b.icon)}"></i></span>`;
      });
      badgesHtml += '</div>';
    }

    html += `
      <div class="leaderboard-item ${isCurrentUser ? 'is-current-user' : ''} ${isTop1 ? 'item-top1' : ''} ${isTop2 ? 'item-top2' : ''} ${isTop3 ? 'item-top3' : ''}">
        <div class="lb-rank-badge ${rankBadgeClass}">
          ${rankIcon}
        </div>
        <div class="lb-avatar-initial">${escapeHTML(entry.avatar_initial || 'A')}</div>
        <div class="lb-athlete-info">
          <div class="lb-athlete-name-row">
            <span class="lb-athlete-name">${escapeHTML(entry.display_name)}</span>
            ${isCurrentUser ? '<span class="lb-you-tag">YOU</span>' : ''}
          </div>
          ${badgesHtml}
        </div>
        <div class="lb-streak-pill" title="${entry.streak} day streak">
          <i class="fa-solid fa-fire lb-flame-icon"></i>
          <span>${entry.streak}d streak</span>
        </div>
        <div class="lb-score-box">
          <span class="lb-score-number">${Number(entry.fitquest_score).toLocaleString()}</span>
          <span class="lb-score-unit">FitScore</span>
        </div>
      </div>
    `;
  });

  entriesContainer.innerHTML = html;
}

/**
 * Renders the authenticated user's position card
 */
function renderCurrentUserStanding(currentUser) {
  const card = document.getElementById('userStandingCard');
  if (!card) return;

  if (!currentUser) {
    card.style.display = 'none';
    return;
  }

  card.style.display = 'block';

  const rankEl = document.getElementById('myStandingRank');
  const nameEl = document.getElementById('myStandingName');
  const scoreEl = document.getElementById('myStandingScore');
  const streakEl = document.getElementById('myStandingStreak');
  const rankChangeEl = document.getElementById('myStandingRankChange');
  const pointsToNextEl = document.getElementById('myStandingPointsToNext');
  const messageEl = document.getElementById('myStandingMessage');

  if (nameEl) nameEl.innerText = currentUser.display_name;
  if (scoreEl) scoreEl.innerText = `${Number(currentUser.fitquest_score).toLocaleString()} FitScore`;
  if (streakEl) streakEl.innerText = `🔥 ${currentUser.streak} day streak`;

  if (rankEl) {
    if (currentUser.rank !== null && currentUser.rank !== undefined) {
      rankEl.innerText = `#${currentUser.rank}`;
      rankEl.classList.remove('unranked');
    } else {
      rankEl.innerText = '--';
      rankEl.classList.add('unranked');
    }
  }

  // Rank change display (e.g. ↑ 3 positions this period)
  if (rankChangeEl) {
    if (currentUser.rank_change !== null && currentUser.rank_change !== undefined && currentUser.rank_change !== 0) {
      rankChangeEl.style.display = 'inline-flex';
      if (currentUser.rank_change > 0) {
        rankChangeEl.className = 'standing-movement-pill movement-up';
        rankChangeEl.innerHTML = `<i class="fa-solid fa-arrow-up"></i> ${currentUser.rank_change} position${currentUser.rank_change > 1 ? 's' : ''} this period`;
      } else {
        const absChange = Math.abs(currentUser.rank_change);
        rankChangeEl.className = 'standing-movement-pill movement-down';
        rankChangeEl.innerHTML = `<i class="fa-solid fa-arrow-down"></i> ${absChange} position${absChange > 1 ? 's' : ''} this period`;
      }
    } else {
      rankChangeEl.style.display = 'none';
    }
  }

  // Points to next rank display
  if (pointsToNextEl) {
    if (currentUser.points_to_next_rank !== null && currentUser.points_to_next_rank !== undefined && currentUser.rank !== 1) {
      pointsToNextEl.style.display = 'inline-flex';
      const targetRank = currentUser.rank ? currentUser.rank - 1 : 'Leaderboard';
      pointsToNextEl.innerText = `${Number(currentUser.points_to_next_rank).toLocaleString()} points to Rank #${targetRank}`;
    } else {
      pointsToNextEl.style.display = 'none';
    }
  }

  // Encouraging contextual message
  if (messageEl) {
    if (currentUser.message) {
      messageEl.innerText = currentUser.message;
      messageEl.style.display = 'block';
    } else {
      messageEl.style.display = 'none';
    }
  }
}

/**
 * HTML Escaping helper to protect against injection
 */
function escapeHTML(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Export functions to window for global access
window.loadLeaderboardView = loadLeaderboardView;
window.switchLeaderboardPeriod = switchLeaderboardPeriod;
