(() => {
  const STORAGE_KEY = "schemesathi_profile";
  const $ = id => document.getElementById(id);
  const form = $("profileForm");
  const fields = ["fullName","email","phone","state","district","preferredLanguage"];
  let toastTimer;

  function readProfile() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"); }
    catch { return {}; }
  }

  function updateSummary(data) {
    const name = data.fullName?.trim() || "Welcome!";
    const email = data.email?.trim() || "Add your email address";
    const initial = data.fullName?.trim()?.charAt(0)?.toUpperCase() || "S";
    $("displayName").textContent = name;
    $("displayEmail").textContent = email;
    $("largeAvatar").textContent = initial;
    $("topAvatar").textContent = initial;

    const checks = [
      !!data.fullName?.trim(), !!data.email?.trim(),
      !!data.phone?.trim(), !!data.state?.trim(),
      !!data.district?.trim(), !!data.preferredLanguage
    ];
    const percent = Math.round(checks.filter(Boolean).length / checks.length * 100);
    $("completionText").textContent = `${percent}%`;
    $("completionBar").style.width = `${percent}%`;
  }

  function loadProfile() {
    const data = readProfile();
    fields.forEach(key => {
      if ($(key)) $(key).value = data[key] || (key === "preferredLanguage" ? "en" : "");
    });
    $("reducedMotion").checked = Boolean(data.reducedMotion);
    $("largeText").checked = Boolean(data.largeText);
    updateSummary(data);
    applyAccessibility(data);
  }

  function applyAccessibility(data) {
    document.body.classList.toggle("large-text", Boolean(data.largeText));
    document.body.classList.toggle("reduced-motion", Boolean(data.reducedMotion));
  }

  function notify(message) {
    const toast = $("toast");
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    const email = $("email").value.trim();
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      $("email").focus();
      $("saveMessage").textContent = "Please enter a valid email address.";
      return;
    }

    const previous = readProfile();
    const data = {};
    fields.forEach(key => data[key] = $(key).value.trim());
    data.reducedMotion = $("reducedMotion").checked;
    data.largeText = $("largeText").checked;
    data.updatedAt = new Date().toISOString();

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({...previous, ...data}));
      updateSummary(data);
      applyAccessibility(data);
      $("saveMessage").textContent = "Saved on this device.";
      notify("Your profile has been saved.");
    } catch {
      $("saveMessage").textContent = "Could not save. Check browser storage settings.";
    }
  });

  $("privacyInfo").addEventListener("click", event => {
    event.preventDefault();
    notify("Profile details are currently stored in this browser only.");
  });

  $("menuBtn").addEventListener("click", () => $("sidebar").classList.toggle("open"));
  document.addEventListener("click", event => {
    if (window.innerWidth <= 760 &&
        !$("sidebar").contains(event.target) &&
        !$("menuBtn").contains(event.target)) {
      $("sidebar").classList.remove("open");
    }
  });

  loadProfile();
})();
