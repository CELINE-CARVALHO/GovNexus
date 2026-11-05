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
  const apiBase = window.SchemeSathiAPI?.baseUrl || "http://127.0.0.1:8000/api/v1";
  const maxRecordingSeconds = 30;

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
  let requestPending = false;

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
    status.textContent = "Preparing audio…";
    try {
      const response = await fetch(`${apiBase}/voice/synthesize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          language_code: languageCode,
          speed: 1.0
        })
      });
      if (!response.ok) {
        const result = await response.json().catch(() => ({}));
        throw new Error(result.detail || "Speech generation failed.");
      }
      const audioBlob = await response.blob();
      if (!audioBlob.size || audioBlob.type !== "audio/wav") {
        throw new Error("The speech service returned an unsupported audio file.");
      }
      activeAudioUrl = URL.createObjectURL(audioBlob);
      activeAudio = new Audio(activeAudioUrl);
      activeAudio.addEventListener("ended", () => {
        status.textContent = "Audio finished.";
        stopPlayback();
      }, { once: true });
      await activeAudio.play();
      status.textContent = "Playing answer.";
      audio.disabled = false;
    } catch (error) {
      status.textContent = "Audio is ready to retry.";
      notify(error.message || "Could not play the spoken answer.");
    }
  }

  function renderMessage(message, options = {}) {
    const isUser = message.role === "user";
    const wrapper = document.createElement("article");
    wrapper.className = `chat-message ${isUser ? "user" : "assistant"}`;
    const body = document.createElement("div");
    body.className = "message-body";
    const name = document.createElement("div");
    name.className = "message-name";
    name.textContent = isUser ? "You" : "SchemeSathi AI";
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = message.text;
    body.append(name, bubble);

    if (!isUser && options.citations?.length) {
      renderCitations(body, options.citations);
    }

    const actions = document.createElement("div");
    actions.className = "message-actions";
    const description = document.createElement("span");
    description.textContent = isUser ? "Your question" : "Verified guidance";
    actions.appendChild(description);

    if (!isUser) {
      const copyButton = document.createElement("button");
      copyButton.type = "button";
      copyButton.textContent = "Copy response";
      copyButton.addEventListener("click", () => {
        navigator.clipboard?.writeText(message.text)
          .then(() => notify("Response copied."))
          .catch(() => notify("Clipboard access is unavailable."));
      });
      actions.appendChild(copyButton);

      const audioStatus = document.createElement("span");
      audioStatus.className = "audio-status";
      const listenButton = document.createElement("button");
      listenButton.type = "button";
      listenButton.textContent = "Listen";
      listenButton.addEventListener("click", () => speakAnswer(
        message.text,
        message.languageCode || languageSelect.value,
        listenButton,
        audioStatus
      ));
      const replayButton = document.createElement("button");
      replayButton.type = "button";
      replayButton.textContent = "Replay";
      replayButton.addEventListener("click", () => speakAnswer(
        message.text,
        message.languageCode || languageSelect.value,
        replayButton,
        audioStatus
      ));
      const stopButton = document.createElement("button");
      stopButton.type = "button";
      stopButton.textContent = "Stop";
      stopButton.addEventListener("click", () => {
        stopPlayback();
        audioStatus.textContent = "Playback stopped.";
      });
      actions.append(listenButton, replayButton, stopButton, audioStatus);
      if (options.autoSpeak) {
        speakAnswer(
          message.text,
          message.languageCode || languageSelect.value,
          listenButton,
          audioStatus
        );
      }
    }

    body.appendChild(actions);
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = isUser ? "◎" : "✳";
    wrapper.append(avatar, body);
    conversation.appendChild(wrapper);
  }

  function updateHistory(text) {
    historyList.querySelector(".history-empty")?.remove();
    const item = document.createElement("button");
    item.className = "history-item";
    item.type = "button";
    item.textContent = "◦  " + (text.length > 32 ? text.slice(0, 32) + "…" : text);
    item.title = text;
    historyList.prepend(item);
  }

  function addTypingIndicator() {
    const typing = document.createElement("article");
    typing.className = "chat-message assistant";
    typing.innerHTML = `
      <div class="message-avatar">✳</div>
      <div class="message-body">
        <div class="message-name">SchemeSathi AI</div>
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
    updateHistory(cleanText);
    input.value = "";
    input.style.height = "auto";
    const typing = addTypingIndicator();
    setVoiceStatus("Finding verified information…");

    try {
      const payload = {
        message: cleanText,
        language_code: languageSelect.value
      };
      if (guestSessionToken) payload.guest_session_token = guestSessionToken;
      if (conversationId) payload.conversation_id = conversationId;
      const response = await fetch(`${apiBase}/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(result.detail || "The assistant could not answer right now.");
      }
      guestSessionToken = result.guest_session_token || guestSessionToken;
      conversationId = result.conversation_id || conversationId;
      typing.remove();
      renderMessage(
        {
          role: "assistant",
          text: result.answer,
          languageCode: payload.language_code
        },
        { citations: result.citations, autoSpeak: fromVoice }
      );
      setVoiceStatus(
        result.evidence_language_fallback
          ? "Verified source text is available in another language."
          : "Ask in your preferred language"
      );
      conversation.scrollIntoView({ behavior: "smooth", block: "end" });
    } catch (error) {
      typing.remove();
      notify(error.message || "The assistant could not answer right now.");
      setVoiceStatus("Ask in your preferred language");
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
      audioContext.close().catch(() => {});
      audioContext = null;
    }
    recording = false;
    setVoiceState(false, "Speak");
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
      setVoiceState(true, "Stop");
      setVoiceStatus("Recording · up to 30 seconds");
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

    voiceButton.disabled = true;
    setVoiceStatus("Transcribing your question…");
    try {
      const formData = new FormData();
      formData.append("audio_file", blob, "schemesathi-recording.wav");
      formData.append("language_code", languageSelect.value);
      formData.append("format", "transcribe");
      const response = await fetch(`${apiBase}/voice/transcribe`, {
        method: "POST",
        body: formData
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(result.detail || "Speech recognition failed.");
      }
      const transcript = String(result.transcript || "").trim();
      if (!transcript) throw new Error("No speech was recognized.");
      input.value = transcript;
      input.dispatchEvent(new Event("input"));
      setVoiceStatus(
        result.detected_language_code
          ? `Recognized · ${result.detected_language_code}`
          : "Transcription complete"
      );
      await sendMessage(transcript, { fromVoice: true });
    } catch (error) {
      notify(error.message || "Could not transcribe the recording.");
      setVoiceStatus("Ask in your preferred language");
    } finally {
      voiceButton.disabled = false;
      if (!requestPending && !recording) {
        setTimeout(() => setVoiceStatus("Ask in your preferred language"), 5000);
      }
    }
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    sendMessage(input.value);
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 130) + "px";
  });
  document.querySelectorAll(".prompt-card").forEach(button => {
    button.addEventListener("click", () => sendMessage(button.dataset.prompt || ""));
  });
  voiceButton.addEventListener("click", () => {
    if (recording) stopRecording();
    else startRecording();
  });
  languageSelect.addEventListener("change", () => {
    setVoiceStatus("Ask in your preferred language");
    notify(`Language set to ${languageSelect.options[languageSelect.selectedIndex].text}.`);
  });
  document.getElementById("newChatButton").addEventListener("click", () => {
    conversationId = null;
    guestSessionToken = null;
    stopPlayback();
    if (recording) cleanupRecording();
    conversation.innerHTML = "";
    conversation.classList.remove("active");
    welcome.style.display = "";
    input.value = "";
    input.focus();
    setVoiceStatus("Ask in your preferred language");
    notify("Started a new conversation.");
  });
  document.getElementById("sidebarToggle")?.addEventListener("click", () => {
    document.getElementById("chatSidebar").classList.toggle("open");
    document.getElementById("sidebarOverlay").classList.toggle("show");
  });
  document.getElementById("sidebarOverlay")?.addEventListener("click", () => {
    document.getElementById("chatSidebar").classList.remove("open");
    document.getElementById("sidebarOverlay").classList.remove("show");
  });

  const initialPrompt = sessionStorage.getItem("schemesathi_initial_prompt");
  if (initialPrompt) {
    sessionStorage.removeItem("schemesathi_initial_prompt");
    input.value = initialPrompt;
    sendMessage(initialPrompt);
  }
})();
