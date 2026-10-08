/**
 * FitQuest — Movement Evolution & Longitudinal Intelligence Engine
 * Handles fetching, dual-radar rendering, timeline trend plotting,
 * and AI Movement Insight presentation.
 */

let activeEvolutionExerciseId = null;
let currentEvolutionData = null;

/**
 * Loads Movement Evolution data for the authenticated user and selected exercise.
 */
async function loadMovementEvolution(exerciseId = null) {
  const container = document.getElementById('evolutionView');
  if (!container) return;

  const token = typeof getAuthToken === 'function' ? getAuthToken() : localStorage.getItem('fitquest_token');
  if (!token) {
    console.warn('[FitQuest Evolution]: Unauthenticated evolution request.');
    return;
  }

  // Ensure exercise selector is populated
  await populateEvolutionExerciseSelector();

  try {
    let url = `${API_BASE}/workouts/movement-intelligence/evolution`;
    if (exerciseId) {
      url += `?exercise_id=${exerciseId}`;
    }

    const res = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json'
      }
    });

    if (!res.ok) {
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    const data = await res.json();
    currentEvolutionData = data;
    activeEvolutionExerciseId = data.exercise_id;

    // Sync dropdown selector
    const selector = document.getElementById('evolutionExerciseSelect');
    if (selector && data.exercise_id) {
      selector.value = data.exercise_id;
    }

    renderMovementEvolutionDashboard(data);

  } catch (err) {
    console.error('[FitQuest Evolution Error]: Failed to load evolution data:', err);
    renderEvolutionEmptyState("Failed to load movement evolution telemetry.");
  }
}

/**
 * Populates the Exercise Selector dropdown with all available exercises
 */
async function populateEvolutionExerciseSelector() {
  const selector = document.getElementById('evolutionExerciseSelect');
  if (!selector || selector.children.length > 1) return;

  try {
    const res = await fetch(`${API_BASE}/exercises`);
    if (res.ok) {
      const exercises = await res.json();
      selector.innerHTML = exercises.map(ex => `
        <option value="${ex.id}">${escapeHTML(ex.name)}</option>
      `).join('');
    }
  } catch (e) {
    console.warn('[FitQuest Evolution]: Could not fetch exercises list:', e);
  }
}

/**
 * Renders all dashboard elements in the Movement Evolution view
 */
function renderMovementEvolutionDashboard(data) {
  if (!data) return;

  // 1. Header & Quality Banner
  const exNameEl = document.getElementById('evoExerciseTitle');
  if (exNameEl) exNameEl.innerText = data.exercise_name || 'Movement Evolution';

  const sessionsCountEl = document.getElementById('evoSessionsCount');
  if (sessionsCountEl) {
    sessionsCountEl.innerText = `${data.sessions_analyzed || 0} ${data.sessions_analyzed === 1 ? 'Session' : 'Sessions'} Analyzed`;
  }

  const qualityScoreEl = document.getElementById('evoCurrentQualityScore');
  if (qualityScoreEl) {
    qualityScoreEl.innerText = data.overall ? `${data.overall.latest.toFixed(1)}` : '0.0';
  }

  const qualityChangeEl = document.getElementById('evoQualityChangePill');
  if (qualityChangeEl && data.overall) {
    const change = data.overall.change || 0.0;
    const changePct = data.overall.change_pct || 0.0;
    const isBaseline = data.overall.trend === 'baseline';

    if (isBaseline) {
      qualityChangeEl.className = 'evo-change-pill pill-neutral';
      qualityChangeEl.innerHTML = `<span>Baseline Established</span>`;
    } else if (change >= 0) {
      qualityChangeEl.className = 'evo-change-pill pill-improving';
      qualityChangeEl.innerHTML = `<i class="fa-solid fa-arrow-trend-up"></i> +${change.toFixed(1)} pts (${changePct >= 0 ? '+' : ''}${changePct.toFixed(1)}%)`;
    } else {
      qualityChangeEl.className = 'evo-change-pill pill-declining';
      qualityChangeEl.innerHTML = `<i class="fa-solid fa-arrow-trend-down"></i> ${change.toFixed(1)} pts (${changePct.toFixed(1)}%)`;
    }
  }

  // 2. Render Dual-Radar Fingerprint Canvas (Baseline vs Current)
  const radarCanvas = document.getElementById('evolutionRadarCanvas');
  if (radarCanvas) {
    drawDualFingerprintRadar(radarCanvas, data.baseline_signature, data.current_signature);
  }

  // 3. Render Longitudinal Quality Spline Chart
  const historyCanvas = document.getElementById('evolutionHistoryCanvas');
  if (historyCanvas) {
    drawEvolutionHistoryCanvas(historyCanvas, data.timeline || []);
  }

  // 4. Render Metric Trend Cards
  renderEvolutionMetricCards(data.metrics);

  // 5. Render AI Movement Insight & Recommendations
  const insightEl = document.getElementById('evoAIInsightText');
  if (insightEl) {
    insightEl.innerHTML = `<i class="fa-solid fa-brain" style="color: var(--accent-cyan); margin-right: 6px;"></i> ${escapeHTML(data.ai_insight || '')}`;
  }

  const recsContainer = document.getElementById('evoRecommendationsList');
  if (recsContainer) {
    const recs = data.recommendations || [];
    recsContainer.innerHTML = recs.map(rec => `
      <div class="evo-rec-item">
        <i class="fa-solid fa-circle-check" style="color: var(--accent-lime); margin-top: 3px;"></i>
        <span>${escapeHTML(rec)}</span>
      </div>
    `).join('');
  }
}

/**
 * Renders the 5 Metric Trend Cards (ROM, Stability, Tempo, Consistency, Symmetry)
 */
function renderEvolutionMetricCards(metrics) {
  const container = document.getElementById('evolutionMetricCardsGrid');
  if (!container || !metrics) return;

  const metricDefs = [
    { key: 'rom', label: 'Range of Motion', icon: 'fa-arrows-up-down', unit: '°/pts' },
    { key: 'stability', label: 'Movement Stability', icon: 'fa-crosshairs', unit: 'pts' },
    { key: 'tempo', label: 'Tempo Control', icon: 'fa-stopwatch', unit: 'pts' },
    { key: 'consistency', label: 'Rep Consistency', icon: 'fa-wave-square', unit: 'pts' },
    { key: 'symmetry', label: 'Bilateral Symmetry', icon: 'fa-scale-balanced', unit: 'pts' }
  ];

  container.innerHTML = metricDefs.map(def => {
    const m = metrics[def.key];
    if (!m) return '';

    const isAvail = m.available;
    const isNullSym = def.key === 'symmetry' && m.initial === null && m.latest === null;

    let trendClass = 'trend-stable';
    let trendIcon = '<i class="fa-solid fa-minus"></i>';
    let trendLabel = 'STABLE';

    if (m.trend === 'improving') {
      trendClass = 'trend-improving';
      trendIcon = '<i class="fa-solid fa-arrow-up"></i>';
      trendLabel = 'IMPROVING';
    } else if (m.trend === 'declining') {
      trendClass = 'trend-declining';
      trendIcon = '<i class="fa-solid fa-arrow-down"></i>';
      trendLabel = 'DECLINING';
    } else if (m.trend === 'baseline') {
      trendClass = 'trend-baseline';
      trendIcon = '<i class="fa-solid fa-circle-dot"></i>';
      trendLabel = 'BASELINE';
    }

    if (isNullSym) {
      return `
        <div class="evo-metric-card disabled-card">
          <div class="evo-card-header">
            <span class="evo-card-title"><i class="fa-solid ${def.icon}"></i> ${def.label}</span>
            <span class="evo-trend-badge trend-neutral">N/A</span>
          </div>
          <div class="evo-card-body">
            <div class="evo-metric-value" style="font-size: 1.1rem; color: var(--text-muted);">Single-Axis</div>
            <div class="evo-metric-sub">Unilateral / Axial Movement</div>
          </div>
        </div>
      `;
    }

    const curScore = isAvail && m.latest !== null ? m.latest.toFixed(1) : '--';
    const changeText = isAvail && m.trend !== 'baseline' 
      ? `${m.change >= 0 ? '+' : ''}${m.change.toFixed(1)} (${m.change_pct >= 0 ? '+' : ''}${m.change_pct.toFixed(1)}%)`
      : 'Initial Baseline';

    return `
      <div class="evo-metric-card ${trendClass}">
        <div class="evo-card-header">
          <span class="evo-card-title"><i class="fa-solid ${def.icon}"></i> ${def.label}</span>
          <span class="evo-trend-badge ${trendClass}">${trendIcon} ${trendLabel}</span>
        </div>
        <div class="evo-card-body">
          <div class="evo-metric-value">${curScore}</div>
          <div class="evo-metric-sub">${changeText}</div>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Draws the Superimposed Dual Movement Fingerprint Radar (Baseline vs Current)
 */
function drawDualFingerprintRadar(canvas, baseSig, curSig) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const w = 320;
  const h = 320;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = `${w}px`;
  canvas.style.height = `${h}px`;
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, w, h);

  const cx = w / 2;
  const cy = h / 2;
  const maxRadius = 100;

  // Determine axes
  const hasSymmetry = curSig && curSig.symmetry_score !== null;
  const axes = [
    { key: 'rom_score', label: 'ROM' },
    { key: 'stability_score', label: 'STABILITY' },
    { key: 'tempo_score', label: 'TEMPO' },
    { key: 'consistency_score', label: 'CONSIST' }
  ];
  if (hasSymmetry) {
    axes.push({ key: 'symmetry_score', label: 'SYMMETRY' });
  }

  const numAxes = axes.length;
  const angleStep = (Math.PI * 2) / numAxes;
  const startAngle = -Math.PI / 2;

  // Concentric Radar Rings
  const rings = [0.2, 0.4, 0.6, 0.8, 1.0];
  rings.forEach((ratio) => {
    const r = maxRadius * ratio;
    ctx.beginPath();
    for (let i = 0; i < numAxes; i++) {
      const angle = startAngle + i * angleStep;
      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = ratio === 1.0 ? '#cbd5e1' : '#e2e8f0';
    ctx.lineWidth = 1;
    ctx.stroke();
  });

  // Radial Spokes and Axis Labels
  axes.forEach((axis, i) => {
    const angle = startAngle + i * angleStep;
    const x = cx + maxRadius * Math.cos(angle);
    const y = cy + maxRadius * Math.sin(angle);

    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(x, y);
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1;
    ctx.stroke();

    const labelDist = maxRadius + 22;
    const lx = cx + labelDist * Math.cos(angle);
    const ly = cy + labelDist * Math.sin(angle);

    ctx.font = '700 9px "Outfit", "Inter", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#0f172a';
    ctx.fillText(axis.label, lx, ly);
  });

  // 1. Draw Baseline Polygon (Dashed Amber)
  if (baseSig) {
    ctx.save();
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    axes.forEach((axis, i) => {
      const val = Math.max(8, Math.min(100, baseSig[axis.key] || 0));
      const r = maxRadius * (val / 100);
      const angle = startAngle + i * angleStep;
      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.fillStyle = 'rgba(217, 119, 6, 0.08)';
    ctx.fill();
    ctx.strokeStyle = '#d97706';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();
  }

  // 2. Draw Current Polygon (Cyan / Lime)
  if (curSig) {
    const curPoints = axes.map((axis, i) => {
      const val = Math.max(8, Math.min(100, curSig[axis.key] || 0));
      const r = maxRadius * (val / 100);
      const angle = startAngle + i * angleStep;
      return {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle)
      };
    });

    ctx.beginPath();
    curPoints.forEach((pt, i) => {
      if (i === 0) ctx.moveTo(pt.x, pt.y);
      else ctx.lineTo(pt.x, pt.y);
    });
    ctx.closePath();

    const grad = ctx.createRadialGradient(cx, cy, 10, cx, cy, maxRadius);
    grad.addColorStop(0, 'rgba(2, 132, 199, 0.25)');
    grad.addColorStop(1, 'rgba(132, 204, 22, 0.1)');
    ctx.fillStyle = grad;
    ctx.fill();

    ctx.strokeStyle = '#0284c7';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Coordinate dots
    curPoints.forEach(pt => {
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 2.5, 0, Math.PI * 2);
      ctx.fillStyle = '#4d7c0f';
      ctx.fill();
    });
  }
}

/**
 * Draws the Smooth Longitudinal Spline / Quality Evolution Chart
 */
function drawEvolutionHistoryCanvas(canvas, timeline) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const parentW = canvas.parentElement ? canvas.parentElement.clientWidth : 480;
  const w = Math.max(300, parentW || 480);
  const h = 200;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = '100%';
  canvas.style.height = `${h}px`;
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, w, h);

  const padLeft = 40;
  const padRight = 30;
  const padTop = 25;
  const padBottom = 35;
  const chartW = w - padLeft - padRight;
  const chartH = h - padTop - padBottom;

  // Background Grid Lines
  const gridLevels = [0, 25, 50, 75, 100];
  ctx.font = '600 9px "Outfit", monospace';
  ctx.fillStyle = '#64748b';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';

  gridLevels.forEach(lvl => {
    const y = padTop + chartH - (lvl / 100) * chartH;
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(w - padRight, y);
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillText(`${lvl}`, padLeft - 8, y);
  });

  if (!timeline || timeline.length === 0) {
    ctx.fillStyle = '#64748b';
    ctx.textAlign = 'center';
    ctx.font = '11px "Outfit", sans-serif';
    ctx.fillText('No historical sessions recorded yet.', w / 2, h / 2);
    return;
  }

  // Calculate coordinates for timeline points
  const points = timeline.map((pt, i) => {
    const x = timeline.length === 1 
      ? padLeft + chartW / 2 
      : padLeft + (i / (timeline.length - 1)) * chartW;
    const score = Math.max(0, Math.min(100, pt.quality || 0));
    const y = padTop + chartH - (score / 100) * chartH;
    return { x, y, score, date: pt.date, idx: i + 1 };
  });

  // Draw Gradient Area Fill under trajectory
  if (points.length > 1) {
    ctx.beginPath();
    ctx.moveTo(points[0].x, padTop + chartH);
    points.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.lineTo(points[points.length - 1].x, padTop + chartH);
    ctx.closePath();

    const areaGrad = ctx.createLinearGradient(0, padTop, 0, padTop + chartH);
    areaGrad.addColorStop(0, 'rgba(2, 132, 199, 0.2)');
    areaGrad.addColorStop(1, 'rgba(2, 132, 199, 0.0)');
    ctx.fillStyle = areaGrad;
    ctx.fill();
  }

  // Draw Line Path
  ctx.beginPath();
  points.forEach((p, i) => {
    if (i === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  });
  ctx.strokeStyle = '#0284c7';
  ctx.lineWidth = 2.5;
  ctx.stroke();

  // Draw Points & Labels
  points.forEach((p, i) => {
    // Coordinate circle
    ctx.beginPath();
    ctx.arc(p.x, p.y, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();

    ctx.beginPath();
    ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
    ctx.fillStyle = i === points.length - 1 ? '#4d7c0f' : '#0284c7';
    ctx.fill();

    // Score Callout Badge on latest
    if (i === points.length - 1 || points.length <= 4) {
      ctx.font = '700 10px "Outfit", monospace';
      ctx.fillStyle = '#0284c7';
      ctx.textAlign = 'center';
      ctx.fillText(`${p.score.toFixed(0)}`, p.x, p.y - 10);
    }

    // X-axis Session Date label
    ctx.font = '600 9px "Outfit", sans-serif';
    ctx.fillStyle = '#64748b';
    ctx.textAlign = 'center';
    ctx.fillText(p.date || `S${p.idx}`, p.x, padTop + chartH + 18);
  });
}

/**
 * Renders graceful empty state when user has no movement records
 */
function renderEvolutionEmptyState(msg) {
  const container = document.getElementById('evolutionMetricCardsGrid');
  if (container) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
        <i class="fa-solid fa-dna" style="font-size: 2.5rem; margin-bottom: 12px; opacity: 0.5; color: var(--accent-cyan);"></i>
        <div style="font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">Movement Evolution Ready</div>
        <p style="font-size: 0.85rem; max-width: 400px; margin: 0 auto;">${escapeHTML(msg)}</p>
      </div>
    `;
  }
}

// Global hook: Exercise dropdown change
document.addEventListener('DOMContentLoaded', () => {
  const selectEl = document.getElementById('evolutionExerciseSelect');
  if (selectEl) {
    selectEl.addEventListener('change', (e) => {
      const exId = parseInt(e.target.value, 10);
      if (exId) {
        loadMovementEvolution(exId);
      }
    });
  }
});

/**
 * Toggles progressive disclosure for Movement Evolution full history and charts.
 */
function toggleEvolutionDetails() {
  const content = document.getElementById('evolutionDetailsContent');
  const toggleBtn = document.getElementById('evolutionDetailsToggle');
  const toggleText = document.getElementById('evoToggleText');
  const toggleIcon = document.getElementById('evoToggleIcon');

  if (!content) return;
  const isHidden = content.style.display === 'none' || !content.classList.contains('open');

  if (isHidden) {
    content.style.display = 'flex';
    content.classList.add('open');
    if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');
    if (toggleText) toggleText.innerText = 'Hide History & Visualizations';
    if (toggleIcon) {
      toggleIcon.classList.remove('fa-chevron-down');
      toggleIcon.classList.add('fa-chevron-up');
    }
    // Re-draw canvases
    if (currentEvolutionData) {
      const radarCanvas = document.getElementById('evolutionRadarCanvas');
      if (radarCanvas) {
        drawDualFingerprintRadar(radarCanvas, currentEvolutionData.baseline_signature, currentEvolutionData.current_signature);
      }
      const historyCanvas = document.getElementById('evolutionHistoryCanvas');
      if (historyCanvas) {
        drawEvolutionHistoryCanvas(historyCanvas, currentEvolutionData.timeline || []);
      }
    }
  } else {
    content.style.display = 'none';
    content.classList.remove('open');
    if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
    if (toggleText) toggleText.innerText = 'View Full History & Visualizations';
    if (toggleIcon) {
      toggleIcon.classList.remove('fa-chevron-up');
      toggleIcon.classList.add('fa-chevron-down');
    }
  }
}
window.toggleEvolutionDetails = toggleEvolutionDetails;

