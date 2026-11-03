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
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;

    voiceButton.addEventListener("click", () => {
      recognition.lang = languageSelect.value;
      try {
        recognition.start();
        voiceButton.classList.add("listening");
        voiceLabel.textContent = "Listening...";
      } catch {
        notify("Voice recognition is already active.");
      }
    });

    recognition.onresult = event => {
      input.value = Array.from(event.results)
        .map(result => result[0].transcript)
        .join("");
      input.dispatchEvent(new Event("input"));
    };

    recognition.onend = () => {
      voiceButton.classList.remove("listening");
      voiceLabel.textContent = "Speak";
    };

    recognition.onerror = () => {
      voiceButton.classList.remove("listening");
      voiceLabel.textContent = "Speak";
      notify("Voice input could not start. Please check microphone permission.");
    };
  } else {
    voiceButton.addEventListener("click", () => {
      notify("Voice input is not supported in this browser. Try Chrome or Edge.");
    });
  }

  // Mobile sidebar
  const sidebar = document.getElementById("chatSidebar");
  const overlay = document.getElementById("sidebarOverlay");

  function closeSidebar() {
    sidebar.classList.remove("open");
    overlay.classList.remove("show");
  }

  document.getElementById("sidebarToggle").addEventListener("click", () => {
    sidebar.classList.toggle("open");
    overlay.classList.toggle("show");
  });

  overlay.addEventListener("click", closeSidebar);

  // Receive prompt from the homepage
  const initialPrompt = sessionStorage.getItem("schemesathi_initial_prompt");
  if (initialPrompt) {
    sessionStorage.removeItem("schemesathi_initial_prompt");
    sendMessage(initialPrompt);
  }
})();
