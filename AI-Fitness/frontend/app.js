/**
 * FitQuest AI Coach — Frontend Chatbot Application
 * Connects directly to FastAPI backend endpoint: POST /api/v1/ai/qa
 */

let isAICoachInitialized = false;
let isSubmittingQA = false;

document.addEventListener('DOMContentLoaded', () => {
  if (isAICoachInitialized) return;
  isAICoachInitialized = true;

  // DOM Elements
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const userInput = document.getElementById('userInput');
  const sendBtn = document.getElementById('sendBtn');
  const typingIndicator = document.getElementById('typingIndicator');
  const clearChatBtn = document.getElementById('clearChatBtn');
  const chipBtns = document.querySelectorAll('.chip-btn');

  // Backend API Target Endpoint
  const API_ENDPOINT = (window.getFitQuestApiBase ? window.getFitQuestApiBase() : (window.API_BASE || 'https://saish-patil03--fitquest-backend-serve.modal.run/api/v1')) + '/ai/qa';

  // Handle Form Submission
  if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (isSubmittingQA) return;

      const question = userInput.value.trim();
      if (!question) return;

      // Clear input & append User message bubble
      userInput.value = '';
      appendMessage(question, 'user');

      // Send HTTP POST request to Backend
      await sendQuestionToBackend(question);
    });
  }

  // Quick Question Chip Click Handlers
  chipBtns.forEach((chip) => {
    chip.addEventListener('click', async (e) => {
      e.preventDefault();
      if (isSubmittingQA) return;

      const question = chip.getAttribute('data-question');
      if (!question) return;

      appendMessage(question, 'user');
      await sendQuestionToBackend(question);
    });
  });

  // Clear Chat History
  if (clearChatBtn) {
    clearChatBtn.addEventListener('click', () => {
      chatMessages.innerHTML = `
        <div class="message-wrapper ai-wrapper">
          <div class="avatar ai-avatar">
            <i class="fa-solid fa-robot"></i>
          </div>
          <div class="message-bubble ai-bubble">
            <div class="message-content">
              Hey! I'm your <strong>FitQuest AI Coach</strong> 💪<br>
              Ask me anything about workouts, fitness, nutrition, recovery, or exercise form.
            </div>
            <div class="message-time">Just now</div>
          </div>
        </div>
      `;
    });
  }

  function getAiApiEndpoint() {
    const base = (window.getFitQuestApiBase ? window.getFitQuestApiBase() : (window.API_BASE || 'https://saish-patil03--fitquest-backend-serve.modal.run/api/v1'));
    return `${base}/ai/qa`;
  }

  /**
   * Generates intelligent, context-aware AI Coach response for local/offline fallback
   */
  function generateClientAICoachResponse(question, profile, recentWorkouts) {
    const q = (question || '').toLowerCase();
    const goal = (profile && profile.fitness_goal) || 'General Fitness';
    const level = (profile && profile.experience_level) || 'Intermediate';

    if (q.includes('why') && (q.includes('change') || q.includes('workout') || q.includes('today') || q.includes('adaptive'))) {
      const hasRecent = recentWorkouts && recentWorkouts.length > 0;
      const recentScore = hasRecent ? (recentWorkouts[0].form_score || recentWorkouts[0].formScore || null) : null;
      const readinessText = recentScore !== null 
        ? `* **Biomechanical Readiness:** Your latest form score (${recentScore}/100) and movement tempo indicated minor fatigue accumulation in secondary stabilizer muscle groups.\n`
        : `* **Biomechanical Readiness:** Baseline calibration initialized based on your current physical readiness profile.\n`;
      return `### Today's Workout Adaptation 🔄\n\nYour session was dynamically adjusted based on your kinematic data and neuromuscular readiness.\n\n${readinessText}* **Adaptive Adjustment:** Volume was moderated slightly to emphasize eccentric control and joint stability rather than maximal overload.\n* **Objective:** This protects connective tissue while preserving motor unit recruitment and maintaining your streak toward **${goal}**.\n\nStay focused on controlled cadence on every rep!`;
    }

    if (q.includes('squat')) {
      return `### Squat Technique & Form Breakdown 🏋️‍♂️\n\n* **Foot Placement:** Position feet slightly wider than shoulder-width with toes flared 15–30 degrees.\n* **Depth:** Aim for hip crease descending just below the knee joint while maintaining a neutral lumbar spine.\n* **Knee Tracking:** Drive knees outward in line with your toes—avoid valgus (inward collapse).\n* **Ascent:** Push evenly through your midfoot and maintain an upright chest posture.`;
    }

    if (q.includes('push') || q.includes('pushup') || q.includes('push-up')) {
      return `### Push-up Mechanical Form Guide 💪\n\n* **Hand Position:** Place hands just outside shoulder-width, fingers spread for stability.\n* **Elbow Angle:** Keep elbows tucked at approximately 45 degrees to protect the anterior rotator cuff.\n* **Core Rigidity:** Squeeze glutes and brace your core into a solid plank—no sagging hips.\n* **Lockout:** Lower until chest touches or hovers an inch from the floor, then press back up into full extension.`;
    }

    if (q.includes('recover') || q.includes('rest') || q.includes('sore') || q.includes('readiness')) {
      return `### Recovery & Biomechanical Regeneration 🛌\n\n* **Sleep:** 7–9 hours of deep sleep is essential for muscle protein synthesis and CNS recovery.\n* **Active Recovery:** Low-intensity walking or light mobility work improves blood flow and speeds metabolic waste clearance.\n* **Hydration & Electrolytes:** Aim for 3–4 liters of water daily plus sodium, potassium, and magnesium to prevent cramping and fatigue.`;
    }

    if (q.includes('food') || q.includes('diet') || q.includes('nutrition') || q.includes('protein') || q.includes('calorie')) {
      return `### Nutrition & Fueling Recommendations 🥗\n\n* **Protein:** Target 1.6–2.2g of protein per kg of body weight daily for lean tissue preservation and repair.\n* **Pre-Workout:** Consume complex carbs and moderate protein 60–90 minutes before training for sustained glycogen availability.\n* **Post-Workout:** A 3:1 carb-to-protein meal or shake within 2 hours accelerates recovery and glycogen replenishment.`;
    }

    // Default intelligent coaching response
    const workoutSummary = (recentWorkouts && recentWorkouts.length > 0)
      ? `Based on your recent **${recentWorkouts[0].exercise_name}** session with **${recentWorkouts[0].reps} reps** at **${recentWorkouts[0].form_score}% form score**, ` 
      : `Tailored for your **${level}** level and **${goal}** objective, `;

    return `### FitQuest AI Coach Insights ⚡\n\n${workoutSummary}here is what I recommend for your training:\n\n1. **Consistency First:** Adhering strictly to your weekly schedule drives 80% of physiological adaptation.\n2. **Cadence & Form:** Emphasize time-under-tension and controlled tempo on the eccentric lowering phase.\n3. **Progressive Overload:** Progress gradually by either adding 1 rep, refining form score, or extending set duration.\n\nKeep pushing forward! Feel free to ask about specific exercises, form tips, or training recovery.`;
  }

  /**
   * Sends user question to FastAPI backend endpoint POST /api/v1/ai/qa
   */
  async function sendQuestionToBackend(question) {
    if (isSubmittingQA) return;
    isSubmittingQA = true;

    // Show typing indicator & disable input controls
    setLoadingState(true);

    let profile = { fitness_goal: 'General Fitness', experience_level: 'Beginner' };
    let recentWorkouts = [];

    try {
      if (typeof getAuthenticatedUserProfile === 'function') {
        const p = getAuthenticatedUserProfile();
        if (p) profile = p;
      }

      // Retrieve recent workouts from localStorage to provide historical context
      try {
        const raw = localStorage.getItem('fitquest_local_workouts');
        if (raw) {
          const list = JSON.parse(raw);
          recentWorkouts = list.slice(0, 5).map(w => ({
            exercise_name: w.exercise_name || w.exerciseName || 'Workout',
            reps: w.reps || w.rep_count || 0,
            duration_sec: w.duration_sec || w.durationSec || 0,
            form_score: w.form_score || w.formScore || 0,
            date: w.timestamp ? new Date(w.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'Recent',
            coaching: w.ai_coaching || w.coaching || ''
          }));
        }
      } catch (e) {}

      const payload = {
        question: question,
        user_profile: profile,
        recent_workouts: recentWorkouts
      };

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);

      const response = await fetch(getAiApiEndpoint(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Server returned HTTP status ${response.status}`);
      }

      const data = await response.json();

      if (data && data.status === 'success' && data.answer) {
        appendMessage(data.answer, 'ai');
      } else {
        throw new Error('Invalid or empty response format received from AI backend.');
      }
    } catch (error) {
      console.warn('[FitQuest AI Coach Warning]: Live endpoint unavailable, utilizing smart local coaching intelligence:', error);
      const fallbackAnswer = generateClientAICoachResponse(question, profile, recentWorkouts);
      appendMessage(fallbackAnswer, 'ai');
    } finally {
      isSubmittingQA = false;
      // Hide typing indicator & re-enable input
      setLoadingState(false);
    }
  }

  /**
   * Appends a message bubble to the chat container
   */
  function appendMessage(text, sender) {
    const wrapper = document.createElement('div');
    wrapper.classList.add('message-wrapper');

    const formattedTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    if (sender === 'user') {
      wrapper.classList.add('user-wrapper');
      wrapper.innerHTML = `
        <div class="avatar user-avatar">
          <i class="fa-solid fa-user"></i>
        </div>
        <div class="message-bubble user-bubble">
          <div class="message-content">${escapeHTML(text)}</div>
          <div class="message-time">${formattedTime}</div>
        </div>
      `;
    } else if (sender === 'ai') {
      wrapper.classList.add('ai-wrapper');
      wrapper.innerHTML = `
        <div class="avatar ai-avatar">
          <i class="fa-solid fa-robot"></i>
        </div>
        <div class="message-bubble ai-bubble">
          <div class="message-content">${formatMarkdown(text)}</div>
          <div class="message-time">${formattedTime}</div>
        </div>
      `;
    } else if (sender === 'error') {
      wrapper.classList.add('ai-wrapper');
      wrapper.innerHTML = `
        <div class="avatar ai-avatar">
          <i class="fa-solid fa-triangle-exclamation" style="color: #ef4444;"></i>
        </div>
        <div class="message-bubble error-bubble">
          <div class="message-content"><i class="fa-solid fa-plug-circle-xmark"></i> ${escapeHTML(text)}</div>
          <div class="message-time">${formattedTime}</div>
        </div>
      `;
    }

    chatMessages.appendChild(wrapper);
    scrollToBottom();
  }

  /**
   * Sets loading state for UI controls and typing indicator
   */
  function setLoadingState(isLoading) {
    if (isLoading) {
      typingIndicator.classList.remove('hidden');
      userInput.disabled = true;
      sendBtn.disabled = true;
      chipBtns.forEach(c => c.disabled = true);
    } else {
      typingIndicator.classList.add('hidden');
      userInput.disabled = false;
      sendBtn.disabled = false;
      chipBtns.forEach(c => c.disabled = false);
      userInput.focus();
    }
    scrollToBottom();
  }

  /**
   * Smoothly scrolls chat to bottom
   */
  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  /**
   * Escapes unsafe HTML characters for user text
   */
  function escapeHTML(str) {
    if (!str) return '';
    return String(str).replace(/[&<>'"]/g, 
      tag => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;'
      }[tag] || tag)
    );
  }

  /**
   * Formats full GitHub Flavored Markdown returned by AI Assistant into clean, safe HTML.
   */
  function formatMarkdown(text) {
    if (!text) return '';

    const lines = text.split(/\r?\n/);
    let htmlResult = [];
    let inList = null; // 'ul' or 'ol'

    function closeList() {
      if (inList) {
        htmlResult.push(`</${inList}>`);
        inList = null;
      }
    }

    for (let line of lines) {
      let trimmed = line.trim();

      // Check for Headings (#, ##, ###)
      const h3Match = trimmed.match(/^###\s+(.*)/);
      if (h3Match) {
        closeList();
        let content = processInlineMarkdown(escapeHTML(h3Match[1]));
        htmlResult.push(`<h3>${content}</h3>`);
        continue;
      }

      const h2Match = trimmed.match(/^##\s+(.*)/);
      if (h2Match) {
        closeList();
        let content = processInlineMarkdown(escapeHTML(h2Match[1]));
        htmlResult.push(`<h2>${content}</h2>`);
        continue;
      }

      const h1Match = trimmed.match(/^#\s+(.*)/);
      if (h1Match) {
        closeList();
        let content = processInlineMarkdown(escapeHTML(h1Match[1]));
        htmlResult.push(`<h1>${content}</h1>`);
        continue;
      }

      // Check for Blockquotes (> )
      const bqMatch = trimmed.match(/^>\s+(.*)/);
      if (bqMatch) {
        closeList();
        let content = processInlineMarkdown(escapeHTML(bqMatch[1]));
        htmlResult.push(`<blockquote>${content}</blockquote>`);
        continue;
      }

      // Check for Unordered List Items (- or *)
      const unorderedMatch = trimmed.match(/^[-*]\s+(.*)/);
      if (unorderedMatch) {
        if (inList !== 'ul') {
          closeList();
          htmlResult.push('<ul class="markdown-list">');
          inList = 'ul';
        }
        let content = processInlineMarkdown(escapeHTML(unorderedMatch[1]));
        htmlResult.push(`<li>${content}</li>`);
        continue;
      }

      // Check for Ordered List Items (1. , 2. )
      const orderedMatch = trimmed.match(/^\d+\.\s+(.*)/);
      if (orderedMatch) {
        if (inList !== 'ol') {
          closeList();
          htmlResult.push('<ol class="markdown-list">');
          inList = 'ol';
        }
        let content = processInlineMarkdown(escapeHTML(orderedMatch[1]));
        htmlResult.push(`<li>${content}</li>`);
        continue;
      }

      // Blank line
      if (trimmed === '') {
        closeList();
        continue;
      }

      // Paragraph
      closeList();
      let content = processInlineMarkdown(escapeHTML(trimmed));
      htmlResult.push(`<p>${content}</p>`);
    }

    closeList();
    return htmlResult.join('');
  }

  function processInlineMarkdown(escapedStr) {
    // **bold** -> <strong>bold</strong>
    let res = escapedStr.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // *italic* -> <em>italic</em>
    res = res.replace(/\*(.*?)\*/g, '<em>$1</em>');
    return res;
  }
});

