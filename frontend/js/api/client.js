(() => {
  const configuredBase = document.querySelector('meta[name="schemesathi-api-base"]')?.content;
  const localHost = ["localhost", "127.0.0.1"].includes(window.location.hostname)
    ? window.location.hostname
    : "127.0.0.1";
  const API_BASE_URL = (configuredBase || `http://${localHost}:8000/api/v1`).replace(/\/$/, "");
  const SESSION_KEYS = {
    citizen: "schemesathi_citizen_authenticated",
    admin: "schemesathi_admin_authenticated"
  };
  const ACCESSIBILITY_KEY = "schemesathi_accessibility_v1";
  const ACCESSIBILITY_DEFAULTS = {
    font_size: "medium",
    text_scale_percent: 100,
    high_contrast: false,
    increased_spacing: false,
    large_buttons: false,
    simple_mode: false,
    read_aloud: false,
    reduced_motion: false
  };
  const sessionChecks = {};
  const memorySessions = { citizen: false, admin: false };
  let sessionStorageUnavailable = false;

  function normalizeAccessibilityPreferences(preferences = {}) {
    const legacy = preferences.largeText === true;
    return {
      ...ACCESSIBILITY_DEFAULTS,
      ...preferences,
      font_size: preferences.font_size ||
        (legacy ? "large" : ACCESSIBILITY_DEFAULTS.font_size),
      text_scale_percent: Number(preferences.text_scale_percent) ||
        (legacy ? 125 : ACCESSIBILITY_DEFAULTS.text_scale_percent)
    };
  }

  function applyAccessibilityPreferences(preferences, persist = true) {
    const normalized = normalizeAccessibilityPreferences(preferences);
    const root = document.documentElement;
    root.style.setProperty(
      "--accessibility-scale",
      String(normalized.text_scale_percent / 100)
    );
    if (document.body) {
      document.body.classList.toggle(
        "high-contrast",
        normalized.high_contrast
      );
      document.body.classList.toggle(
        "increased-spacing",
        normalized.increased_spacing
      );
      document.body.classList.toggle(
        "large-buttons",
        normalized.large_buttons
      );
      document.body.classList.toggle("simple-mode", normalized.simple_mode);
      document.body.classList.toggle(
        "reduced-motion",
        normalized.reduced_motion
      );
    }
    if (persist) {
      try {
        window.localStorage.setItem(
          ACCESSIBILITY_KEY,
          JSON.stringify(normalized)
        );
      } catch (error) {
        console.error("Could not cache accessibility preferences.", error);
      }
    }
    return normalized;
  }

  function loadCachedAccessibilityPreferences() {
    try {
      const cached = JSON.parse(
        window.localStorage.getItem(ACCESSIBILITY_KEY) || "{}"
      );
      applyAccessibilityPreferences(cached, false);
    } catch (error) {
      console.error("Could not load cached accessibility preferences.", error);
      applyAccessibilityPreferences(ACCESSIBILITY_DEFAULTS, false);
    }
  }

  function hasSession(scope) {
    if (!SESSION_KEYS[scope]) return false;
    if (memorySessions[scope]) return true;
    try {
      return window.sessionStorage.getItem(SESSION_KEYS[scope]) === "1";
    } catch {
      sessionStorageUnavailable = true;
      return false;
    }
  }

  function markAuthenticated(scope) {
    if (!SESSION_KEYS[scope]) throw new Error("Unknown authentication scope.");
    memorySessions[scope] = true;
    try {
      window.sessionStorage.setItem(SESSION_KEYS[scope], "1");
    } catch (error) {
      sessionStorageUnavailable = true;
      console.error("Could not save the non-secret sign-in state in this tab.", error);
    }
  }

  function clearSession(scope) {
    if (!SESSION_KEYS[scope]) return;
    memorySessions[scope] = false;
    try {
      window.sessionStorage.removeItem(SESSION_KEYS[scope]);
    } catch (error) {
      sessionStorageUnavailable = true;
      console.error("Could not clear the SchemeSathi sign-in state.", error);
    }
  }

  function redirectToLogin(scope) {
    const path = window.location.pathname;
    const relativePath = scope === "admin"
      ? path.includes("/pages/admin/") ? "login.html" : "pages/admin/login.html"
      : path.includes("/pages/admin/")
        ? "../login.html"
        : path.includes("/pages/")
          ? "login.html"
          : "pages/login.html";
    const login = new URL(relativePath, window.location.href);
    if (login.pathname === window.location.pathname) return;
    login.searchParams.set("next", `${window.location.pathname}${window.location.search}`);
    login.searchParams.set("expired", "1");
    window.location.replace(login.href);
  }

  function formatError(data, fallback) {
    const detail = data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail)) {
      const messages = detail.map(item => item?.msg).filter(Boolean);
      if (messages.length) return messages.join(" ");
    }
    if (detail && typeof detail === "object" && typeof detail.message === "string") {
      return detail.message;
    }
    return fallback;
  }

  async function request(path, options = {}) {
    const {
      auth = null,
      responseType = "json",
      redirectOnUnauthorized = true,
      headers: suppliedHeaders = {},
      ...fetchOptions
    } = options;
    const headers = new Headers(suppliedHeaders);
    const hasBody = fetchOptions.body !== undefined && fetchOptions.body !== null;
    const isFormData = hasBody && fetchOptions.body instanceof FormData;

    if (hasBody && !isFormData && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    let response;
    try {
      response = await fetch(`${API_BASE_URL}${path}`, {
        ...fetchOptions,
        credentials: "include",
        headers
      });
    } catch (error) {
      throw new Error("Could not reach the SchemeSathi server. Check your connection and try again.");
    }

    if (response.status === 401 && auth) {
      clearSession(auth);
      if (redirectOnUnauthorized) redirectToLogin(auth);
    }

    if (!response.ok) {
      const body = await response.text();
      let data = {};
      if (body) {
        try {
          data = JSON.parse(body);
        } catch (error) {
          data = { detail: body };
        }
      }
      const error = new Error(formatError(data, `Request failed (${response.status}).`));
      error.status = response.status;
      throw error;
    }

    if (auth) markAuthenticated(auth);
    if (response.status === 204) return null;
    if (responseType === "blob") return response.blob();
    if (responseType === "response") return response;

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const data = await response.json();
      if (path === "/users/me" && data.accessibility_preferences) {
        applyAccessibilityPreferences(data.accessibility_preferences);
      } else if (
        (path === "/auth/citizen/login" ||
          path === "/auth/citizen/register") &&
        data.citizen?.accessibility_preferences
      ) {
        applyAccessibilityPreferences(data.citizen.accessibility_preferences);
      }
      return data;
    }
    return response.text();
  }

  function jsonRequest(method, path, body, auth = null) {
    return request(path, {
      method,
      auth,
      ...(body === undefined ? {} : { body: JSON.stringify(body) })
    });
  }

  async function isAuthenticated(scope) {
    if (!SESSION_KEYS[scope]) throw new Error("Unknown authentication scope.");
    if (hasSession(scope)) return true;
    if (sessionChecks[scope]) return sessionChecks[scope];
    sessionChecks[scope] = checkSession(scope);
    try {
      return await sessionChecks[scope];
    } finally {
      delete sessionChecks[scope];
    }
  }

  async function checkSession(scope) {
    const path = scope === "admin" ? "/admin/dashboard" : "/users/me";
    try {
      await request(path, { auth: scope, redirectOnUnauthorized: false });
      return true;
    } catch (error) {
      if (error.status === 401) return false;
      throw error;
    }
  }

  function requireSession(scope) {
    if (hasSession(scope) || sessionStorageUnavailable) return true;
    redirectToLogin(scope);
    return false;
  }

  const api = {
    baseUrl: API_BASE_URL,
    request,
    get: (path, auth = null) => request(path, { auth }),
    post: (path, body, auth = null) => jsonRequest("POST", path, body, auth),
    put: (path, body, auth = null) => jsonRequest("PUT", path, body, auth),
    patch: (path, body, auth = null) => jsonRequest("PATCH", path, body, auth),
    delete: (path, auth = null) => jsonRequest("DELETE", path, undefined, auth),
    isAuthenticated,
    markAuthenticated,
    clearSession,
    applyAccessibilityPreferences,
    getAccessibilityPreferences: () => {
      try {
        return normalizeAccessibilityPreferences(
          JSON.parse(window.localStorage.getItem(ACCESSIBILITY_KEY) || "{}")
        );
      } catch (error) {
        console.error("Could not read accessibility preferences.", error);
        return { ...ACCESSIBILITY_DEFAULTS };
      }
    },
    requireCitizen: () => requireSession("citizen"),
    requireAdmin: () => requireSession("admin"),
    formatError
  };

  loadCachedAccessibilityPreferences();
  window.SchemeSathiAPI = api;
})();
