(() => {
  const toast = document.getElementById("toast");
  let toastTimer;

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 3200);
  }

  // Mobile navigation
  const menuButton = document.getElementById("mobileMenu");
  const nav = document.getElementById("mainNav");

  menuButton?.addEventListener("click", () => {
    nav.classList.toggle("open");
  });

  nav?.querySelectorAll("a").forEach(link => {
    link.addEventListener("click", () => nav.classList.remove("open"));
  });

  // Prompt suggestions
  document.querySelectorAll(".suggestion-chip").forEach(button => {
    button.addEventListener("click", () => {
      const input = document.getElementById("heroPrompt");
      input.value = button.dataset.prompt || "";
      input.focus();
    });
  });

  // Assistant entry point
  document.getElementById("heroChatForm")?.addEventListener("submit", event => {
    event.preventDefault();
    const input = document.getElementById("heroPrompt");
    const prompt = input.value.trim();

    if (!prompt) {
      showToast("Type a question or choose one of the suggestions.");
      input.focus();
      return;
    }

    // The chat page will be connected to the backend chat API in the next frontend stage.
    sessionStorage.setItem("schemesathi_initial_prompt", prompt);
    window.location.href = "pages/assistant.html";
  });

  // Service search
  document.getElementById("serviceSearchForm")?.addEventListener("submit", event => {
    event.preventDefault();
    const query = document.getElementById("serviceSearch").value.trim();

    if (!query) {
      showToast("Enter a service, scheme or document to search.");
      return;
    }

    window.location.href = `pages/services.html?q=${encodeURIComponent(query)}`;
  });

  // Voice input: browser Web Speech API where supported
  const voiceButton = document.getElementById("voiceButton");
  const voiceStatus = document.getElementById("voiceStatus");
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (voiceButton && SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = true;
    recognition.continuous = false;

    voiceButton.addEventListener("click", () => {
      try {
        recognition.start();
        voiceButton.classList.add("listening");
        voiceStatus.textContent = "Listening... speak now";
      } catch {
        showToast("Voice input is already active.");
      }
    });

    recognition.onresult = event => {
      const transcript = Array.from(event.results)
        .map(result => result[0].transcript)
        .join("");
      document.getElementById("heroPrompt").value = transcript;
    };

    recognition.onend = () => {
      voiceButton.classList.remove("listening");
      voiceStatus.textContent = "✦ Powered by AI";
    };

    recognition.onerror = () => {
      voiceButton.classList.remove("listening");
      voiceStatus.textContent = "Voice input unavailable";
      showToast("We couldn't access voice input. You can type your question instead.");
    };
  } else if (voiceButton) {
    voiceButton.addEventListener("click", () => {
      showToast("Voice input is not supported by this browser. Try Chrome or Edge.");
    });
  }

  // Language selector placeholder until multilingual preferences are connected
  document.getElementById("languageButton")?.addEventListener("click", () => {
    showToast("Indian-language selection will be enabled in the multilingual interface.");
  });
})();
