(() => {
  const input = document.getElementById("messageInput");
  const form = document.getElementById("messageForm");
  const welcome = document.getElementById("welcomePanel");
  const conversation = document.getElementById("conversationArea");
  const toast = document.getElementById("assistantToast");
  const historyList = document.getElementById("historyList");
  const voiceButton = document.getElementById("voiceInputButton");
  const voiceLabel = document.getElementById("voiceLabel");
  const languageSelect = document.getElementById("chatLanguage");

  let messages = [];
  let toastTimer;

  function notify(message) {
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 3000);
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

  function renderMessage(message) {
    const isUser = message.role === "user";
    const wrapper = document.createElement("article");
    wrapper.className = `chat-message ${isUser ? "user" : "assistant"}`;

    const safeText = escapeHTML(message.text).replace(/\n/g, "<br>");

    wrapper.innerHTML = `
      <div class="message-avatar">${isUser ? "◎" : "✳"}</div>
      <div class="message-body">
        <div class="message-name">${isUser ? "You" : "SchemeSathi AI"}</div>
        <div class="message-bubble">${safeText}</div>
        ${!isUser ? `
          <div class="demo-response">
            <strong>Demo preview — not verified government guidance</strong>
            The chat interface is ready, but the live AI and verified knowledge service have not been connected yet. No eligibility, fee, document or application claim is being made here.
          </div>
        ` : ""}
        <div class="message-actions">
          <span>${isUser ? "Your question" : "Demo response"}</span>
          ${!isUser ? '<button type="button" class="copy-message">Copy response</button>' : ""}
        </div>
      </div>
    `;

    const copyButton = wrapper.querySelector(".copy-message");
    copyButton?.addEventListener("click", () => {
      navigator.clipboard?.writeText(message.text)
        .then(() => notify("Response copied."))
        .catch(() => notify("Clipboard access is unavailable."));
    });

    conversation.appendChild(wrapper);
  }

  function updateHistory(text) {
    const empty = historyList.querySelector(".history-empty");
    empty?.remove();

    const item = document.createElement("button");
    item.className = "history-item";
    item.type = "button";
    item.textContent = "◦  " + (text.length > 32 ? text.slice(0, 32) + "…" : text);
    item.title = text;
    item.addEventListener("click", () => {
      notify("Conversation history will be saved when account storage is connected.");
    });

    historyList.prepend(item);
  }

  function sendMessage(text) {
    const cleanText = text.trim();
    if (!cleanText) return;

    showConversation();
    messages.push({ role: "user", text: cleanText });
    renderMessage(messages[messages.length - 1]);
    updateHistory(cleanText);

    input.value = "";
    input.style.height = "auto";

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

    // This is deliberately a transparent UI preview, not a simulated AI answer.
    setTimeout(() => {
      typing.remove();
      const response = {
        role: "assistant",
        text: "Thanks for sharing your question. SchemeSathi is ready to guide you through government services. The live AI knowledge and retrieval API is the next integration step."
      };
      messages.push(response);
      renderMessage(response);
      conversation.scrollIntoView({ behavior: "smooth", block: "end" });
    }, 650);
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

  document.getElementById("newChatButton").addEventListener("click", () => {
    messages = [];
    conversation.innerHTML = "";
    conversation.classList.remove("active");
    welcome.style.display = "";
    input.value = "";
    input.focus();
    notify("Started a new conversation.");
  });

  languageSelect.addEventListener("change", () => {
    const selected = languageSelect.options[languageSelect.selectedIndex].text;
    notify(`Selected ${selected}. Live multilingual responses will be connected in a later stage.`);
  });

  // Voice input
    // Gnani Prisma voice input
  const API_BASE = "http://127.0.0.1:8000/api/v1";

  let microphoneStream = null;
  let audioContext = null;
  let processor = null;
  let audioChunks = [];
  let recording = false;
  let recordingTimeout = null;

  function setVoiceState(active, label) {
    voiceButton.classList.toggle("listening", active);
    voiceLabel.textContent = label;
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
      const source = audioContext.createMediaStreamSource(microphoneStream);

      processor = audioContext.createScriptProcessor(4096, 1, 1);
      audioChunks = [];
      recording = true;

      processor.onaudioprocess = event => {
        if (!recording) return;
        audioChunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setVoiceState(true, "Stop recording");
      notify("Listening. Speak your question clearly.");

      recordingTimeout = setTimeout(() => {
        if (recording) stopGnaniRecording();
      }, 55000);

    } catch (error) {
      console.error("Microphone error:", error);
      cleanupGnaniRecording();
      setVoiceState(false, "Speak");
      notify("Microphone access failed. Check browser permissions.");
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

    if (microphoneStream) {
      microphoneStream.getTracks().forEach(track => track.stop());
      microphoneStream = null;
    }

    if (audioContext) {
      audioContext.close().catch(() => {});
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
      notify("No audio was recorded. Please try again.");
      return;
    }

    const formData = new FormData();
    formData.append("audio_file", wavBlob, "schemesathi-recording.wav");
    formData.append("language_code", languageSelect.value);
    formData.append("audio_format", "transcribe");

    setVoiceState(false, "Transcribing...");
    voiceButton.disabled = true;

    try {
      const response = await fetch(`${API_BASE}/voice/transcribe`, {
        method: "POST",
        body: formData
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Prisma transcription failed.");
      }

      input.value = result.transcript;
      input.dispatchEvent(new Event("input"));
      input.focus();

      notify("Speech transcribed. Review your question and press Send.");

    } catch (error) {
      console.error("Gnani Prisma error:", error);
      notify(error.message || "Could not transcribe your audio.");
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

  // Optional helper for speaking a real assistant response with Gnani Timbre.
  // Call this only after the live assistant API returns its answer.
  window.schemesathiSpeak = async function (text, languageCode) {
    const response = await fetch(`${API_BASE}/voice/synthesize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        language_code: languageCode || languageSelect.value,
        speed: 1.0
      })
    });

    if (!response.ok) {
      let detail = "Gnani Timbre could not generate speech.";
      try {
        const error = await response.json();
        detail = error.detail || detail;
      } catch (_) {}
      throw new Error(detail);
    }

    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);

    audio.addEventListener("ended", () => URL.revokeObjectURL(audioUrl), {
      once: true
    });

    await audio.play();
  };