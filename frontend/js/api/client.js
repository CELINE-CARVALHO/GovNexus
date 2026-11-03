const SchemeSathiAPI = (() => {
  const API_BASE_URL = "http://127.0.0.1:8000/api/v1";

  async function request(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `Request failed (${response.status})`);
    }

    return response.json();
  }

  return {
    baseUrl: API_BASE_URL,
    getServices: (params = "") => request(`/services${params}`),
    getServiceDetails: (id, language = "en") =>
      request(`/services/${encodeURIComponent(id)}/details?language=${encodeURIComponent(language)}`)
  };
})();

window.SchemeSathiAPI = SchemeSathiAPI;
