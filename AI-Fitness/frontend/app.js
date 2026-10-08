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
  const API_ENDPOINT = (window.getFitQuestApiBase ? window.getFitQuestApiBase() : (window.API_BASE || 'https://fitquest-backend-1brv.onrender.com/api/v1')) + '/ai/qa';

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

  /**
   * Sends user question to FastAPI backend endpoint POST /api/v1/ai/qa
   */
  async function sendQuestionToBackend(question) {
    if (isSubmittingQA) return;
    isSubmittingQA = true;

    // Show typing indicator & disable input controls
    setLoadingState(true);

    try {
      const profile = typeof getAuthenticatedUserProfile === 'function' 
        ? getAuthenticatedUserProfile() 
        : { fitness_goal: 'General Fitness', experience_level: 'Beginner' };

      const payload = {
        question: question,
        user_profile: profile
      };

      const response = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
      });

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
      console.error('[FitQuest Frontend Error]:', error);
      const errorMessage = `Sorry, I couldn't connect to the FitQuest AI Coach. Please make sure the backend server is running.`;
      appendMessage(errorMessage, 'error');
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

