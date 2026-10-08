/**
 * FitQuest Authentication & User Profile Manager
 * Manages Registration, Login, Token Storage, Persistent Sessions, Profile Updates, and Protected Route Redirection.
 */

const AUTH_API_BASE = (window.getFitQuestApiBase ? window.getFitQuestApiBase() : (window.API_BASE || 'https://fitquest-backend-1brv.onrender.com/api/v1')) + '/auth';

// State
let currentUser = null;
let authToken = localStorage.getItem('fitquest_token') || null;

document.addEventListener('DOMContentLoaded', () => {
  initAuthUI();
  checkPersistentSession();
});

/**
 * Initializes Event Listeners for Login, Register, Profile Edit, Logout, and User Dropdown
 */
function initAuthUI() {
  // Auth Form Tabs Switcher (Login <-> Signup)
  const authTabs = document.querySelectorAll('.auth-tab-btn');
  authTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      authTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const formType = tab.getAttribute('data-auth-form');
      showAuthFormContainer(formType === 'login' ? 'loginFormContainer' : 'registerFormContainer');
      clearAuthAlerts();
    });
  });

  // Forgot Password Link Click
  const forgotPassLink = document.getElementById('forgotPassLink');
  if (forgotPassLink) {
    forgotPassLink.addEventListener('click', (e) => {
      e.preventDefault();
      clearAuthAlerts();
      showAuthFormContainer('forgotPasswordFormContainer');
    });
  }

  // Back to Login Links Click
  const backToLoginLinks = document.querySelectorAll('.back-to-login-link');
  backToLoginLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      clearAuthAlerts();
      const loginTab = document.querySelector('.auth-tab-btn[data-auth-form="login"]');
      if (loginTab) {
        authTabs.forEach(t => t.classList.remove('active'));
        loginTab.classList.add('active');
      }
      showAuthFormContainer('loginFormContainer');
    });
  });

  // Forgot Password Form Submission
  const forgotPasswordForm = document.getElementById('forgotPasswordForm');
  if (forgotPasswordForm) {
    forgotPasswordForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearAuthAlerts();

      const email = document.getElementById('forgotEmail').value.trim();
      if (!email) {
        showAuthError('Please enter a valid email address.');
        return;
      }

      setAuthBtnLoading('forgotBtn', true, 'Sending...');
      try {
        const response = await fetch(`${AUTH_API_BASE}/forgot-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email })
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || 'Failed to process password reset request.');
        }

        showAuthSuccess(data.message || 'If an account exists for this email, password reset instructions have been sent.');
      } catch (err) {
        showAuthError(err.message);
      } finally {
        setAuthBtnLoading('forgotBtn', false, 'Send Reset Link');
      }
    });
  }

  // Reset Password Form Submission
  const resetPasswordForm = document.getElementById('resetPasswordForm');
  if (resetPasswordForm) {
    resetPasswordForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearAuthAlerts();

      const token = document.getElementById('resetTokenInput').value.trim();
      const newPassword = document.getElementById('newPassword').value;
      const confirmNewPassword = document.getElementById('confirmNewPassword').value;

      if (!token) {
        showAuthError('This password reset link is invalid or has expired. Please request a new one.');
        return;
      }

      if (!newPassword || newPassword.length < 6) {
        showAuthError('Password must be at least 6 characters long.');
        return;
      }

      if (newPassword !== confirmNewPassword) {
        showAuthError('Passwords do not match. Please re-enter your new password.');
        return;
      }

      setAuthBtnLoading('resetBtn', true, 'Updating...');
      try {
        const response = await fetch(`${AUTH_API_BASE}/reset-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token, new_password: newPassword })
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || 'This password reset link is invalid or has expired. Please request a new one.');
        }

        showAuthSuccess('Your password has been successfully reset. Please log in with your new password.');
        setTimeout(() => {
          showAuthFormContainer('loginFormContainer');
        }, 2500);
      } catch (err) {
        showAuthError(err.message);
      } finally {
        setAuthBtnLoading('resetBtn', false, 'Reset Password');
      }
    });
  }

  // Check URL query parameters for reset password token (?token=...)
  const urlParams = new URLSearchParams(window.location.search);
  const resetToken = urlParams.get('token');
  if (resetToken) {
    document.getElementById('resetTokenInput').value = resetToken;
    showAuthFormContainer('resetPasswordFormContainer');
  }


  // Login Form Submission
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearAuthAlerts();

      const email = document.getElementById('loginEmail').value.trim();
      const password = document.getElementById('loginPassword').value;

      if (!email || !password) {
        showAuthError('Please enter both email and password.');
        return;
      }

      setAuthBtnLoading('loginBtn', true);
      try {
        const response = await fetch(`${AUTH_API_BASE}/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || 'Login failed. Please check your credentials.');
        }

        handleAuthSuccess(data);
      } catch (err) {
        showAuthError(err.message);
      } finally {
        setAuthBtnLoading('loginBtn', false);
      }
    });
  }

  // Register Form Submission
  const registerForm = document.getElementById('registerForm');
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearAuthAlerts();

      const name = document.getElementById('regName').value.trim();
      const email = document.getElementById('regEmail').value.trim();
      const password = document.getElementById('regPassword').value;
      const confirmPassword = document.getElementById('regConfirmPassword').value;
      const fitnessGoal = document.getElementById('regFitnessGoal').value;
      const experienceLevel = document.getElementById('regExperienceLevel').value;
      const age = document.getElementById('regAge').value ? parseInt(document.getElementById('regAge').value) : null;
      const height = document.getElementById('regHeight').value ? parseFloat(document.getElementById('regHeight').value) : null;
      const weight = document.getElementById('regWeight').value ? parseFloat(document.getElementById('regWeight').value) : null;
      const gender = document.getElementById('regGender').value || null;

      if (!name || !email || !password) {
        showAuthError('Please fill in all required fields (Name, Email, Password).');
        return;
      }

      if (password !== confirmPassword) {
        showAuthError('Passwords do not match. Please re-enter your password.');
        return;
      }

      const payload = {
        name,
        email,
        password,
        fitness_goal: fitnessGoal,
        experience_level: experienceLevel,
        age,
        height,
        weight,
        gender
      };

      setAuthBtnLoading('registerBtn', true);
      try {
        const response = await fetch(`${AUTH_API_BASE}/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || 'Registration failed. Duplicate email or invalid input.');
        }

        handleAuthSuccess(data);
      } catch (err) {
        showAuthError(err.message);
      } finally {
        setAuthBtnLoading('registerBtn', false);
      }
    });
  }

  // Profile Edit Form Submission
  const profileEditForm = document.getElementById('profileEditForm');
  if (profileEditForm) {
    profileEditForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const updatePayload = {
        name: document.getElementById('editName').value.trim(),
        fitness_goal: document.getElementById('editFitnessGoal').value,
        experience_level: document.getElementById('editExperienceLevel').value,
        age: document.getElementById('editAge').value ? parseInt(document.getElementById('editAge').value) : null,
        height: document.getElementById('editHeight').value ? parseFloat(document.getElementById('editHeight').value) : null,
        weight: document.getElementById('editWeight').value ? parseFloat(document.getElementById('editWeight').value) : null,
        gender: document.getElementById('editGender').value || null,
        leaderboard_visible: document.getElementById('editLeaderboardVisible') ? document.getElementById('editLeaderboardVisible').checked : true
      };

      try {
        const response = await fetch(`${AUTH_API_BASE}/profile`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify(updatePayload)
        });

        const updatedUser = await response.json();
        if (!response.ok) {
          throw new Error(updatedUser.detail || 'Failed to update profile.');
        }

        currentUser = updatedUser;
        renderProfilePage();
        updateUserNavBadge();
        toggleEditProfileModal(false);
        alert('Profile updated successfully!');
      } catch (err) {
        alert(`Error updating profile: ${err.message}`);
      }
    });
  }
}

/**
 * Checks for stored authentication token on page refresh
 */
async function checkPersistentSession() {
  if (!authToken) {
    showUnauthenticatedState();
    return;
  }

  try {
    const response = await fetch(`${AUTH_API_BASE}/me`, {
      method: 'GET',
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    if (!response.ok) {
      throw new Error('Token expired or invalid');
    }

    currentUser = await response.json();
    showAuthenticatedState();
  } catch (err) {
    console.warn('[FitQuest Auth]: Persistent session check failed:', err);
    logoutUser();
  }
}

function safeSwitchTab(viewId) {
  if (typeof switchTab === 'function') {
    switchTab(viewId);
  } else if (typeof window !== 'undefined' && typeof window.switchTab === 'function') {
    window.switchTab(viewId);
  }
}

/**
 * Handles successful login or registration
 */
function handleAuthSuccess(authData) {
  authToken = authData.access_token;
  currentUser = authData.user;
  localStorage.setItem('fitquest_token', authToken);

  showAuthenticatedState();
  safeSwitchTab('homeView');
}

/**
 * Logs out user and resets UI state
 */
async function logoutUser() {
  if (authToken) {
    try {
      await fetch(`${AUTH_API_BASE}/logout`, { method: 'POST' });
    } catch (e) {
      // Ignore
    }
  }

  authToken = null;
  currentUser = null;
  localStorage.removeItem('fitquest_token');

  showUnauthenticatedState();
}

/**
 * Switches UI to Authenticated state
 */
function showAuthenticatedState() {
  const landingView = document.getElementById('landingView');
  if (landingView) landingView.style.display = 'none';

  const authView = document.getElementById('authView');
  if (authView) authView.style.display = 'none';

  const appMain = document.getElementById('appMainWrapper');
  if (appMain) appMain.style.display = 'block';

  updateUserNavBadge();
  renderProfilePage();

  if (typeof loadGamificationData === 'function') {
    loadGamificationData();
  }

  // If coming from login, default to home view if active view is authView
  const currentActivePanel = document.querySelector('.view-panel.active');
  if (!currentActivePanel || currentActivePanel.id === 'authView') {
    safeSwitchTab('homeView');
  } else {
    // Reload user-specific history if currently on historyView
    if (currentActivePanel.id === 'historyView' && typeof loadWorkoutHistory === 'function') {
      loadWorkoutHistory();
    }
  }
}


/**
 * Switches UI to Unauthenticated state
 */
function showUnauthenticatedState() {
  const landingView = document.getElementById('landingView');
  if (landingView && landingView.style.display !== 'none' && !landingView.classList.contains('fade-out')) {
    // Landing page is displaying, preserve landing page display
    return;
  }

  const appMain = document.getElementById('appMainWrapper');
  if (appMain) appMain.style.display = 'none';

  const authView = document.getElementById('authView');
  if (authView) {
    authView.style.display = 'block';
    authView.classList.add('active');
  }

  const viewPanels = document.querySelectorAll('.view-panel');
  viewPanels.forEach(panel => panel.classList.remove('active'));
}

/**
 * Updates Top Navigation user badge with active user's name & dropdown menu
 */
function updateUserNavBadge() {
  const userBadge = document.getElementById('userNavBadge');
  if (!userBadge || !currentUser) return;

  const initial = (currentUser.name && currentUser.name.trim().length > 0)
    ? currentUser.name.trim().charAt(0).toUpperCase()
    : 'U';

  userBadge.innerHTML = `
    <div class="user-dropdown-container">
      <button class="user-profile-trigger" id="userProfileTrigger" onclick="toggleUserDropdown(event)" aria-expanded="false" aria-label="User profile menu">
        <div class="profile-avatar-circle">
          <span>${escapeHTML(initial)}</span>
          <span class="avatar-status-dot"></span>
        </div>
        <div class="profile-trigger-info">
          <span class="profile-trigger-name">${escapeHTML(currentUser.name)}</span>
          <span class="profile-trigger-email">${escapeHTML(currentUser.email)}</span>
        </div>
        <i class="fa-solid fa-chevron-down profile-trigger-chevron"></i>
      </button>

      <div id="userDropdownMenu" class="user-dropdown-menu" role="menu">
        <div class="dropdown-user-header">
          <div class="dropdown-avatar-circle">${escapeHTML(initial)}</div>
          <div class="dropdown-user-meta">
            <span class="dropdown-user-name">${escapeHTML(currentUser.name)}</span>
            <span class="dropdown-user-email">${escapeHTML(currentUser.email)}</span>
            <span class="dropdown-user-goal-tag"><i class="fa-solid fa-bullseye"></i> ${escapeHTML(currentUser.fitness_goal || 'General Fitness')}</span>
          </div>
        </div>

        <div class="dropdown-divider"></div>

        <button class="dropdown-action-btn" onclick="openProfileTab()" role="menuitem">
          <div class="dropdown-btn-icon"><i class="fa-solid fa-address-card"></i></div>
          <div class="dropdown-btn-text">
            <span>My Profile</span>
            <small>View & edit account details</small>
          </div>
          <i class="fa-solid fa-arrow-right dropdown-btn-arrow"></i>
        </button>

        <button class="dropdown-action-btn danger" onclick="logoutUser()" role="menuitem">
          <div class="dropdown-btn-icon danger"><i class="fa-solid fa-right-from-bracket"></i></div>
          <div class="dropdown-btn-text">
            <span>Log Out</span>
            <small>End active session</small>
          </div>
        </button>
      </div>
    </div>
  `;
}

/**
 * Toggles header user profile dropdown menu
 */
function toggleUserDropdown(event) {
  if (event) event.stopPropagation();
  const menu = document.getElementById('userDropdownMenu');
  const trigger = document.getElementById('userProfileTrigger');
  if (menu) {
    const isShowing = menu.classList.toggle('show');
    if (trigger) {
      trigger.classList.toggle('open', isShowing);
      trigger.setAttribute('aria-expanded', isShowing ? 'true' : 'false');
    }
  }
}

// Close dropdown on outside click
document.addEventListener('click', (e) => {
  const menu = document.getElementById('userDropdownMenu');
  const trigger = document.getElementById('userProfileTrigger');
  if (menu && menu.classList.contains('show')) {
    if (!menu.contains(e.target) && (!trigger || !trigger.contains(e.target))) {
      menu.classList.remove('show');
      if (trigger) {
        trigger.classList.remove('open');
        trigger.setAttribute('aria-expanded', 'false');
      }
    }
  }
});

/**
 * Calculates Body Mass Index (BMI) dynamically from weight in kg and height in cm.
 * Formula: BMI = weight (kg) / (height (m))^2
 */
function calculateBMI(weightKg, heightCm) {
  if (!weightKg || !heightCm || isNaN(weightKg) || isNaN(heightCm) || heightCm <= 0 || weightKg <= 0) {
    return null;
  }
  const heightM = heightCm / 100;
  const bmi = weightKg / (heightM * heightM);
  if (!isFinite(bmi) || isNaN(bmi) || bmi <= 0) {
    return null;
  }
  return parseFloat(bmi.toFixed(1));
}

/**
 * Returns neutral adult BMI classification label and CSS badge class.
 * Categories:
 *   < 18.5       -> Underweight
 *   18.5 - 24.9  -> Normal Range
 *   25.0 - 29.9  -> Overweight
 *   >= 30.0      -> Obesity
 */
function getBMICategory(bmi) {
  if (bmi === null || bmi === undefined || isNaN(bmi)) {
    return { label: 'Add Height & Weight', class: 'bmi-na' };
  }
  if (bmi < 18.5) {
    return { label: 'Underweight', class: 'bmi-underweight' };
  } else if (bmi <= 24.9) {
    return { label: 'Normal Range', class: 'bmi-normal' };
  } else if (bmi <= 29.9) {
    return { label: 'Overweight', class: 'bmi-overweight' };
  } else {
    return { label: 'Obesity', class: 'bmi-obesity' };
  }
}

/**
 * Renders Profile Page view with authenticated user info and dynamic Body Metrics / BMI
 */
function renderProfilePage() {
  if (!currentUser) return;

  const initialEl = document.getElementById('profAvatarInitial');
  if (initialEl) initialEl.innerText = currentUser.name.charAt(0).toUpperCase();

  const nameEl = document.getElementById('profName');
  if (nameEl) nameEl.innerText = currentUser.name;

  const emailEl = document.getElementById('profEmail');
  if (emailEl) emailEl.innerText = currentUser.email;

  const goalEl = document.getElementById('profGoal');
  if (goalEl) goalEl.innerText = currentUser.fitness_goal || 'General Fitness';

  const expEl = document.getElementById('profExperience');
  if (expEl) expEl.innerText = currentUser.experience_level || 'Beginner';

  const ageEl = document.getElementById('profAge');
  if (ageEl) ageEl.innerText = currentUser.age ? `${currentUser.age} yrs` : 'Not specified';

  const heightEl = document.getElementById('profHeight');
  if (heightEl) heightEl.innerText = currentUser.height ? `${currentUser.height} cm` : 'Not specified';

  const weightEl = document.getElementById('profWeight');
  if (weightEl) weightEl.innerText = currentUser.weight ? `${currentUser.weight} kg` : 'Not specified';

  const genderEl = document.getElementById('profGender');
  if (genderEl) genderEl.innerText = currentUser.gender || 'Not specified';

  // Body Metrics & Dynamic BMI Calculation
  const bmWeightEl = document.getElementById('profBmWeight');
  const bmHeightEl = document.getElementById('profBmHeight');
  const bmBmiEl = document.getElementById('profBmBmi');
  const bmCategoryEl = document.getElementById('profBmCategory');

  if (bmWeightEl) bmWeightEl.innerText = currentUser.weight ? `${currentUser.weight} kg` : '-- kg';
  if (bmHeightEl) bmHeightEl.innerText = currentUser.height ? `${currentUser.height} cm` : '-- cm';

  const calculatedBMI = calculateBMI(currentUser.weight, currentUser.height);
  const bmiCat = getBMICategory(calculatedBMI);

  if (bmBmiEl) {
    bmBmiEl.innerText = calculatedBMI !== null ? calculatedBMI.toFixed(1) : '--';
  }
  if (bmCategoryEl) {
    bmCategoryEl.innerText = bmiCat.label;
    bmCategoryEl.className = `prof-bmi-badge ${bmiCat.class}`;
  }

  // Leaderboard Privacy Setting
  const profLbCheckbox = document.getElementById('profLeaderboardCheckbox');
  if (profLbCheckbox) {
    profLbCheckbox.checked = currentUser.leaderboard_visible !== false;
  }

  // Load Progress Reports
  if (typeof loadProgressReports === 'function') {
    loadProgressReports();
  }
}

/**
 * Opens My Profile tab directly from header dropdown
 */
function openProfileTab() {
  safeSwitchTab('profileView');
}

/**
 * Toggles Edit Profile Modal visibility
 */
function toggleEditProfileModal(show) {
  const modal = document.getElementById('editProfileModal');
  if (!modal) return;

  if (show) {
    document.getElementById('editName').value = currentUser.name;
    document.getElementById('editFitnessGoal').value = currentUser.fitness_goal || 'General Fitness';
    document.getElementById('editExperienceLevel').value = currentUser.experience_level || 'Beginner';
    document.getElementById('editAge').value = currentUser.age || '';
    document.getElementById('editHeight').value = currentUser.height || '';
    document.getElementById('editWeight').value = currentUser.weight || '';
    document.getElementById('editGender').value = currentUser.gender || '';
    const editLbVis = document.getElementById('editLeaderboardVisible');
    if (editLbVis) {
      editLbVis.checked = currentUser.leaderboard_visible !== false;
    }
    modal.style.display = 'flex';
  } else {
    modal.style.display = 'none';
  }
}

/**
 * Returns active user ID or null if unauthenticated
 */
function getAuthenticatedUserId() {
  return currentUser ? currentUser.id : null;
}

/**
 * Returns active session token or null
 */
function getAuthToken() {
  return authToken || localStorage.getItem('fitquest_token') || null;
}

/**
 * Returns active user profile object for AI Coach
 */
function getAuthenticatedUserProfile() {
  if (!currentUser) {
    return null;
  }
  return {
    user_id: String(currentUser.id),
    fitness_goal: currentUser.fitness_goal || 'General Fitness',
    experience_level: currentUser.experience_level || 'Beginner'
  };
}

/* Helpers */
function showAuthFormContainer(containerId) {
  const containers = ['loginFormContainer', 'registerFormContainer', 'forgotPasswordFormContainer', 'resetPasswordFormContainer'];
  containers.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = id === containerId ? 'block' : 'none';
  });
}

function showAuthError(msg) {
  const alertBox = document.getElementById('authAlertBox');
  if (alertBox) {
    alertBox.className = 'auth-alert-box alert-danger';
    alertBox.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${escapeHTML(msg)}`;
    alertBox.style.display = 'block';
  }
}

function showAuthSuccess(msg) {
  const alertBox = document.getElementById('authAlertBox');
  if (alertBox) {
    alertBox.className = 'auth-alert-box alert-success';
    alertBox.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${escapeHTML(msg)}`;
    alertBox.style.display = 'block';
  }
}

function clearAuthAlerts() {
  const alertBox = document.getElementById('authAlertBox');
  if (alertBox) {
    alertBox.style.display = 'none';
    alertBox.innerHTML = '';
  }
}

function setAuthBtnLoading(btnId, isLoading, defaultText = 'Submit') {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = isLoading;
  if (isLoading) {
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Please wait...`;
  } else {
    btn.innerHTML = defaultText;
  }
}

function escapeHTML(str) {
  if (!str) return '';
  return String(str).replace(/[&<>'"]/g, tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
}

// Window Exports
window.calculateBMI = calculateBMI;
window.getBMICategory = getBMICategory;
/**
 * Toggles Leaderboard Privacy setting directly from Athlete Profile view
 */
async function toggleLeaderboardPrivacy(checked) {
  if (!authToken || !currentUser) return;
  try {
    const response = await fetch(`${AUTH_API_BASE}/profile`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
      },
      body: JSON.stringify({ leaderboard_visible: checked })
    });
    const updatedUser = await response.json();
    if (!response.ok) {
      throw new Error(updatedUser.detail || 'Failed to update leaderboard privacy.');
    }
    currentUser = updatedUser;
    renderProfilePage();
    if (typeof loadLeaderboardView === 'function') {
      loadLeaderboardView();
    }
  } catch (err) {
    alert(`Error updating privacy: ${err.message}`);
    const profLbCheckbox = document.getElementById('profLeaderboardCheckbox');
    if (profLbCheckbox) profLbCheckbox.checked = !checked;
  }
}

window.renderProfilePage = renderProfilePage;
window.toggleLeaderboardPrivacy = toggleLeaderboardPrivacy;

