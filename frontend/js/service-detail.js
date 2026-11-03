(() => {
  const params = new URLSearchParams(window.location.search);
  const category = params.get("category") || "";
  const serviceId = params.get("id") || "";
  const titleCase = value => value.replace(/[-_]/g, " ").replace(/\b\w/g, char => char.toUpperCase());
  const title = category ? titleCase(category) : "Government service";
  const $ = id => document.getElementById(id);
  let toastTimer;

  $("categoryTag").textContent = category ? title.toUpperCase() : "SERVICE CATEGORY";
  $("serviceTitle").textContent = category ? `${title} services, made easier to understand.` : "Understand your government service.";
  $("serviceDescription").textContent = category
    ? `Explore information related to ${title.toLowerCase()}. SchemeSathi will help organise service details, eligibility, documents and official application guidance when verified records are available.`
    : "Find the information you need to understand a government service, prepare documents and identify the right official application channel.";
  document.title = `${title} | SchemeSathi`;

  function notify(message) {
    const toast = $("toast");
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
  }

  function getSaved() {
    try { return JSON.parse(localStorage.getItem("schemesathi_saved_services") || "[]"); }
    catch { return []; }
  }

  function saveCategory() {
    const key = category || "general";
    const saved = getSaved();
    const exists = saved.some(item => (typeof item === "string" ? item : item.category) === key);
    if (exists) {
      notify("This category is already in your saved list.");
      return;
    }
    saved.push({category:key, title, savedAt:new Date().toISOString()});
    localStorage.setItem("schemesathi_saved_services", JSON.stringify(saved));
    $("saveService").textContent = "♥ Saved";
    notify("Added to your saved services on this device.");
  }

  function askAssistant(prompt) {
    const context = `I am exploring ${title}. ${prompt}`;
    sessionStorage.setItem("schemesathi_initial_prompt", context);
    window.location.href = "assistant.html";
  }

  $("saveService").addEventListener("click", saveCategory);
  $("askAI").addEventListener("click", () => askAssistant("Explain what information I should look for."));
  $("openAssistant").addEventListener("click", () => askAssistant("Help me understand this service."));
  document.querySelectorAll("[data-prompt]").forEach(button => {
    button.addEventListener("click", () => askAssistant(button.dataset.prompt));
  });

  const tabs = [...document.querySelectorAll(".tab")];
  tabs.forEach(tab => tab.addEventListener("click", () => {
    const target = document.getElementById(tab.dataset.target);
    if (!target) return;
    tabs.forEach(item => item.classList.toggle("active", item === tab));
    target.scrollIntoView({behavior:"smooth", block:"start"});
  }));

  const observer = new IntersectionObserver(entries => {
    const visible = entries.filter(entry => entry.isIntersecting).sort((a,b) => b.intersectionRatio-a.intersectionRatio)[0];
    if (!visible) return;
    tabs.forEach(tab => tab.classList.toggle("active", tab.dataset.target === visible.target.id));
  }, {rootMargin:"-18% 0px -65% 0px", threshold:[0,.15,.4]});
  document.querySelectorAll(".detail-section").forEach(section => observer.observe(section));

  $("mobileMenu").addEventListener("click", () => document.querySelector(".main-nav").classList.toggle("open"));

  if (serviceId) {
    // The service ID is retained for the future verified catalogue API integration.
    console.info("Selected SchemeSathi service ID:", serviceId);
  }

  if (getSaved().some(item => (typeof item === "string" ? item : item.category) === (category || "general"))) {
    $("saveService").textContent = "♥ Saved";
  }
})();
