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
  const heroPrompt = document.getElementById("heroPrompt");

  menuButton?.addEventListener("click", () => {
    nav.classList.toggle("open");
  });

  nav?.querySelectorAll("a").forEach(link => {
    link.addEventListener("click", () => nav.classList.remove("open"));
  });

  // Prompt suggestions
  document.querySelectorAll(".suggestion-chip").forEach(button => {
    button.addEventListener("click", () => {
      heroPrompt.value = button.dataset.prompt || "";
      heroPrompt.focus();
    });
  });

  const api = window.SchemeSathiAPI;
  let citizenProfilePromise = null;

  function getCitizenProfile() {
    if (!citizenProfilePromise) {
      citizenProfilePromise = api.get("/users/me", "citizen");
    }
    return citizenProfilePromise;
  }

  async function getAllPages(path) {
    const items = [];
    let page = 1;
    let pages = 1;
    do {
      const separator = path.includes("?") ? "&" : "?";
      const result = await api.get(`${path}${separator}page=${page}&limit=100`);
      items.push(...(Array.isArray(result.items) ? result.items : []));
      pages = Number(result.pagination?.pages) || 1;
      page += 1;
    } while (page <= pages);
    return items;
  }

  async function loadHomeCategories() {
    const grid = document.getElementById("homeCategoryGrid");
    if (!grid) return;
    try {
      const categories = await getAllPages("/categories?language=en&active_only=true");
      grid.replaceChildren();
      if (!categories.length) {
        grid.appendChild(Object.assign(document.createElement("p"), {
          textContent: "No active service categories are available."
        }));
        return;
      }
      const colors = ["blue", "peach", "green", "lilac", "yellow", "mint"];
      const icons = ["▣", "✧", "♡", "₹", "⌂", "＋"];
      categories.forEach((category, index) => {
        const card = document.createElement("a");
        card.className = `category-card category-${colors[index % colors.length]}`;
        card.href = `pages/services.html?category=${encodeURIComponent(category.id)}`;
        const icon = document.createElement("span");
        icon.className = "category-icon";
        icon.textContent = icons[index % icons.length];
        const label = document.createElement("span");
        label.className = "category-count";
        label.textContent = "SERVICE CATEGORIES";
        const title = document.createElement("strong");
        title.textContent = category.name || category.code;
        const arrow = document.createElement("span");
        arrow.className = "category-arrow";
        arrow.textContent = "↗";
        card.append(icon, label, title, arrow);
        grid.appendChild(card);
      });
    } catch (error) {
      grid.replaceChildren();
      const message = document.createElement("p");
      message.setAttribute("role", "status");
      message.textContent = `Published categories are unavailable: ${error.message}`;
      grid.appendChild(message);
    }
  }

  async function loadHomeSavedServices() {
    const container = document.getElementById("homeSavedServices");
    if (!container) return;
    try {
      if (!await api.isAuthenticated("citizen")) {
        container.replaceChildren();
        const message = document.createElement("p");
        message.textContent = "Sign in to view your saved services.";
        const link = document.createElement("a");
        link.href = "pages/login.html";
        link.textContent = "Sign in";
        container.append(message, link);
        return;
      }
    } catch (error) {
      container.replaceChildren();
      const message = document.createElement("p");
      message.textContent = `Saved services are unavailable: ${error.message}`;
      container.appendChild(message);
      return;
    }
    try {
      const profile = await getCitizenProfile();
      const result = await api.get(
        `/users/me/saved-services?language=${encodeURIComponent(profile.preferred_language_code || "en")}`,
        "citizen"
      );
      const services = Array.isArray(result.items) ? result.items : [];
      container.replaceChildren();
      if (!services.length) {
        const message = document.createElement("p");
        message.textContent = "You have not saved any published services yet.";
        const link = document.createElement("a");
        link.href = "pages/services.html";
        link.textContent = "Explore services";
        container.append(message, link);
        return;
      }
      services.slice(0, 3).forEach(service => {
        const link = document.createElement("a");
        link.className = "recommendation-item";
        link.href = `pages/service-detail.html?id=${encodeURIComponent(service.service_id)}`;
        const icon = document.createElement("span");
        icon.className = "recommendation-icon rec-violet";
        icon.textContent = "♡";
        const details = document.createElement("span");
        const title = document.createElement("strong");
        title.textContent = service.title || service.code;
        const description = document.createElement("span");
        description.textContent = service.description || "Published service";
        details.append(title, description);
        const arrow = document.createElement("span");
        arrow.className = "recommendation-chevron";
        arrow.textContent = "↗";
        link.append(icon, details, arrow);
        container.appendChild(link);
      });
      if (services.length > 3) {
        const all = document.createElement("a");
        all.href = "pages/dashboard.html#savedSection";
        all.textContent = "View all saved services →";
        container.appendChild(all);
      }
    } catch (error) {
      container.replaceChildren();
      const message = document.createElement("p");
      message.setAttribute("role", "status");
      message.textContent = `Saved services are unavailable: ${error.message}`;
      container.appendChild(message);
    }
  }

  // Assistant entry point
  document.getElementById("heroChatForm")?.addEventListener("submit", event => {
    event.preventDefault();
    const prompt = heroPrompt.value.trim();

    if (!prompt) {
      showToast("Type a question or choose one of the suggestions.");
      heroPrompt.focus();
      return;
    }

    try {
      sessionStorage.setItem("schemesathi_initial_prompt", prompt);
      window.location.href = "pages/assistant.html";
    } catch (error) {
      showToast("Could not open the assistant prompt in this browser session.");
    }
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

  // Gnani Prisma voice input
  const MAX_RECORDING_SECONDS = 30;
  const voiceButton = document.getElementById("voiceButton");
  const voiceStatus = document.getElementById("voiceStatus");
  const languageSelect = document.getElementById("voiceLanguage");
  const languageButton = document.getElementById("languageButton");

  function updateLanguageButton() {
    if (!languageButton || !languageSelect.value) return;
    const option = languageSelect.options[languageSelect.selectedIndex];
    languageButton.childNodes.forEach(node => {
      if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
        node.textContent = ` ${option.textContent.split("—").pop().trim()} `;
      }
    });
  }

  let microphoneStream = null;
  let audioContext = null;
  let processor = null;
  let mutedOutput = null;
  let audioChunks = [];
  let recording = false;
  let recordingTimeout = null;

  function setVoiceState(active, label) {
    voiceButton?.classList.toggle("listening", active);
    if (voiceButton) {
      voiceButton.setAttribute("aria-pressed", String(active));
      voiceButton.title = label;
    }
    if (voiceStatus) voiceStatus.textContent = active ? "Listening · up to 30 seconds" : label;
  }

  async function loadVoiceLanguages() {
    const supportedCodes = new Set(["bn", "en", "gu", "hi", "kn", "ml", "mr", "pa", "ta", "te"]);
    try {
      const result = await api.get("/languages?active_only=true");
      const items = (result.items || []).filter(item =>
        supportedCodes.has(String(item.code).split("-")[0].toLowerCase())
      );
      languageSelect.replaceChildren();
      items.forEach(item => {
        const code = `${String(item.code).split("-")[0].toLowerCase()}-IN`;
        const option = new Option(
          item.native_name ? `${item.native_name} — ${item.english_name}` : item.english_name,
          code
        );
        languageSelect.appendChild(option);
      });

      const requestedLanguage = items[0]
        ? `${String(items[0].code).split("-")[0].toLowerCase()}-IN`
        : "";
      if (await api.isAuthenticated("citizen")) {
        const profile = await getCitizenProfile();
        const preferred = `${String(profile.preferred_language_code || "").split("-")[0].toLowerCase()}-IN`;
        languageSelect.value = [...languageSelect.options].some(option => option.value === preferred)
          ? preferred
          : requestedLanguage;
      } else {
        languageSelect.value = requestedLanguage;
      }
      if (!languageSelect.value) {
        voiceButton.disabled = true;
        voiceStatus.textContent = "Voice input is unavailable in this language.";
      }
      updateLanguageButton();
    } catch (error) {
      voiceButton.disabled = true;
      voiceStatus.textContent = `Voice languages unavailable: ${error.message}`;
    }
  }

  function encodeWav(samples, sampleRate) {
    const bytesPerSample = 2;
    const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample);
    const view = new DataView(buffer);

    function writeString(offset, value) {
      for (let i = 0; i < value.length; i++) {
        view.setUint8(offset + i, value.charCodeAt(i));
      }
    }

    writeString(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, "data");
    view.setUint32(40, samples.length * 2, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const sample = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(
        offset,
        sample < 0 ? sample * 0x8000 : sample * 0x7fff,
        true
      );
    }

    return new Blob([buffer], { type: "audio/wav" });
  }

  function downsample(samples, inputRate, outputRate) {
    if (inputRate === outputRate) return new Float32Array(samples);

    const ratio = inputRate / outputRate;
    const outputLength = Math.floor(samples.length / ratio);
    const output = new Float32Array(outputLength);

    for (let i = 0; i < outputLength; i++) {
      const start = Math.floor(i * ratio);
      const end = Math.min(Math.floor((i + 1) * ratio), samples.length);

      let total = 0;
      for (let j = start; j < end; j++) total += samples[j];

      output[i] = total / Math.max(1, end - start);
    }

    return output;
  }

  async function startGnaniRecording() {
    if (!navigator.mediaDevices?.getUserMedia ||
        !(window.AudioContext || window.webkitAudioContext)) {
      showToast("This browser does not support microphone recording.");
      return;
    }
    if (!window.isSecureContext && location.hostname !== "localhost" &&
        location.hostname !== "127.0.0.1") {
      showToast("Microphone access requires HTTPS or localhost.");
      return;
    }
    try {
      microphoneStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      if (audioContext.state === "suspended") await audioContext.resume();
      const source = audioContext.createMediaStreamSource(microphoneStream);

      processor = audioContext.createScriptProcessor(4096, 1, 1);
      mutedOutput = audioContext.createGain();
      mutedOutput.gain.value = 0;
      audioChunks = [];
      recording = true;

      processor.onaudioprocess = event => {
        if (!recording) return;
        audioChunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };

      source.connect(processor);
      processor.connect(mutedOutput);
      mutedOutput.connect(audioContext.destination);

      setVoiceState(true, "Stop recording");
      showToast("Listening. Speak your question clearly.");

      recordingTimeout = setTimeout(() => {
        if (recording) stopGnaniRecording();
      }, MAX_RECORDING_SECONDS * 1000);

    } catch (error) {
      console.error("Microphone error:", error);
      cleanupGnaniRecording();
      setVoiceState(false, "Speak");
      showToast("Microphone access failed. Check browser permissions.");
    }
  }

  function cleanupGnaniRecording() {
    if (recordingTimeout) clearTimeout(recordingTimeout);
    recordingTimeout = null;

    if (processor) {
      processor.disconnect();
      processor.onaudioprocess = null;
      processor = null;
    }

    if (mutedOutput) {
      mutedOutput.disconnect();
      mutedOutput = null;
    }

    if (microphoneStream) {
      microphoneStream.getTracks().forEach(track => track.stop());
      microphoneStream = null;
    }

    if (audioContext) {
      audioContext.close().catch(error => console.error("Could not close the audio context.", error));
      audioContext = null;
    }

    recording = false;
    setVoiceState(false, "Speak");
  }

  async function stopGnaniRecording() {
    if (!recording || !audioContext) return;

    const sourceRate = audioContext.sampleRate;
    const mergedLength = audioChunks.reduce(
      (total, chunk) => total + chunk.length, 0
    );

    const merged = new Float32Array(mergedLength);
    let offset = 0;

    audioChunks.forEach(chunk => {
      merged.set(chunk, offset);
      offset += chunk.length;
    });

    const wavSamples = downsample(merged, sourceRate, 16000);
    const wavBlob = encodeWav(wavSamples, 16000);

    cleanupGnaniRecording();

    if (!wavSamples.length) {
      showToast("No audio was recorded. Please try again.");
      return;
    }
    if (wavBlob.size > 10 * 1024 * 1024) {
      showToast("Recording exceeds the supported 10 MB limit.");
      return;
    }

    const formData = new FormData();
    formData.append("audio_file", wavBlob, "schemesathi-recording.wav");
    formData.append("language_code", languageSelect.value);
    formData.append("format", "transcribe");

    setVoiceState(false, "Transcribing...");
    voiceButton.disabled = true;

    try {
      const result = await api.request("/voice/transcribe", {
        method: "POST",
        body: formData
      });

      heroPrompt.value = result.transcript;
      heroPrompt.dispatchEvent(new Event("input"));
      heroPrompt.focus();

      showToast("Speech transcribed. Review your question and press Send.");

    } catch (error) {
      console.error("Gnani Prisma error:", error);
      showToast(error.message || "Could not transcribe your audio.");
    } finally {
      voiceButton.disabled = false;
      setVoiceState(false, "Speak");
    }
  }

  voiceButton.addEventListener("click", () => {
    if (recording) {
      stopGnaniRecording();
    } else {
      startGnaniRecording();
    }
  });

  languageSelect.addEventListener("change", () => {
    try {
      sessionStorage.setItem("schemesathi_selected_language", languageSelect.value);
    } catch (error) {
      showToast("Language selection will apply only on this page.");
    }
    updateLanguageButton();
  });
  languageButton?.addEventListener("click", () => {
    document.getElementById("assistant").scrollIntoView({ behavior: "smooth", block: "center" });
    languageSelect.focus();
  });

  loadVoiceLanguages();
  loadHomeCategories();
  loadHomeSavedServices();

  window.schemesathiSpeak = async function (text, languageCode) {
    const audioBlob = await api.request("/voice/synthesize", {
      method: "POST",
      responseType: "blob",
      body: JSON.stringify({
        text,
        language_code: languageCode || languageSelect.value,
        speed: 1.0
      })
    });
    if (!audioBlob.size || audioBlob.type !== "audio/wav") {
      throw new Error("Gnani Timbre returned an unsupported audio file.");
    }
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);

    audio.addEventListener("ended", () => URL.revokeObjectURL(audioUrl), {
      once: true
    });

    await audio.play();
  };
})();
