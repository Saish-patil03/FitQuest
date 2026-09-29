/**
 * FitQuest Centralized API & Environment Configuration
 * Single source of truth for:
 * 1. Main Application Backend API (Render in Production, localhost:8000 in Dev)
 * 2. Dedicated Modal Computer Vision & ML Microservice
 */
(function(window) {
  'use strict';

  // Environment detection: local development vs production
  var hostname = (typeof window !== 'undefined' && window.location && window.location.hostname) || '';
  var protocol = (typeof window !== 'undefined' && window.location && window.location.protocol) || '';

  var isLocalDev = Boolean(
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '0.0.0.0' ||
    hostname.endsWith('.local') ||
    protocol === 'file:' ||
    !hostname
  );

  // Production Endpoints
  var PRODUCTION_BACKEND_URL = 'https://fitquest-backend-1brv.onrender.com/api/v1';
  var PRODUCTION_MODAL_ML_URL = 'https://nihartambe20--fitquest-ml-fastapi-app.modal.run';

  // Local Development Endpoints
  var LOCAL_BACKEND_URL = 'http://127.0.0.1:8000/api/v1';
  var LOCAL_MODAL_ML_URL = 'http://127.0.0.1:8100';

  /**
   * Resolves the active backend API base URL
   * Priority:
   * 1. Explicit window.FITQUEST_API_OVERRIDE (testing / manual override)
   * 2. Existing window.API_BASE if explicitly set and not conflicting
   * 3. Localhost:8000 if running in local environment
   * 4. Production Render backend URL (default)
   */
  function getApiBase() {
    if (typeof window !== 'undefined' && window.FITQUEST_API_OVERRIDE) {
      return window.FITQUEST_API_OVERRIDE;
    }
    if (typeof window !== 'undefined' && window.API_BASE) {
      // If running on remote domain (like Vercel), reject unintended localhost values
      if (!isLocalDev && (window.API_BASE.indexOf('127.0.0.1') !== -1 || window.API_BASE.indexOf('localhost') !== -1)) {
        return PRODUCTION_BACKEND_URL;
      }
      return window.API_BASE;
    }
    return isLocalDev ? LOCAL_BACKEND_URL : PRODUCTION_BACKEND_URL;
  }

  /**
   * Resolves the active Modal ML base URL
   * Priority:
   * 1. Explicit window.FITQUEST_ML_OVERRIDE (testing / manual override)
   * 2. Existing window.ML_API_BASE if explicitly set
   * 3. Local ML microservice (port 8100) ONLY if isLocalDev and USE_LOCAL_ML toggle is enabled
   * 4. Production Modal ML URL (default)
   */
  function getMlBase() {
    if (typeof window !== 'undefined' && window.FITQUEST_ML_OVERRIDE) {
      return window.FITQUEST_ML_OVERRIDE;
    }
    if (typeof window !== 'undefined' && window.ML_API_BASE) {
      if (!isLocalDev && (window.ML_API_BASE.indexOf('127.0.0.1') !== -1 || window.ML_API_BASE.indexOf('localhost') !== -1)) {
        return PRODUCTION_MODAL_ML_URL;
      }
      return window.ML_API_BASE;
    }
    return isLocalDev ? LOCAL_BACKEND_URL : PRODUCTION_MODAL_ML_URL;
  }

  // Assign to window object
  window.FITQUEST_CONFIG = {
    isLocalDev: isLocalDev,
    productionBackendUrl: PRODUCTION_BACKEND_URL,
    productionModalMlUrl: PRODUCTION_MODAL_ML_URL,
    localBackendUrl: LOCAL_BACKEND_URL,
    localModalMlUrl: LOCAL_MODAL_ML_URL,
    getApiBase: getApiBase,
    getMlBase: getMlBase
  };

  window.API_BASE = getApiBase();
  window.ML_API_BASE = getMlBase();
  window.getFitQuestApiBase = getApiBase;
  window.getFitQuestMlBase = getMlBase;

})(typeof window !== 'undefined' ? window : this);
