(() => {
  const STORAGE_KEY = "schemesathi_preferences";
  const PROFILE_KEY = "schemesathi_profile";
  const $ = id => document.getElementById(id);
  const toggleIds = ["applicationReminders","savedUpdates","newServices","productTips","largeText","reducedMotion","highContrast"];
  let toastTimer;

  function read(key) {
    try { return JSON.parse(localStorage.getItem(key) || "{}"); }
    catch { return {}; }
  }

  function notify(message) {
    $("toast").textContent = message;
    $("toast").classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $("toast").classList.remove("show"),2600);
  }

  function applyAccessibility(settings) {
    document.body.classList.toggle("large-text",Boolean(settings.largeText));
    document.body.classList.toggle("reduced-motion",Boolean(settings.reducedMotion));
    document.body.classList.toggle("high-contrast",Boolean(settings.highContrast));
  }

  function loadSettings() {
    const settings = read(STORAGE_KEY);
    const profile = read(PROFILE_KEY);
    $("language").value = settings.language || profile.preferredLanguage || "en";
    toggleIds.forEach(id => $(id).checked = Boolean(settings[id]));
    applyAccessibility(settings);
    $("topAvatar").textContent = profile.fullName?.trim()?.charAt(0)?.toUpperCase() || "S";
  }

  function collectSettings() {
    const settings = {language:$("language").value,updatedAt:new Date().toISOString()};
    toggleIds.forEach(id => settings[id] = $(id).checked);
    return settings;
  }

  function saveSettings() {
    const settings = collectSettings();
    try {
      localStorage.setItem(STORAGE_KEY,JSON.stringify(settings));
      const profile = read(PROFILE_KEY);
      profile.preferredLanguage = settings.language;
      profile.largeText = settings.largeText;
      profile.reducedMotion = settings.reducedMotion;
      localStorage.setItem(PROFILE_KEY,JSON.stringify(profile));
      applyAccessibility(settings);
      $("saveMessage").textContent = "Preferences saved on this device.";
      notify("Your preferences have been saved.");
    } catch {
      $("saveMessage").textContent = "Could not save preferences. Check browser storage settings.";
    }
  }

  $("saveSettings").addEventListener("click",saveSettings);

  $("resetSettings").addEventListener("click",() => {
    if (!window.confirm("Reset all preferences to their default values?")) return;
    localStorage.removeItem(STORAGE_KEY);
    toggleIds.forEach(id => $(id).checked = false);
    $("language").value = "en";
    const profile = read(PROFILE_KEY);
    profile.preferredLanguage = "en";
    profile.largeText = false;
    profile.reducedMotion = false;
    localStorage.setItem(PROFILE_KEY,JSON.stringify(profile));
    applyAccessibility({});
    $("saveMessage").textContent = "Preferences reset.";
    notify("Preferences have been reset.");
  });

  $("clearSearchHistory").addEventListener("click",() => {
    if (!window.confirm("Clear your recently viewed service history from this browser?")) return;
    localStorage.removeItem("schemesathi_recent_services");
    notify("Recent service history cleared.");
  });

  $("menuBtn").addEventListener("click",() => $("sidebar").classList.toggle("open"));
  document.addEventListener("click",event => {
    if (window.innerWidth <= 760 && !$("sidebar").contains(event.target) && !$("menuBtn").contains(event.target)) {
      $("sidebar").classList.remove("open");
    }
  });

  loadSettings();
})();
