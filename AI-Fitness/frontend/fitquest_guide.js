/**
 * FITQUEST GUIDE™ — Frontend In-App Help Chatbot
 * Provides interactive guidance, feature explanations, and navigation assistance.
 * Completely isolated from the AI Coach.
 */

(function () {
  'use strict';

  let isGuideOpen = false;
  let isGuideSubmitting = false;
  const guideHistory = [];

  // DOM Elements cache
  let containerEl = null;
  let launcherBtn = null;
  let panelEl = null;
  let messagesEl = null;
  let formEl = null;
  let inputEl = null;
  let sendBtnEl = null;
  let typingIndicatorEl = null;
  let minimizeBtnEl = null;
  let closeBtnEl = null;

  document.addEventListener('DOMContentLoaded', () => {
    initFitQuestGuide();
  });

  function initFitQuestGuide() {
    containerEl = document.getElementById('fitquestGuideContainer');
    launcherBtn = document.getElementById('fitquestGuideLauncher');
    panelEl = document.getElementById('fitquestGuidePanel');
    messagesEl = document.getElementById('fitquestGuideMessages');
    formEl = document.getElementById('fitquestGuideForm');
    inputEl = document.getElementById('fitquestGuideInput');
    sendBtnEl = document.getElementById('fitquestGuideSendBtn');
    typingIndicatorEl = document.getElementById('fitquestGuideTypingIndicator');
    minimizeBtnEl = document.getElementById('fitquestGuideMinimizeBtn');
    closeBtnEl = document.getElementById('fitquestGuideCloseBtn');

    if (!containerEl || !launcherBtn || !panelEl) {
      console.warn('[FitQuest Guide]: Container elements not found in DOM.');
      return;
    }

    // Toggle Launcher
    launcherBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleGuide();
    });

    // Minimize / Close Buttons
    if (minimizeBtnEl) {
      minimizeBtnEl.addEventListener('click', (e) => {
        e.stopPropagation();
        closeGuide();
      });
    }

    if (closeBtnEl) {
      closeBtnEl.addEventListener('click', (e) => {
        e.stopPropagation();
        closeGuide();
      });
    }

    // Handle Form Submission
    if (formEl) {
      formEl.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (isGuideSubmitting) return;

        const question = inputEl ? inputEl.value.trim() : '';
        if (!question) return;

        if (inputEl) inputEl.value = '';
        await askGuide(question);
      });
    }

    // Handle Quick Suggestion Chips
    const chips = containerEl.querySelectorAll('.fitquest-guide-chip');
    chips.forEach((chip) => {
      chip.addEventListener('click', async (e) => {
        e.preventDefault();
        if (isGuideSubmitting) return;
        const question = chip.getAttribute('data-question') || chip.textContent.trim();
        if (question) {
          await askGuide(question);
        }
      });
    });

    // Global navigation bridge
    window.fitquestGuideNavigate = function (viewId) {
      if (typeof switchTab === 'function') {
        switchTab(viewId);
      }
    };

    console.log('[FitQuest Guide]: Initialized successfully.');
  }

  function toggleGuide(forceState) {
    const targetState = typeof forceState === 'boolean' ? forceState : !isGuideOpen;
    if (targetState) {
      openGuide();
    } else {
      closeGuide();
    }
  }

  function openGuide() {
    isGuideOpen = true;
    if (panelEl) {
      panelEl.classList.remove('fitquest-guide-hidden');
      panelEl.setAttribute('aria-hidden', 'false');
    }
    if (launcherBtn) {
      launcherBtn.classList.add('fitquest-guide-active');
    }
    if (inputEl) {
      setTimeout(() => inputEl.focus(), 150);
    }
    scrollMessagesToBottom();
  }

  function closeGuide() {
    isGuideOpen = false;
    if (panelEl) {
      panelEl.classList.add('fitquest-guide-hidden');
      panelEl.setAttribute('aria-hidden', 'true');
    }
    if (launcherBtn) {
      launcherBtn.classList.remove('fitquest-guide-active');
    }
  }

  async function askGuide(question) {
    if (!question || isGuideSubmitting) return;
    isGuideSubmitting = true;

    // Append user message
    appendMessage(question, 'user');
    guideHistory.push({ role: 'user', content: question });

    // Show loading state
    setLoadingState(true);

    // Identify current active view in the application
    const activePanel = document.querySelector('.view-panel.active');
    const currentViewId = activePanel ? activePanel.id : 'homeView';

    const apiBase = window.getFitQuestApiBase ? window.getFitQuestApiBase() : (window.API_BASE || 'https://fitquest-backend-1brv.onrender.com/api/v1');
    const endpoint = `${apiBase}/guide/chat`;

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: question,
          current_view: currentViewId,
          conversation_history: guideHistory.slice(-6)
        })
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP status ${res.status}`);
      }

      const data = await res.json();
      const reply = data.reply || "I'm here to help you navigate FitQuest! What would you like to know?";
      const navSuggestion = data.nav_suggestion || data.nav_action;

      guideHistory.push({ role: 'assistant', content: reply });
      appendMessage(reply, 'assistant', navSuggestion);

      // Auto-trigger navigation if explicit nav action was returned
      if (data.nav_action && typeof switchTab === 'function') {
        switchTab(data.nav_action);
      }
    } catch (err) {
      console.warn('[FitQuest Guide]: Request failed:', err);
      appendMessage(
        "I'm having trouble connecting to the guide service right now. Please try asking again in a moment.",
        'assistant'
      );
    } finally {
      setLoadingState(false);
      isGuideSubmitting = false;
      if (inputEl) inputEl.focus();
    }
  }

  function appendMessage(text, role, navTarget) {
    if (!messagesEl) return;

    const wrapper = document.createElement('div');
    wrapper.className = `fitquest-guide-msg-wrapper fitquest-guide-${role}`;

    const bubble = document.createElement('div');
    bubble.className = `fitquest-guide-msg-bubble fitquest-guide-${role}-bubble`;

    if (role === 'assistant') {
      const formattedHtml = formatGuideMarkdown(text);
      bubble.innerHTML = `<div class="fitquest-guide-msg-text">${formattedHtml}</div>`;

      // Optional Navigation Action Chip
      if (navTarget) {
        const viewLabelMap = {
          homeView: 'Dashboard',
          workoutView: 'Workout',
          nutritionView: 'Nutrition',
          movementDnaView: 'Movement DNA™',
          adaptiveTrainingView: 'Adaptive AI',
          evolutionView: 'Evolution',
          progressView: 'Analytics',
          aiCoachView: 'AI Coach',
          historyView: 'History'
        };
        const label = viewLabelMap[navTarget] || 'Go to Section';
        const actionBtn = document.createElement('button');
        actionBtn.type = 'button';
        actionBtn.className = 'fitquest-guide-nav-btn';
        actionBtn.innerHTML = `<i class="fa-solid fa-arrow-right-to-bracket"></i> Open ${label}`;
        actionBtn.onclick = () => {
          if (typeof switchTab === 'function') {
            switchTab(navTarget);
          }
        };
        bubble.appendChild(actionBtn);
      }
    } else {
      bubble.textContent = text;
    }

    wrapper.appendChild(bubble);
    messagesEl.appendChild(wrapper);
    scrollMessagesToBottom();
  }

  function formatGuideMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);

    // Headers (### Header)
    html = html.replace(/^### (.*$)/gim, '<h4 class="fitquest-guide-h4">$1</h4>');

    // Bold (**text**)
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italics (*text*)
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Bullet points (• or -)
    html = html.replace(/^[•\-]\s+(.*$)/gim, '<div class="fitquest-guide-bullet"><span class="fitquest-guide-dot">•</span> <span>$1</span></div>');

    // Numbered lists (1. Item)
    html = html.replace(/^(\d+)\.\s+(.*$)/gim, '<div class="fitquest-guide-bullet"><span class="fitquest-guide-num">$1.</span> <span>$2</span></div>');

    // Paragraph breaks
    html = html.replace(/\n\n/g, '<div class="fitquest-guide-gap"></div>');
    html = html.replace(/\n/g, '<br>');

    return html;
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function setLoadingState(isLoading) {
    if (typingIndicatorEl) {
      if (isLoading) {
        typingIndicatorEl.classList.remove('fitquest-guide-hidden');
      } else {
        typingIndicatorEl.classList.add('fitquest-guide-hidden');
      }
    }
    if (sendBtnEl) {
      sendBtnEl.disabled = isLoading;
    }
    if (inputEl) {
      inputEl.disabled = isLoading;
    }
    scrollMessagesToBottom();
  }

  function scrollMessagesToBottom() {
    if (messagesEl) {
      requestAnimationFrame(() => {
        messagesEl.scrollTop = messagesEl.scrollHeight;
      });
    }
  }

  // Expose global controller
  window.fitquestGuide = {
    toggle: toggleGuide,
    open: openGuide,
    close: closeGuide,
    ask: askGuide
  };
})();
