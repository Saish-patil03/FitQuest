/**
 * FitQuest — Premium Public Landing Page Controller
 * Manages Showcase Tab Switching, Interactive Telemetry HUD Mockups,
 * Smooth Section Navigation, and Seamless Application Entry Transitions.
 */

(function () {
  let isLandingActive = true;

  document.addEventListener('DOMContentLoaded', () => {
    initLandingPage();
  });

  function initLandingPage() {
    const landingView = document.getElementById('landingView');
    const enterBtns = document.querySelectorAll('.btn-landing-enter');
    const signInBtns = document.querySelectorAll('.btn-landing-signin');
    const brandLinks = document.querySelectorAll('.nav-brand, .landing-nav-brand');

    if (!landingView) return;

    // 1. Initialize Interactive Showcase Tabs
    initShowcaseTabs();

    // 2. Initialize Smooth Scrolling for Landing Navigation Links
    initLandingNavScroll();

    // 3. CTA Click Handlers — Enter FitQuest Main Application
    enterBtns.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        enterApplication();
      });
    });

    // 4. Sign In Button Handler — Directly opens Auth View (Login form)
    signInBtns.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        enterApplication('login');
      });
    });

    // 5. Brand Shift+Click Handler to return to Landing Page from authenticated view
    brandLinks.forEach((brand) => {
      brand.addEventListener('click', (e) => {
        if (e.shiftKey) {
          e.preventDefault();
          showLandingPage();
        }
      });
    });
  }

  /**
   * Initializes Interactive Product Showcase Tabs (Vision, Adaptive, Nutrition, Evolution)
   */
  function initShowcaseTabs() {
    const tabButtons = document.querySelectorAll('.showcase-tab-btn');
    const panels = {
      vision: document.getElementById('showcasePanelVision'),
      adaptive: document.getElementById('showcasePanelAdaptive'),
      nutrition: document.getElementById('showcasePanelNutrition'),
      evolution: document.getElementById('showcasePanelEvolution')
    };

    tabButtons.forEach((tab) => {
      tab.addEventListener('click', () => {
        const target = tab.getAttribute('data-showcase');
        if (!target || !panels[target]) return;

        // Update Tab active states & ARIA attributes
        tabButtons.forEach((t) => {
          t.classList.remove('active');
          t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');

        // Switch panels with smooth fade-in
        Object.keys(panels).forEach((key) => {
          const panel = panels[key];
          if (!panel) return;

          if (key === target) {
            panel.style.display = 'block';
            panel.style.opacity = '0';
            panel.classList.add('active');
            requestAnimationFrame(() => {
              panel.style.transition = 'opacity 0.3s ease';
              panel.style.opacity = '1';
            });
          } else {
            panel.style.display = 'none';
            panel.classList.remove('active');
          }
        });
      });
    });
  }

  /**
   * Smooth scroll navigation within the landing page container
   */
  function initLandingNavScroll() {
    const landingView = document.getElementById('landingView');
    const navLinks = document.querySelectorAll('.landing-nav-link, .btn-hero-secondary, .footer-link[href^="#"]');

    navLinks.forEach((link) => {
      link.addEventListener('click', (e) => {
        const href = link.getAttribute('href');
        if (!href || !href.startsWith('#')) return;

        const targetEl = document.querySelector(href);
        if (targetEl && landingView) {
          e.preventDefault();
          const targetOffset = targetEl.offsetTop - (document.getElementById('landingNavHeader')?.offsetHeight || 60);
          landingView.scrollTo({
            top: targetOffset,
            behavior: 'smooth'
          });
        }
      });
    });
  }

  /**
   * Transitions from Cinematic Landing Page into the main FitQuest application or auth screen
   * @param {string} [preferredForm='login']
   */
  function enterApplication(preferredForm) {
    const landingView = document.getElementById('landingView');
    if (!landingView) return;

    isLandingActive = false;
    landingView.classList.add('fade-out');

    setTimeout(() => {
      landingView.style.display = 'none';
      landingView.classList.remove('fade-out');
      landingView.scrollTop = 0;

      const token = localStorage.getItem('fitquest_token');
      const authView = document.getElementById('authView');
      const appMainWrapper = document.getElementById('appMainWrapper');

      if (token) {
        if (authView) authView.style.display = 'none';
        if (appMainWrapper) appMainWrapper.style.display = 'block';

        if (typeof switchTab === 'function') {
          switchTab('homeView');
        }
        if (typeof loadGamificationData === 'function') {
          loadGamificationData();
        }
      } else {
        if (appMainWrapper) appMainWrapper.style.display = 'none';
        if (authView) {
          authView.style.display = 'flex';
          authView.classList.add('active');

          if (preferredForm === 'login' && typeof showAuthFormContainer === 'function') {
            showAuthFormContainer('loginFormContainer');
            const loginTab = document.querySelector('.auth-tab-btn[data-auth-form="login"]');
            if (loginTab) {
              document.querySelectorAll('.auth-tab-btn').forEach(t => t.classList.remove('active'));
              loginTab.classList.add('active');
            }
          }
        }
      }
    }, 350);
  }

  /**
   * Re-displays the Landing Page
   */
  function showLandingPage() {
    const landingView = document.getElementById('landingView');
    const authView = document.getElementById('authView');
    const appMainWrapper = document.getElementById('appMainWrapper');

    if (landingView) {
      isLandingActive = true;
      landingView.scrollTop = 0;

      if (authView) authView.style.display = 'none';
      if (appMainWrapper) appMainWrapper.style.display = 'none';

      landingView.style.display = 'block';
      landingView.classList.remove('fade-out');
    }
  }

  window.enterFitquestApp = enterApplication;
  window.showLandingPage = showLandingPage;
})();
