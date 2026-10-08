/**
 * FitQuest Nutrition™ — Client-Side Application Controller
 * Handles Today's Nutrition Summary, 7-Day Meal Plan Rendering,
 * Single-Meal Regeneration, Meal Logging, Preferences, and AI Food Analysis.
 */

let activeNutritionDay = 1;
let currentNutritionPlan = null;
let currentNutritionProfile = null;
let currentTodaySummary = null;
let pendingFoodAnalysisResult = null;
let selectedFoodPhotoBase64 = null;

function getNutritionApiBase() {
  return window.getFitQuestApiBase ? window.getFitQuestApiBase() : (window.API_BASE || 'https://fitquest-backend-1brv.onrender.com/api/v1');
}

document.addEventListener('DOMContentLoaded', () => {
  // Check if nutrition view is active on initial load
  const activePanel = document.querySelector('.view-panel.active');
  if (activePanel && activePanel.id === 'nutritionView') {
    loadNutritionView();
  }
});

/**
 * Primary loader invoked when switching to Nutrition tab
 */
async function loadNutritionView() {
  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
  if (!token) {
    console.warn('[FitQuest Nutrition]: No auth token found.');
    return;
  }

  const apiBase = getNutritionApiBase();

  try {
    // 1. Fetch Today's Nutrition Summary
    const summaryRes = await fetch(`${apiBase}/nutrition/today`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (summaryRes.ok) {
      currentTodaySummary = await summaryRes.json();
      renderTodayNutritionSummary(currentTodaySummary);
      updateHomeNutritionWidget(currentTodaySummary);
    }

    // 2. Fetch Active 7-Day Plan
    const planRes = await fetch(`${apiBase}/nutrition/plan`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (planRes.ok) {
      currentNutritionPlan = await planRes.json();
      render7DayMealPlan(currentNutritionPlan);
    }

    // 3. Fetch Nutrition Profile
    const profRes = await fetch(`${apiBase}/nutrition/profile`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (profRes.ok) {
      currentNutritionProfile = await profRes.json();
      syncProfileFieldsWithUI(currentNutritionProfile);
    }
  } catch (err) {
    console.error('[FitQuest Nutrition] Failed to load nutrition view data:', err);
  }
}

/**
 * Renders Section A: Today's Nutrition Metrics & Progress Bars
 */
function renderTodayNutritionSummary(summary) {
  if (!summary) return;

  // Calorie Metrics
  const calValEl = document.getElementById('nutritionCalorieVal');
  const calSubEl = document.getElementById('nutritionCalorieSub');
  const calBarEl = document.getElementById('nutritionCalorieBar');
  if (calValEl) calValEl.innerHTML = `${summary.daily_calorie_target.toLocaleString()} <small>kcal</small>`;
  if (calSubEl) calSubEl.textContent = `${summary.calories_logged.toLocaleString()} / ${summary.daily_calorie_target.toLocaleString()} kcal logged`;
  if (calBarEl) calBarEl.style.width = `${Math.min(100, summary.calorie_progress_pct)}%`;

  // Protein Metrics
  const pValEl = document.getElementById('nutritionProteinVal');
  const pSubEl = document.getElementById('nutritionProteinSub');
  const pBarEl = document.getElementById('nutritionProteinBar');
  if (pValEl) pValEl.innerHTML = `${Math.round(summary.daily_protein_target)} <small>g</small>`;
  if (pSubEl) pSubEl.textContent = `${summary.protein_logged} / ${Math.round(summary.daily_protein_target)}g logged`;
  if (pBarEl) pBarEl.style.width = `${Math.min(100, summary.protein_progress_pct)}%`;

  // Meals Logged & Dots
  const mealsValEl = document.getElementById('nutritionMealsCountVal');
  const mealsSubEl = document.getElementById('nutritionMealsRemainingSub');
  if (mealsValEl) mealsValEl.textContent = `${summary.meals_logged_count} / ${summary.meals_total_target}`;
  if (mealsSubEl) {
    const rem = Math.max(0, summary.meals_total_target - summary.meals_logged_count);
    mealsSubEl.textContent = `${rem} meal${rem === 1 ? '' : 's'} remaining`;
  }

  // Meal Dots Visualizer
  const dotsContainer = document.getElementById('nutritionMealDotsContainer');
  if (dotsContainer) {
    const types = summary.meal_types_logged || [];
    const mealMap = [
      { key: 'breakfast', label: 'B', title: 'Breakfast' },
      { key: 'lunch', label: 'L', title: 'Lunch' },
      { key: 'snack', label: 'S', title: 'Snack' },
      { key: 'dinner', label: 'D', title: 'Dinner' }
    ];
    dotsContainer.innerHTML = mealMap.map(m => {
      const isDone = types.includes(m.key);
      return `<span class="nutrition-meal-dot ${isDone ? 'completed' : ''}" title="${m.title}: ${isDone ? 'Logged' : 'Pending'}">${isDone ? '✓' : m.label}</span>`;
    }).join('');
  }

  // Goal Badge
  const goalText = document.getElementById('nutritionGoalText');
  if (goalText) goalText.textContent = summary.fitness_goal || 'General Fitness';

  // Progressive Disclosure Drawer Values
  const bmrEl = document.getElementById('nutritionBmrVal');
  const tdeeEl = document.getElementById('nutritionTdeeVal');
  const carbsEl = document.getElementById('nutritionCarbsTargetVal');
  const fatEl = document.getElementById('nutritionFatTargetVal');
  if (bmrEl) bmrEl.textContent = `${summary.bmr_estimate} kcal`;
  if (tdeeEl) tdeeEl.textContent = `${summary.tdee_estimate} kcal`;
  if (carbsEl) carbsEl.textContent = `${Math.round(summary.daily_carbs_target)} g`;
  if (fatEl) fatEl.textContent = `${Math.round(summary.daily_fat_target)} g`;

  // Render Logged Meals List
  renderLoggedMealsList(summary.logged_meals || []);
}

/**
 * Updates the compact Today's Nutrition widget on Home Dashboard (#homeView)
 */
function updateHomeNutritionWidget(summary) {
  if (!summary) return;

  const calEl = document.getElementById('homeNutrCalVal');
  const pEl = document.getElementById('homeNutrProteinVal');
  const mealsEl = document.getElementById('homeNutrMealsVal');
  const barEl = document.getElementById('homeNutrProgressBar');

  if (calEl) calEl.textContent = `${summary.calories_logged.toLocaleString()} / ${summary.daily_calorie_target.toLocaleString()} kcal`;
  if (pEl) pEl.textContent = `${summary.protein_logged} / ${Math.round(summary.daily_protein_target)} g`;
  if (mealsEl) mealsEl.textContent = `${summary.meals_logged_count} / ${summary.meals_total_target} Logged`;
  if (barEl) barEl.style.width = `${Math.min(100, summary.calorie_progress_pct)}%`;
}

/**
 * Renders Section B: 7-Day Meal Plan with active day filter
 */
function render7DayMealPlan(plan) {
  if (!plan || !plan.days || plan.days.length === 0) {
    const container = document.getElementById('nutritionMealsContainer');
    if (container) {
      container.innerHTML = `
        <div class="nutrition-empty-plan">
          <i class="fa-solid fa-utensils"></i>
          <h3>No Meal Plan Active</h3>
          <p>Generate a personalized 7-day nutrition plan tailored to your fitness goals.</p>
          <button class="btn btn-primary" onclick="generateOrRefreshMealPlan(true)">Generate 7-Day Plan</button>
        </div>
      `;
    }
    return;
  }

  // Update source badge
  const sourceBadge = document.getElementById('nutritionPlanSourceBadge');
  if (sourceBadge) {
    const isGemini = plan.generator_source === 'Gemini AI';
    sourceBadge.innerHTML = isGemini 
      ? `<i class="fa-solid fa-sparkles" style="color: var(--accent-cyan);"></i> AI Personalized`
      : `<i class="fa-solid fa-shield-check" style="color: var(--accent-lime);"></i> Recipe Engine`;
  }

  // Find active day
  const dayData = plan.days.find(d => d.day === activeNutritionDay) || plan.days[0];
  const container = document.getElementById('nutritionMealsContainer');
  if (!container) return;

  const mealIcons = {
    breakfast: 'fa-mug-saucer',
    lunch: 'fa-burger',
    snack: 'fa-apple-whole',
    dinner: 'fa-bowl-rice'
  };

  const mealColors = {
    breakfast: '#ff9800',
    lunch: '#00f2fe',
    snack: '#10b981',
    dinner: '#9d4edd'
  };

  container.innerHTML = dayData.meals.map((meal, idx) => {
    const icon = mealIcons[meal.type.toLowerCase()] || 'fa-utensils';
    const color = mealColors[meal.type.toLowerCase()] || '#10b981';
    const cardId = `mealCard_${dayData.day}_${meal.type}`;
    const detailsId = `mealDetails_${dayData.day}_${meal.type}`;

    const tagsHtml = (meal.tags || []).map(t => `<span class="meal-tag">${escapeHTML(t)}</span>`).join('');
    const ingredientsHtml = (meal.ingredients || []).map(ing => `<li><i class="fa-solid fa-check"></i> ${escapeHTML(ing)}</li>`).join('');
    const instructionsHtml = (meal.instructions || []).map((step, sIdx) => `<li><span class="step-num">${sIdx + 1}</span> ${escapeHTML(step)}</li>`).join('');

    return `
      <div class="nutrition-meal-card" id="${cardId}">
        <div class="meal-card-main">
          <div class="meal-card-header">
            <div class="meal-type-badge" style="color: ${color}; background: ${color}15; border-color: ${color}35;">
              <i class="fa-solid ${icon}"></i> ${meal.type.toUpperCase()}
            </div>
            <div class="meal-header-actions">
              <button type="button" class="meal-regen-btn" title="Regenerate only this meal" onclick="regenerateIndividualMeal(${dayData.day}, '${meal.type}', event)">
                <i class="fa-solid fa-arrows-rotate"></i> Regenerate
              </button>
            </div>
          </div>

          <h3 class="meal-card-title">${escapeHTML(meal.name)}</h3>

          <!-- Macro Pills -->
          <div class="meal-macros-row">
            <div class="meal-macro-chip cal">
              <i class="fa-solid fa-fire"></i> <strong>${meal.calories}</strong> kcal
            </div>
            <div class="meal-macro-chip protein">
              <i class="fa-solid fa-drumstick-bite"></i> <strong>${meal.protein_g}g</strong> protein
            </div>
            <div class="meal-macro-chip carbs">
              <i class="fa-solid fa-wheat-awn"></i> ${meal.carbs_g}g carbs
            </div>
            <div class="meal-macro-chip fat">
              <i class="fa-solid fa-droplet"></i> ${meal.fat_g}g fat
            </div>
          </div>

          ${tagsHtml ? `<div class="meal-tags-row">${tagsHtml}</div>` : ''}

          <!-- Expand Toggle -->
          <button type="button" class="meal-expand-btn" onclick="toggleMealCardDetails('${detailsId}', this)" aria-expanded="false">
            <span>View Recipe & Ingredients</span>
            <i class="fa-solid fa-chevron-down"></i>
          </button>
        </div>

        <!-- Expandable Details Container -->
        <div class="meal-card-expanded" id="${detailsId}" style="display: none;">
          ${ingredientsHtml ? `
            <div class="meal-ingredients-box">
              <h4><i class="fa-solid fa-list-ul"></i> Ingredients</h4>
              <ul class="meal-ingredients-list">${ingredientsHtml}</ul>
            </div>
          ` : ''}

          ${instructionsHtml ? `
            <div class="meal-instructions-box">
              <h4><i class="fa-solid fa-kitchen-set"></i> Preparation Steps</h4>
              <ol class="meal-instructions-list">${instructionsHtml}</ol>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Switches the active day in 7-Day plan
 */
function selectNutritionDay(dayNum) {
  activeNutritionDay = dayNum;

  // Update tab buttons
  const buttons = document.querySelectorAll('.nutrition-day-btn');
  buttons.forEach(btn => {
    if (parseInt(btn.getAttribute('data-day'), 10) === dayNum) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  if (currentNutritionPlan) {
    render7DayMealPlan(currentNutritionPlan);
  }
}

/**
 * Toggles expandable meal card ingredients & instructions
 */
function toggleMealCardDetails(detailsId, btn) {
  const detailsEl = document.getElementById(detailsId);
  if (!detailsEl) return;

  const isHidden = detailsEl.style.display === 'none';
  detailsEl.style.display = isHidden ? 'block' : 'none';

  if (btn) {
    btn.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
    const span = btn.querySelector('span');
    const icon = btn.querySelector('i');
    if (span) span.textContent = isHidden ? 'Hide Recipe Details' : 'View Recipe & Ingredients';
    if (icon) {
      icon.className = isHidden ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down';
    }
  }
}

/**
 * Toggles progressive disclosure drawer for BMR/TDEE calculation
 */
function toggleNutritionDetails() {
  const content = document.getElementById('nutritionDetailsContent');
  const toggleBtn = document.getElementById('nutritionDetailsToggle');
  const toggleText = document.getElementById('nutritionDetailsToggleText');
  const toggleIcon = document.getElementById('nutritionDetailsToggleIcon');
  if (!content) return;

  const isHidden = content.style.display === 'none';
  content.style.display = isHidden ? 'block' : 'none';

  if (toggleBtn) toggleBtn.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
  if (toggleText) toggleText.textContent = isHidden ? 'Hide Target Calculation Details' : 'View Target Calculation Details';
  if (toggleIcon) toggleIcon.className = isHidden ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down';
}

/**
 * Regenerates an individual meal on demand while keeping the rest of the plan
 */
async function regenerateIndividualMeal(dayNum, mealType, event) {
  if (event) event.stopPropagation();

  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
  if (!token) return;

  const btn = event ? event.currentTarget : null;
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Swapping...`;
  }

  const apiBase = getNutritionApiBase();

  try {
    const res = await fetch(`${apiBase}/nutrition/meal/regenerate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        day: dayNum,
        meal_type: mealType
      })
    });

    if (!res.ok) {
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    currentNutritionPlan = await res.json();
    render7DayMealPlan(currentNutritionPlan);
  } catch (err) {
    console.error('[FitQuest Nutrition] Meal regeneration failed:', err);
    alert('Failed to regenerate meal. Please check your connection and try again.');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> Regenerate`;
    }
  }
}

/**
 * Generates or completely refreshes the 7-day meal plan
 */
async function generateOrRefreshMealPlan(force = true) {
  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
  if (!token) return;

  const container = document.getElementById('nutritionMealsContainer');
  if (container) {
    container.innerHTML = `
      <div class="loading-spinner" style="padding: 40px; text-align: center; color: var(--accent-cyan);">
        <i class="fa-solid fa-circle-notch fa-spin fa-2x"></i>
        <p style="margin-top: 14px; font-weight: 500;">Generating your personalized 7-Day Nutrition Plan...</p>
      </div>
    `;
  }

  const apiBase = getNutritionApiBase();

  try {
    const res = await fetch(`${apiBase}/nutrition/plan/generate?force=${force}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!res.ok) {
      throw new Error(`HTTP error ${res.status}`);
    }

    currentNutritionPlan = await res.json();
    render7DayMealPlan(currentNutritionPlan);
  } catch (err) {
    console.error('[FitQuest Nutrition] Plan generation failed:', err);
    if (container) {
      container.innerHTML = `
        <div class="nutrition-empty-plan">
          <i class="fa-solid fa-triangle-exclamation" style="color: #ff5252;"></i>
          <h3>Generation Encountered an Error</h3>
          <p>We could not generate the meal plan at this moment. Please try again.</p>
          <button class="btn btn-primary" onclick="generateOrRefreshMealPlan(true)">Retry</button>
        </div>
      `;
    }
  }
}

/**
 * Handles submission of "Log What You Ate" form
 */
async function handleMealLogSubmit(e) {
  e.preventDefault();

  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
  if (!token) return;

  const mealType = document.getElementById('logMealType').value;
  const foodName = document.getElementById('logFoodName').value.trim();
  if (!foodName) return;

  const calInput = document.getElementById('logCalories').value;
  const pInput = document.getElementById('logProtein').value;
  const cInput = document.getElementById('logCarbs').value;
  const fInput = document.getElementById('logFat').value;

  const payload = {
    meal_type: mealType,
    food_name: foodName,
    calories: calInput ? parseInt(calInput, 10) : null,
    protein_g: pInput ? parseFloat(pInput) : null,
    carbs_g: cInput ? parseFloat(cInput) : null,
    fat_g: fInput ? parseFloat(fInput) : null
  };

  const submitBtn = document.getElementById('logMealSubmitBtn');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Logging...`;
  }

  const apiBase = getNutritionApiBase();

  try {
    const res = await fetch(`${apiBase}/nutrition/meal/log`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      throw new Error(`HTTP error ${res.status}`);
    }

    // Reset form inputs
    document.getElementById('logFoodName').value = '';
    document.getElementById('logCalories').value = '';
    document.getElementById('logProtein').value = '';
    document.getElementById('logCarbs').value = '';
    document.getElementById('logFat').value = '';

    // Reload today's summary to update progress bars
    const summaryRes = await fetch(`${apiBase}/nutrition/today`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (summaryRes.ok) {
      currentTodaySummary = await summaryRes.json();
      renderTodayNutritionSummary(currentTodaySummary);
      updateHomeNutritionWidget(currentTodaySummary);
    }
  } catch (err) {
    console.error('[FitQuest Nutrition] Failed to log meal:', err);
    alert('Failed to log meal. Please try again.');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<i class="fa-solid fa-plus"></i> Log Meal`;
    }
  }
}

/**
 * Populates food name from quick suggestion chips
 */
function populateLogFood(foodName) {
  const input = document.getElementById('logFoodName');
  if (input) {
    input.value = foodName;
    input.focus();
  }
}

/**
 * Renders list of meals logged today with delete action
 */
function renderLoggedMealsList(logs) {
  const container = document.getElementById('nutritionLoggedMealsList');
  if (!container) return;

  if (!logs || logs.length === 0) {
    container.innerHTML = `<div class="nutrition-empty-logs">No meals logged yet today. Enter what you ate above to begin!</div>`;
    return;
  }

  container.innerHTML = logs.map(item => {
    const timeStr = item.logged_at ? new Date(item.logged_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
    return `
      <div class="nutrition-logged-item">
        <div class="logged-item-info">
          <div class="logged-item-type-badge">${escapeHTML(item.meal_type)}</div>
          <div class="logged-item-title-col">
            <span class="logged-item-name">${escapeHTML(item.food_name)}</span>
            <span class="logged-item-time">${timeStr}</span>
          </div>
        </div>
        <div class="logged-item-macros">
          <span class="logged-macro-pill cal"><strong>${item.calories}</strong> kcal</span>
          <span class="logged-macro-pill protein"><strong>${item.protein_g}g</strong> P</span>
          <span class="logged-macro-pill carbs">${item.carbs_g}g C</span>
          <span class="logged-macro-pill fat">${item.fat_g}g F</span>
          <button type="button" class="logged-item-delete-btn" title="Remove logged meal" onclick="deleteMealLog(${item.id})">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Deletes a logged meal
 */
async function deleteMealLog(logId) {
  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
  if (!token) return;

  const apiBase = getNutritionApiBase();

  try {
    const res = await fetch(`${apiBase}/nutrition/meal/log/${logId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (res.ok) {
      // Reload summary
      const summaryRes = await fetch(`${apiBase}/nutrition/today`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (summaryRes.ok) {
        currentTodaySummary = await summaryRes.json();
        renderTodayNutritionSummary(currentTodaySummary);
        updateHomeNutritionWidget(currentTodaySummary);
      }
    }
  } catch (err) {
    console.error('[FitQuest Nutrition] Failed to delete logged meal:', err);
  }
}

/**
 * Smooth scroll to meal logger section
 */
function scrollToMealLogger() {
  const section = document.getElementById('nutritionLoggerSection');
  if (section) {
    section.scrollIntoView({ behavior: 'smooth' });
    const input = document.getElementById('logFoodName');
    if (input) setTimeout(() => input.focus(), 400);
  }
}

// -------------------------------------------------------------
// Preferences Modal Logic
// -------------------------------------------------------------
function openNutritionPreferencesModal() {
  const modal = document.getElementById('nutritionPreferencesModal');
  if (!modal) return;

  if (currentNutritionProfile) {
    syncProfileFieldsWithUI(currentNutritionProfile);
  }
  modal.style.display = 'flex';
}

function closeNutritionPreferencesModal() {
  const modal = document.getElementById('nutritionPreferencesModal');
  if (modal) modal.style.display = 'none';
}

function syncProfileFieldsWithUI(profile) {
  if (!profile) return;

  // Diet Type radio
  const dietRadios = document.querySelectorAll('input[name="dietType"]');
  dietRadios.forEach(radio => {
    radio.checked = (radio.value.toLowerCase() === (profile.diet_type || 'Non-Vegetarian').toLowerCase());
  });

  // Allergies
  const allergyBtns = document.querySelectorAll('#nutritionAllergiesSelector .nutrition-select-tag');
  const userAllergies = (profile.allergies || []).map(a => a.toLowerCase());
  allergyBtns.forEach(btn => {
    const val = btn.getAttribute('data-val').toLowerCase();
    if (userAllergies.includes(val)) {
      btn.classList.add('selected');
    } else {
      btn.classList.remove('selected');
    }
  });

  // Cuisines
  const cuisineBtns = document.querySelectorAll('#nutritionCuisinesSelector .nutrition-select-tag');
  const userCuisines = (profile.cuisines || []).map(c => c.toLowerCase());
  cuisineBtns.forEach(btn => {
    const val = btn.getAttribute('data-val').toLowerCase();
    if (userCuisines.includes(val)) {
      btn.classList.add('selected');
    } else {
      btn.classList.remove('selected');
    }
  });

  // Budget
  const budgetSelect = document.getElementById('nutritionBudgetSelect');
  if (budgetSelect && profile.budget) budgetSelect.value = profile.budget;

  // Meals per day
  const mealsSelect = document.getElementById('nutritionMealsPerDaySelect');
  if (mealsSelect && profile.meals_per_day) mealsSelect.value = String(profile.meals_per_day);
}

function toggleSelectionTag(btn) {
  if (btn) btn.classList.toggle('selected');
}

async function handleNutritionPreferencesSubmit(e) {
  e.preventDefault();

  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
  if (!token) return;

  const dietType = document.querySelector('input[name="dietType"]:checked')?.value || 'Non-Vegetarian';

  // Selected allergies
  const allergies = [];
  document.querySelectorAll('#nutritionAllergiesSelector .nutrition-select-tag.selected').forEach(btn => {
    allergies.push(btn.getAttribute('data-val'));
  });
  const customAllergy = document.getElementById('customAllergyInput')?.value.trim();
  if (customAllergy) {
    customAllergy.split(',').forEach(a => {
      if (a.trim()) allergies.push(a.trim());
    });
  }

  // Selected cuisines
  const cuisines = [];
  document.querySelectorAll('#nutritionCuisinesSelector .nutrition-select-tag.selected').forEach(btn => {
    cuisines.push(btn.getAttribute('data-val'));
  });

  const budget = document.getElementById('nutritionBudgetSelect')?.value || 'Moderate';
  const mealsPerDay = parseInt(document.getElementById('nutritionMealsPerDaySelect')?.value || '4', 10);

  const payload = {
    diet_type: dietType,
    allergies: allergies,
    cuisines: cuisines,
    budget: budget,
    meals_per_day: mealsPerDay
  };

  const btn = document.getElementById('saveNutritionPrefBtn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Saving...`;
  }

  const apiBase = getNutritionApiBase();

  try {
    const res = await fetch(`${apiBase}/nutrition/profile`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error(`HTTP error ${res.status}`);

    currentNutritionProfile = await res.json();
    closeNutritionPreferencesModal();

    // Regenerate plan with updated preferences
    await generateOrRefreshMealPlan(true);

    // Refresh today's summary
    const summaryRes = await fetch(`${apiBase}/nutrition/today`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (summaryRes.ok) {
      currentTodaySummary = await summaryRes.json();
      renderTodayNutritionSummary(currentTodaySummary);
      updateHomeNutritionWidget(currentTodaySummary);
    }
  } catch (err) {
    console.error('[FitQuest Nutrition] Failed to save preferences:', err);
    alert('Failed to save preferences. Please try again.');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-check"></i> Save & Recalculate`;
    }
  }
}

// -------------------------------------------------------------
// AI Food & Meal Analyzer Modal Logic
// -------------------------------------------------------------
function openFoodAnalyzerModal() {
  const modal = document.getElementById('nutritionFoodAnalyzerModal');
  if (modal) {
    modal.style.display = 'flex';
    // Clear preview
    selectedFoodPhotoBase64 = null;
    pendingFoodAnalysisResult = null;
    const preview = document.getElementById('foodPhotoPreviewImg');
    if (preview) preview.style.display = 'none';
    const dropText = document.getElementById('nutritionDropzoneText');
    if (dropText) dropText.style.display = 'block';
    const resultsBox = document.getElementById('foodAnalysisResultsBox');
    if (resultsBox) resultsBox.style.display = 'none';
  }
}

function closeFoodAnalyzerModal() {
  const modal = document.getElementById('nutritionFoodAnalyzerModal');
  if (modal) modal.style.display = 'none';
}

function handleFoodPhotoSelected(e) {
  const file = e.target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (event) => {
    selectedFoodPhotoBase64 = event.target.result;
    const preview = document.getElementById('foodPhotoPreviewImg');
    const dropText = document.getElementById('nutritionDropzoneText');
    if (preview) {
      preview.src = selectedFoodPhotoBase64;
      preview.style.display = 'block';
    }
    if (dropText) dropText.style.display = 'none';
  };
  reader.readAsDataURL(file);
}

function analyzeSampleFood(sampleText) {
  const input = document.getElementById('foodDescriptionInput');
  if (input) input.value = sampleText;
  runFoodAnalysis();
}

async function runFoodAnalysis() {
  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
  if (!token) return;

  const textDesc = document.getElementById('foodDescriptionInput')?.value.trim();
  if (!selectedFoodPhotoBase64 && !textDesc) {
    alert('Please select a food photo or enter a meal description to analyze.');
    return;
  }

  const btn = document.getElementById('analyzeFoodBtn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Analyzing with AI...`;
  }

  const apiBase = getNutritionApiBase();

  try {
    const res = await fetch(`${apiBase}/nutrition/analyze-food`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        image_base64: selectedFoodPhotoBase64,
        text_description: textDesc
      })
    });

    if (!res.ok) throw new Error(`HTTP error ${res.status}`);

    const result = await res.json();
    pendingFoodAnalysisResult = result;
    renderFoodAnalysisResults(result);
  } catch (err) {
    console.error('[FitQuest Nutrition] Food analysis error:', err);
    alert('Food analysis encountered an issue. Please verify your connection.');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Analyze Food`;
    }
  }
}

function renderFoodAnalysisResults(result) {
  const box = document.getElementById('foodAnalysisResultsBox');
  if (!box) return;

  box.style.display = 'block';
  document.getElementById('analyzedFoodTitle').textContent = result.food_name || 'Identified Food Item';
  document.getElementById('analyzedProviderBadge').textContent = result.provider || 'Gemini Vision AI';

  document.getElementById('analyzedCalVal').textContent = `${result.estimated_calories}`;
  document.getElementById('analyzedProteinVal').textContent = `${result.protein_g}g`;
  document.getElementById('analyzedCarbsVal').textContent = `${result.carbs_g}g`;
  document.getElementById('analyzedFatVal').textContent = `${result.fat_g}g`;

  // Allergen warnings
  const allergenAlert = document.getElementById('analyzedAllergensAlert');
  if (allergenAlert) {
    if (result.allergen_warnings && result.allergen_warnings.length > 0) {
      allergenAlert.style.display = 'block';
      allergenAlert.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> <strong>Allergen Notice:</strong> ${escapeHTML(result.allergen_warnings.join(', '))}`;
    } else {
      allergenAlert.style.display = 'none';
    }
  }

  // Recommendations
  const recBox = document.getElementById('analyzedRecommendation');
  if (recBox) {
    recBox.innerHTML = `<i class="fa-solid fa-lightbulb"></i> <strong>Coach Tip:</strong> ${escapeHTML(result.recommendations || 'Balanced fitness meal.')}`;
  }
}

async function logAnalyzedMealToToday() {
  if (!pendingFoodAnalysisResult) return;

  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
  if (!token) return;

  const payload = {
    meal_type: 'lunch',
    food_name: pendingFoodAnalysisResult.food_name,
    calories: pendingFoodAnalysisResult.estimated_calories,
    protein_g: pendingFoodAnalysisResult.protein_g,
    carbs_g: pendingFoodAnalysisResult.carbs_g,
    fat_g: pendingFoodAnalysisResult.fat_g
  };

  const btn = document.getElementById('logAnalyzedMealBtn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Logging to Tracker...`;
  }

  const apiBase = getNutritionApiBase();

  try {
    const res = await fetch(`${apiBase}/nutrition/meal/log`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      closeFoodAnalyzerModal();
      // Reload today's summary
      const summaryRes = await fetch(`${apiBase}/nutrition/today`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (summaryRes.ok) {
        currentTodaySummary = await summaryRes.json();
        renderTodayNutritionSummary(currentTodaySummary);
        updateHomeNutritionWidget(currentTodaySummary);
      }
    }
  } catch (err) {
    console.error('[FitQuest Nutrition] Failed to log analyzed meal:', err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-plus"></i> Log This Meal to Today's Tracker`;
    }
  }
}

// Utility HTML escape helper
function escapeHTML(str) {
  if (!str) return '';
  return String(str).replace(/[&<>'"]/g, tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
}
