(() => {
  const input = document.getElementById("messageInput");
  const form = document.getElementById("messageForm");
  const welcome = document.getElementById("welcomePanel");
  const conversation = document.getElementById("conversationArea");
  const toast = document.getElementById("assistantToast");
  const historyList = document.getElementById("historyList");
  const voiceButton = document.getElementById("voiceInputButton");
  const voiceLabel = document.getElementById("voiceLabel");
  const voiceStatus = document.getElementById("voiceStatus");
  const languageSelect = document.getElementById("chatLanguage");
  const api = window.SchemeSathiAPI;
  const maxRecordingSeconds = 30;
  const voiceSupportedLanguages = new Set([
    "bn", "en", "gu", "hi", "kn", "ml", "mr", "pa", "ta", "te"
  ]);

  let toastTimer;
  let microphoneStream = null;
  let audioContext = null;
  let processor = null;
  let mutedOutput = null;
  let audioChunks = [];
  let recording = false;
  let recordingStartedAt = 0;
  let recordingTimeout = null;
  let activeAudio = null;
  let activeAudioUrl = null;
  let guestSessionToken = null;
  let conversationId = null;
  let activeSchemeId = "";
  let guidanceStage = "";
  let requestPending = false;
  let transcribeInFlight = false;
  let conversationPinned = false;
  let detectedLanguageCode = "";
  let lastRequest = null;

  function t(text) {
    return window.GovNexusI18n?.t?.(text) || text;
  }

  function notify(message) {
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 3500);
  }

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;",
      '"': "&quot;", "'": "&#039;"
    })[char]);
  }

  function showConversation() {
    welcome.style.display = "none";
    conversation.classList.add("active");
  }

  function setVoiceState(active, label) {
    voiceButton.classList.toggle("listening", active);
    voiceLabel.textContent = label;
    voiceButton.setAttribute("aria-pressed", String(active));
  }

  function setVoiceStatus(message) {
    voiceStatus.textContent = message;
  }

  function updateVoiceAvailability() {
    const supported = voiceSupportedLanguages.has(
      languageSelect.value.split("-")[0].toLowerCase()
    );
    voiceButton.disabled = !supported;
    if (!supported) {
      setVoiceStatus("Voice input is currently available in 10 languages.");
    }
    return supported;
  }

  function renderCitations(container, citations) {
    if (!Array.isArray(citations) || !citations.length) return;
    const list = document.createElement("ul");
    list.className = "citation-list";
    citations.forEach(citation => {
      const item = document.createElement("li");
      const link = document.createElement("a");
      let url;
      try {
        url = new URL(citation.url);
      } catch {
        return;
      }
      if (url.protocol !== "https:") return;
      link.href = url.href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = `${citation.publisher} (${citation.marker})`;
      item.appendChild(link);
      if (citation.page_number) {
        const page = document.createElement("span");
        page.textContent = ` · page ${citation.page_number}`;
        item.appendChild(page);
      }
      if (citation.section) {
        const section = document.createElement("span");
        section.textContent = ` · ${citation.section}`;
        item.appendChild(section);
      }
      list.appendChild(item);
    });
    if (list.childElementCount) container.appendChild(list);
  }

  async function stopPlayback() {
    if (activeAudio) {
      activeAudio.pause();
      activeAudio.currentTime = 0;
      activeAudio = null;
    }
    if (activeAudioUrl) {
      URL.revokeObjectURL(activeAudioUrl);
      activeAudioUrl = null;
    }
  }

  async function speakAnswer(text, languageCode, audio, status) {
    await stopPlayback();
    status.textContent = t("Preparing audio…");
    try {
      const audioBlob = await api.request("/voice/synthesize", {
        method: "POST",
        responseType: "blob",
        body: JSON.stringify({
          text,
          language_code: languageCode,
          speed: 1.0
        })
      });
      if (!audioBlob.size || audioBlob.type !== "audio/wav") {
        throw new Error("The speech service returned an unsupported audio file.");
      }
      activeAudioUrl = URL.createObjectURL(audioBlob);
      activeAudio = new Audio(activeAudioUrl);
      activeAudio.addEventListener("ended", () => {
        status.textContent = t("Audio finished.");
        stopPlayback();
      }, { once: true });
      await activeAudio.play();
      status.textContent = t("Playing answer.");
      audio.disabled = false;
    } catch (error) {
      status.textContent = t("Speech could not be played. The written answer is still shown.");
      notify(error.message || t("Speech could not be played. The written answer is still shown."));
    }
  }

  function renderMessage(message, options = {}) {
    const isUser = message.role === "user";
    const messageText = message.text ?? message.content ?? "";
    const wrapper = document.createElement("article");
    wrapper.className = `chat-message ${isUser ? "user" : "assistant"}`;
    const body = document.createElement("div");
    body.className = "message-body";
    const name = document.createElement("div");
    name.className = "message-name";
    name.textContent = isUser ? t("You") : "GovNexus AI";
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    if (isUser) bubble.textContent = messageText;
    else renderRichText(bubble, messageText);
    body.append(name, bubble);

    if (!isUser && options.citations?.length) {
      renderCitations(body, options.citations);
    }

    const actions = document.createElement("div");
    actions.className = "message-actions";
    const description = document.createElement("span");
    description.textContent = t(isUser
      ? "Your question"
      : options.historical
        ? options.grounded === false
          ? "Evidence unavailable"
          : options.grounded === true ? "Verified guidance" : "Conversation history"
        : options.grounded ? "Verified guidance" : "Evidence unavailable");
    actions.appendChild(description);

    if (!isUser) {
      const copyButton = document.createElement("button");
      copyButton.type = "button";
      copyButton.textContent = t("Copy response");
      copyButton.addEventListener("click", async () => {
        if (!navigator.clipboard?.writeText) {
          notify("Clipboard access is unavailable.");
          return;
        }
        try {
          await navigator.clipboard.writeText(messageText);
          notify("Response copied.");
        } catch (error) {
          notify("Clipboard access is unavailable.");
        }
      });
      actions.appendChild(copyButton);

      const audioStatus = document.createElement("span");
      audioStatus.className = "audio-status";
      const code = String(message.languageCode || languageSelect.value)
        .split("-")[0].toLowerCase();
      const spokenCode = voiceSupportedLanguages.has(code) ? `${code}-IN` : "";
      const listenButton = document.createElement("button");
      listenButton.type = "button";
      listenButton.textContent = t("Listen with Prism");
      const speak = () => {
        if (!spokenCode) {
          audioStatus.textContent = t("Prism speech is not available for this language. You can still read the text answer.");
          return;
        }
        speakAnswer(messageText, spokenCode, listenButton, audioStatus);
      };
      listenButton.addEventListener("click", speak);
      const replayButton = document.createElement("button");
      replayButton.type = "button";
      replayButton.textContent = t("Replay");
      replayButton.addEventListener("click", speak);
      const stopButton = document.createElement("button");
      stopButton.type = "button";
      stopButton.textContent = t("Stop");
      stopButton.addEventListener("click", () => {
        stopPlayback();
        audioStatus.textContent = t("Playback stopped.");
      });
      actions.append(listenButton, replayButton, stopButton, audioStatus);
      if (!spokenCode) {
        audioStatus.textContent = t("Prism speech is not available for this language. You can still read the text answer.");
      } else if (options.autoSpeak || options.readAloud) {
        speak();
      }
    }

    body.appendChild(actions);
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = isUser ? "◎" : "✳";
    wrapper.append(avatar, body);
    if (!isUser && options.scheme?.id) {
      const schemeId = encodeURIComponent(options.scheme.id);
      const links = document.createElement("div");
      links.className = "scheme-actions";
      const schemeLinks = [
        ["View scheme details", `service-detail.html?id=${schemeId}`],
        ["Check eligibility", `service-detail.html?id=${schemeId}#eligibility`],
        ["Review document requirements", `service-detail.html?id=${schemeId}#documents`],
        ["Help me apply", `apply.html?scheme=${schemeId}`],
      ];
      if (options.scheme.official_url && String(options.scheme.official_url).startsWith("https://")) {
        schemeLinks.push(["Open the official portal", options.scheme.official_url]);
      }
      schemeLinks.forEach(([label, href]) => {
        const anchor = document.createElement("a");
        anchor.href = href;
        anchor.textContent = t(label);
        if (String(href).startsWith("https://")) {
          anchor.target = "_blank";
          anchor.rel = "noopener noreferrer";
        }
        links.appendChild(anchor);
      });
      actions.appendChild(links);
      ["Am I eligible?", "What documents do I need?", "How do I apply?"].forEach(prompt => {
        const suggestion = document.createElement("button");
        suggestion.type = "button";
        suggestion.textContent = prompt;
        suggestion.addEventListener("click", () => sendMessage(prompt));
        actions.appendChild(suggestion);
      });
      if (options.scheme.verification_label) {
        const status = document.createElement("p");
        status.className = "verification-note";
        status.textContent = options.scheme.verification_label;
        body.appendChild(status);
      }
    }
    conversation.appendChild(wrapper);
    window.GovNexusI18n?.apply();
  }

  function renderRichText(container, text) {
    const lines = String(text || "").split(/\n/);
    let list = null;
    const flush = () => {
      if (list) container.appendChild(list);
      list = null;
    };
    lines.forEach(line => {
      const heading = line.match(/^(#{1,3})\s+(.+)$/);
      const bullet = line.match(/^\s*[-*]\s+(.+)$/);
      const numbered = line.match(/^\s*(\d+)[.)]\s+(.+)$/);
      if (heading) {
        flush();
        const node = document.createElement("h3");
        node.textContent = heading[2];
        container.appendChild(node);
      } else if (bullet || numbered) {
        const ordered = Boolean(numbered);
        if (!list || list.dataset.ordered !== String(ordered)) {
          flush();
          list = document.createElement(ordered ? "ol" : "ul");
          list.dataset.ordered = String(ordered);
        }
        const item = document.createElement("li");
        item.textContent = ordered ? numbered[2] : bullet[1];
        list.appendChild(item);
      } else if (!line.trim()) {
        flush();
      } else {
        flush();
        const paragraph = document.createElement("p");
        paragraph.textContent = line;
        container.appendChild(paragraph);
      }
    });
    flush();
  }

  function renderHistoryEmpty(message) {
    historyList.replaceChildren();
    const empty = document.createElement("div");
    empty.className = "history-empty";
    empty.textContent = message;
    historyList.appendChild(empty);
  }

  function addHistoryItem(id, title) {
    historyList.querySelector(".history-empty")?.remove();
    const existing = [...historyList.querySelectorAll("[data-conversation-id]")]
      .find(item => item.dataset.conversationId === id);
    if (existing) {
      existing.textContent = `◦  ${title}`;
      historyList.prepend(existing);
      return;
    }
    const item = document.createElement("button");
    item.className = "history-item";
    item.type = "button";
    item.dataset.conversationId = id;
    item.textContent = "◦  " + (title.length > 32 ? `${title.slice(0, 32)}…` : title);
    item.title = title;
    item.addEventListener("click", () => openConversation(id));
    historyList.prepend(item);
  }

  async function loadConversationHistory() {
    if (!await api.isAuthenticated("citizen")) {
      renderHistoryEmpty("Sign in to view saved conversation history.");
      return;
    }
    try {
      const conversations = [];
      let page = 1;
      let pages = 1;
      do {
        const result = await api.get(
          `/users/me/conversations?status=all&page=${page}&limit=100`,
          "citizen"
        );
        conversations.push(...(Array.isArray(result.items) ? result.items : []));
        pages = Number(result.pagination?.pages) || 1;
        page += 1;
      } while (page <= pages);

      historyList.replaceChildren();
      if (!conversations.length) {
        renderHistoryEmpty("No saved conversations yet.");
        return;
      }
      conversations.forEach(item => {
        const title = item.title || `Conversation ${item.id.slice(0, 8)}`;
        const button = document.createElement("button");
        button.className = "history-item";
        button.type = "button";
        button.dataset.conversationId = item.id;
        button.textContent = "◦  " + (title.length > 32 ? `${title.slice(0, 32)}…` : title);
        button.title = `${title}${item.status === "archived" ? " · archived" : ""}`;
        button.disabled = item.status === "archived";
        button.addEventListener("click", () => openConversation(item.id));
        historyList.appendChild(button);
      });
    } catch (error) {
      renderHistoryEmpty(`Conversation history is unavailable: ${error.message}`);
    }
  }

  async function openConversation(id) {
    if (!await api.isAuthenticated("citizen")) return;
    try {
      const pages = [];
      let page = 1;
      let totalPages = 1;
      do {
        const result = await api.get(
          `/users/me/conversations/${encodeURIComponent(id)}?page=${page}&limit=200`,
          "citizen"
        );
        pages.push(...(Array.isArray(result.messages) ? result.messages : []));
        totalPages = Number(result.pagination?.pages) || 1;
        page += 1;
      } while (page <= totalPages);

      conversationId = id;
      guestSessionToken = null;
      conversation.replaceChildren();
      showConversation();
      pages.forEach(item => renderMessage({
        role: item.role,
        content: item.content,
        languageCode: item.language_code
      }, {
        historical: true,
        grounded: item.grounded,
        citations: item.citations
      }));
      conversation.scrollTop = conversation.scrollHeight;
      notify("Conversation history loaded.");
    } catch (error) {
      notify(`Could not load conversation: ${error.message}`);
    }
  }

  function addTypingIndicator() {
    const typing = document.createElement("article");
    typing.className = "chat-message assistant";
    typing.innerHTML = `
      <div class="message-avatar">✳</div>
      <div class="message-body">
        <div class="message-name">GovNexus AI</div>
        <div class="message-bubble typing-dots"><i></i><i></i><i></i></div>
      </div>
    `;
    conversation.appendChild(typing);
    conversation.scrollTop = conversation.scrollHeight;
    return typing;
  }

  async function sendMessage(text, { fromVoice = false } = {}) {
    const cleanText = text.trim();
    if (!cleanText || requestPending) return;
    requestPending = true;
    form.querySelector(".submit-message").disabled = true;
    showConversation();
    renderMessage({ role: "user", text: cleanText });
    const typing = addTypingIndicator();
    lastRequest = { text: cleanText, fromVoice };
    setVoiceStatus(t("Finding verified information…"));

    try {
      const payload = {
        message: cleanText,
        language_code: languageSelect.value
      };
      if (detectedLanguageCode) payload.detected_language_code = detectedLanguageCode;
      const citizenSession = await api.isAuthenticated("citizen");
      if (!citizenSession && guestSessionToken) payload.guest_session_token = guestSessionToken;
      if (conversationId) payload.conversation_id = conversationId;
      if (activeSchemeId) payload.scheme_id = activeSchemeId;
      if (guidanceStage) payload.guidance_stage = guidanceStage;
      const result = await api.post("/chat/message", payload, citizenSession ? "citizen" : null);
      guestSessionToken = result.guest_session_token || guestSessionToken;
      conversationId = result.conversation_id || conversationId;
      if (result.active_scheme?.id) {
        activeSchemeId = result.active_scheme.id;
        try { sessionStorage.setItem("govnexus_active_scheme", activeSchemeId); } catch { /* private mode */ }
      }
      if (citizenSession && conversationId) addHistoryItem(conversationId, cleanText);
      typing.remove();
      renderMessage(
        {
          role: "assistant",
          text: result.answer,
          languageCode: result.response_language || payload.language_code
        },
        {
          citations: result.citations,
          grounded: result.grounded,
          scheme: result.active_scheme,
          autoSpeak: fromVoice,
          readAloud: api.getAccessibilityPreferences().read_aloud
        }
      );
      setVoiceStatus(t(
        result.evidence_language_fallback
          ? "Verified source text is available in another language."
          : "Ask in your preferred language"
      ));
      detectedLanguageCode = "";
      input.value = "";
      input.style.height = "auto";
      conversation.scrollIntoView({ behavior: "smooth", block: "end" });
    } catch (error) {
      typing.remove();
      input.value = cleanText;
      const failed = lastRequest;
      renderMessage({
        role: "assistant",
        text: error.message || "The assistant could not answer right now."
      }, { grounded: false });
      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "retry-button";
      retry.textContent = t("Retry");
      retry.addEventListener("click", () => {
        retry.remove();
        if (failed) sendMessage(failed.text, { fromVoice: failed.fromVoice });
      });
      conversation.lastElementChild?.querySelector(".message-actions")?.appendChild(retry);
      setVoiceStatus(t("Ask in your preferred language"));
    } finally {
      requestPending = false;
      form.querySelector(".submit-message").disabled = false;
      input.focus();
    }
  }

  function wavBlob(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);
    const write = (offset, value) => {
      for (let index = 0; index < value.length; index += 1) {
        view.setUint8(offset + index, value.charCodeAt(index));
      }
    };
    write(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    write(8, "WAVE");
    write(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    write(36, "data");
    view.setUint32(40, samples.length * 2, true);
    let offset = 44;
    for (let index = 0; index < samples.length; index += 1, offset += 2) {
      const sample = Math.max(-1, Math.min(1, samples[index]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    }
    return new Blob([buffer], { type: "audio/wav" });
  }

  function downsample(samples, inputRate, outputRate) {
    if (inputRate === outputRate) return new Float32Array(samples);
    const ratio = inputRate / outputRate;
    const output = new Float32Array(Math.floor(samples.length / ratio));
    for (let index = 0; index < output.length; index += 1) {
      const start = Math.floor(index * ratio);
      const end = Math.min(Math.floor((index + 1) * ratio), samples.length);
      let total = 0;
      for (let sourceIndex = start; sourceIndex < end; sourceIndex += 1) {
        total += samples[sourceIndex];
      }
      output[index] = total / Math.max(1, end - start);
    }
    return output;
  }

  function cleanupRecording() {
    clearTimeout(recordingTimeout);
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
    microphoneStream?.getTracks().forEach(track => track.stop());
    microphoneStream = null;
    if (audioContext) {
      audioContext.close().catch(error =>
        console.error("Could not close the audio context.", error)
      );
      audioContext = null;
    }
    recording = false;
    setVoiceState(false, t("Speak"));
  }

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia ||
        !(window.AudioContext || window.webkitAudioContext)) {
      notify("This browser does not support microphone recording.");
      return;
    }
    if (!window.isSecureContext && location.hostname !== "localhost" &&
        location.hostname !== "127.0.0.1") {
      notify("Microphone access requires HTTPS or localhost.");
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
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      audioContext = new AudioContextClass();
      if (audioContext.state === "suspended") await audioContext.resume();
      const source = audioContext.createMediaStreamSource(microphoneStream);
      processor = audioContext.createScriptProcessor(4096, 1, 1);
      mutedOutput = audioContext.createGain();
      mutedOutput.gain.value = 0;
      audioChunks = [];
      recording = true;
      recordingStartedAt = Date.now();
      processor.onaudioprocess = event => {
        if (recording) {
          audioChunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
        }
      };
      source.connect(processor);
      processor.connect(mutedOutput);
      mutedOutput.connect(audioContext.destination);
      setVoiceState(true, t("Stop"));
      setVoiceStatus(t("Recording · up to 30 seconds"));
      recordingTimeout = setTimeout(stopRecording, maxRecordingSeconds * 1000);
    } catch (error) {
      cleanupRecording();
      notify(
        error.name === "NotAllowedError"
          ? "Microphone permission was denied."
          : "Could not start microphone recording."
      );
      setVoiceStatus("Ask in your preferred language");
    }
  }

  async function stopRecording() {
    if (!recording || !audioContext) return;
    recording = false;
    const elapsedSeconds = (Date.now() - recordingStartedAt) / 1000;
    const sampleRate = audioContext.sampleRate;
    const length = audioChunks.reduce((total, chunk) => total + chunk.length, 0);
    const samples = new Float32Array(length);
    let offset = 0;
    audioChunks.forEach(chunk => {
      samples.set(chunk, offset);
      offset += chunk.length;
    });
    const normalized = downsample(samples, sampleRate, 16000);
    const blob = wavBlob(normalized, 16000);
    cleanupRecording();
    if (elapsedSeconds < 0.1 || !normalized.length) {
      notify("No speech was recorded. Please try again.");
      setVoiceStatus("Ask in your preferred language");
      return;
    }
    if (elapsedSeconds > maxRecordingSeconds + 0.5 || blob.size > 10 * 1024 * 1024) {
      notify("Recording exceeded the supported 30-second limit.");
      setVoiceStatus("Ask in your preferred language");
      return;
    }

    transcribeInFlight = true;
    voiceButton.disabled = true;
    setVoiceStatus(t("Transcribing your question…"));
    try {
      const formData = new FormData();
      formData.append("audio_file", blob, "schemesathi-recording.wav");
      formData.append(
        "language_code",
        conversationPinned && languageSelect.value ? languageSelect.value : "indic-auto"
      );
      formData.append("format", "transcribe");
      const result = await api.request("/voice/transcribe", {
        method: "POST",
        body: formData
      });
      const transcript = String(result.transcript || "").trim();
      if (!transcript) throw new Error("No speech was recognized.");
      input.value = transcript;
      input.dispatchEvent(new Event("input"));
      setVoiceStatus(
        result.detected_language_code
          ? `Recognized · ${result.detected_language_code}`
          : "Transcription complete"
      );
      conversationPinned = true;
      if (result.detected_language_code) {
        const detected = String(result.detected_language_code);
        detectedLanguageCode = detected;
        const optionValue = detected.includes("-") ? detected : `${detected}-IN`;
        if ([...languageSelect.options].some(option => option.value === optionValue)) {
          languageSelect.value = optionValue;
        }
      }
      setVoiceStatus(t("Review the transcript, then send."));
      input.focus();
    } catch (error) {
      notify(error.message || t("Transcription failed. You can type your question or try again."));
      setVoiceStatus(t("Transcription failed. You can type your question or try again."));
    } finally {
      transcribeInFlight = false;
      voiceButton.disabled = false;
      if (!requestPending && !recording && !input.value) {
        setTimeout(() => setVoiceStatus(t("Ask in your preferred language")), 5000);
      }
    }
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    if (recording || transcribeInFlight || requestPending) return;
    sendMessage(input.value, { fromVoice: Boolean(detectedLanguageCode) });
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 130) + "px";
  });
  document.querySelectorAll(".prompt-card").forEach(button => {
    button.addEventListener("click", () => sendMessage(button.dataset.prompt || ""));
  });
  voiceButton.addEventListener("click", () => {
    if (transcribeInFlight || requestPending) return;
    if (recording) stopRecording();
    else startRecording();
  });
  languageSelect.addEventListener("change", () => {
    conversationPinned = true;
    const selectedCode = languageSelect.value.split("-")[0].toLowerCase();
    window.GovNexusI18n?.persist?.(selectedCode);
    if (updateVoiceAvailability()) {
      setVoiceStatus(t("Ask in your preferred language"));
    }
    api.isAuthenticated("citizen").then(authenticated => {
      if (!authenticated) return;
      return api.patch("/users/me", { preferred_language_code: selectedCode }, "citizen")
        .then(profile => api.cachePreferredLanguage(profile.preferred_language_code));
    }).catch(error => notify(`Language preference could not be saved: ${error.message}`));
    notify(`Language set to ${languageSelect.options[languageSelect.selectedIndex].text}.`);
  });
  document.getElementById("newChatButton").addEventListener("click", async () => {
    const newChatButton = document.getElementById("newChatButton");
    newChatButton.disabled = true;
    try {
      if (await api.isAuthenticated("citizen")) {
        const result = await api.post(
          "/users/me/conversations",
          { language_code: languageSelect.value.split("-")[0] },
          "citizen"
        );
        conversationId = result.id;
        if (conversationId) addHistoryItem(conversationId, result.title || "New conversation");
      } else {
        conversationId = null;
        guestSessionToken = null;
      }
      activeSchemeId = "";
      guidanceStage = "";
      try { sessionStorage.removeItem("govnexus_active_scheme"); } catch { /* private mode */ }
      await stopPlayback();
      if (recording) cleanupRecording();
      conversation.replaceChildren();
      conversation.classList.remove("active");
      welcome.style.display = "";
      input.value = "";
      input.focus();
      setVoiceStatus(t("Ask in your preferred language"));
      notify(t("Started a new conversation."));
    } catch (error) {
      notify(`Could not start a new conversation: ${error.message}`);
    } finally {
      newChatButton.disabled = false;
    }
  });
  document.getElementById("clearChatButton")?.addEventListener("click", async () => {
    if (!window.confirm(t("Clear this conversation on this screen?"))) return;
    await stopPlayback();
    if (recording) cleanupRecording();
    conversation.replaceChildren();
    conversation.classList.remove("active");
    welcome.style.display = "";
    input.value = "";
    activeSchemeId = "";
    guidanceStage = "";
    try { sessionStorage.removeItem("govnexus_active_scheme"); } catch { /* private mode */ }
    input.focus();
    setVoiceStatus(t("Ask in your preferred language"));
  });
  document.addEventListener("govnexus:language", event => {
    if (conversationPinned) return;
    const requested = `${event.detail?.language || "en"}-IN`;
    if ([...languageSelect.options].some(option => option.value === requested) && languageSelect.value !== requested) {
      languageSelect.value = requested;
      updateVoiceAvailability();
    }
  });
  document.getElementById("sidebarToggle")?.addEventListener("click", () => {
    document.getElementById("chatSidebar").classList.toggle("open");
    document.getElementById("sidebarOverlay").classList.toggle("show");
  });
  document.getElementById("sidebarOverlay")?.addEventListener("click", () => {
    document.getElementById("chatSidebar").classList.remove("open");
    document.getElementById("sidebarOverlay").classList.remove("show");
  });

  async function loadConversationLanguages() {
    const result = await api.get("/languages?active_only=true");
    const items = Array.isArray(result.items) ? result.items : [];
    languageSelect.replaceChildren();
    items.forEach(item => {
      const code = `${String(item.code).split("-")[0].toLowerCase()}-IN`;
      languageSelect.appendChild(new Option(
        item.native_name ? `${item.native_name} — ${item.english_name}` : item.english_name,
        code
      ));
    });
    if (!items.length) throw new Error("No active conversation languages are configured.");
    languageSelect.value = items.some(item => item.code === "en")
      ? "en-IN"
      : `${items[0].code}-IN`;
    updateVoiceAvailability();
  }

  loadConversationLanguages().then(() => api.isAuthenticated("citizen")).then(authenticated => {
    const stored = window.GovNexusI18n?.language?.() || "en";
    const storedCode = `${stored}-IN`;
    if ([...languageSelect.options].some(option => option.value === storedCode)) {
      languageSelect.value = storedCode;
    }
    updateVoiceAvailability();
    if (authenticated) {
      return api.get("/users/me", "citizen").then(profile => {
      const requested = `${profile.preferred_language_code || stored}-IN`;
      if ([...languageSelect.options].some(option => option.value === requested)) {
        languageSelect.value = requested;
        window.GovNexusI18n?.persist?.(profile.preferred_language_code || stored);
      }
      updateVoiceAvailability();
      return loadConversationHistory();
      });
    }
    renderHistoryEmpty("Sign in to view saved conversation history.");
    try {
      const selected = sessionStorage.getItem("schemesathi_selected_language");
      if ([...languageSelect.options].some(option => option.value === selected)) {
        languageSelect.value = selected;
      }
    } catch (error) {
      notify("Could not read the selected language from this browser session.");
    }
  }).catch(error => notify(`Could not check your sign-in session: ${error.message}`));

  const pageQuery = new URLSearchParams(window.location.search);
  const queryScheme = pageQuery.get("scheme") || "";
  const queryStage = pageQuery.get("stage") || "";
  if (/^[A-Za-z0-9_-]{1,80}$/.test(queryScheme)) activeSchemeId = queryScheme;
  if (/^[A-Za-z0-9_-]{1,40}$/.test(queryStage)) guidanceStage = queryStage;
  if (!activeSchemeId) {
    try { activeSchemeId = sessionStorage.getItem("govnexus_active_scheme") || ""; } catch { activeSchemeId = ""; }
  }

  let initialPrompt = "";
  try {
    initialPrompt = sessionStorage.getItem("schemesathi_initial_prompt") || "";
    sessionStorage.removeItem("schemesathi_initial_prompt");
  } catch (error) {
    notify("Could not read the initial assistant prompt from this browser session.");
  }
  if (initialPrompt) {
    input.value = initialPrompt;
    sendMessage(initialPrompt);
  }
})();
