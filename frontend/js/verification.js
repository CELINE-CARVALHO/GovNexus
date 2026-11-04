const API_BASE = "http://127.0.0.1:8000/api/v1";

const state = {
    facts: [],
    selectedFact: null,
    selectedDecision: null
};

const $ = (selector) => document.querySelector(selector);

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

function notify(message, error = false) {
    const toast = $("#reviewToast");
    if (!toast) return;

    toast.textContent = message;
    toast.style.display = "block";
    toast.style.background = error ? "#b42318" : "#25223e";

    window.clearTimeout(notify.timer);
    notify.timer = window.setTimeout(() => {
        toast.style.display = "none";
    }, 3500);
}

async function api(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            ...(options.headers || {})
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.detail || `API error: ${response.status}`);
    }

    return data;
}

async function loadFacts() {
    const list = $("#factList");
    if (list) list.innerHTML = "<p>Loading facts from the backend...</p>";

    try {
        const result = await api("/verification/queue?status=open");

        state.facts = (result.items || []).map(item => ({
            ...item,
            status: "pending",
            category: item.fact_type || "uncategorised"
        }));

        renderFacts();
        updateStats();
    } catch (error) {
        if (list) list.innerHTML = "";
        notify(`Could not load verification queue: ${error.message}`, true);
    }
}

function getFilteredFacts() {
    const search = ($("#factSearch")?.value || "").trim().toLowerCase();
    const status = $("#statusFilter")?.value || "all";
    const category = $("#categoryFilter")?.value || "all";

    return state.facts.filter(fact => {
        const searchable = [
            fact.text,
            fact.fact_type,
            fact.language,
            JSON.stringify(fact.evidence || {})
        ].join(" ").toLowerCase();

        const matchesSearch = !search || searchable.includes(search);
        const matchesStatus = status === "all" || fact.status === status;
        const matchesCategory =
            category === "all" || fact.category === category;

        return matchesSearch && matchesStatus && matchesCategory;
    });
}

function renderFacts() {
    const list = $("#factList");
    const empty = $("#emptyFacts");
    if (!list) return;

    const facts = getFilteredFacts();

    $("#factResultCount").textContent = `${facts.length} RECORDS`;

    list.innerHTML = facts.map(fact => `
        <article class="fact-card">
            <div class="fact-card-header">
                <span class="fact-type">${escapeHTML(fact.fact_type)}</span>
                <span class="fact-status">${escapeHTML(fact.status)}</span>
            </div>

            <h3>${escapeHTML(fact.text || "No extracted fact text")}</h3>

            <p class="fact-description">
                Language: ${escapeHTML(fact.language || "en")}
            </p>

            <div class="fact-meta">
                <div>
                    <small>Fact ID</small>
                    <strong>${escapeHTML(fact.fact_id)}</strong>
                </div>
                <div>
                    <small>Priority</small>
                    <strong>${escapeHTML(fact.priority || "normal")}</strong>
                </div>
                <div>
                    <small>Review status</small>
                    <strong>${escapeHTML(fact.task_status || "open")}</strong>
                </div>
            </div>

            <details>
                <summary>Inspect source evidence</summary>
                <pre>${escapeHTML(JSON.stringify(fact.evidence || {}, null, 2))}</pre>
            </details>

            ${fact.status === "pending" ? `
                <div class="fact-actions">
                    <button type="button" data-review="approved"
                        data-id="${escapeHTML(fact.fact_id)}">Approve</button>
                    <button type="button" data-review="rejected"
                        data-id="${escapeHTML(fact.fact_id)}">Reject</button>
                    <button type="button" data-review="needs_revision"
                        data-id="${escapeHTML(fact.fact_id)}">Request changes</button>
                </div>
            ` : ""}
        </article>
    `).join("");

    if (empty) empty.style.display = facts.length ? "none" : "block";
}

function updateStats() {
    const total = state.facts.length;
    const pending = state.facts.filter(f => f.status === "pending").length;
    const approved = state.facts.filter(f => f.status === "approved").length;
    const other = total - pending - approved;

    $("#totalFacts").textContent = total;
    $("#pendingFacts").textContent = pending;
    $("#approvedFacts").textContent = approved;
    $("#otherFacts").textContent = other;
}

function openReview(factId, decision) {
    const fact = state.facts.find(item => item.fact_id === factId);
    if (!fact) return;

    state.selectedFact = fact;
    state.selectedDecision = decision;

    $("#reviewTitle").textContent =
        decision === "approved" ? "Approve fact" :
        decision === "rejected" ? "Reject fact" : "Request changes";

    $("#reviewDescription").textContent =
        `You are about to mark this fact as ${decision.replace("_", " ")}. Record your reasoning.`;

    $("#reviewNote").value = "";
    $("#reviewModal").classList.add("open");
}

function closeReview() {
    $("#reviewModal").classList.remove("open");
    state.selectedFact = null;
    state.selectedDecision = null;
}

async function confirmReview(event) {
    event.preventDefault();

    if (!state.selectedFact || !state.selectedDecision) return;

    const note = $("#reviewNote").value.trim();

    if (!note) {
        notify("Please enter a reviewer note.", true);
        return;
    }

    const button = $("#confirmReview");
    button.disabled = true;
    button.textContent = "Saving...";

    try {
        const params = new URLSearchParams({
            decision: state.selectedDecision,
            notes: note
        });

        await api(
            `/verification/${encodeURIComponent(state.selectedFact.fact_id)}/decision?${params}`,
            { method: "POST" }
        );

        closeReview();
        notify("Review decision saved.");
        await loadFacts();
    } catch (error) {
        notify(error.message, true);
    } finally {
        button.disabled = false;
        button.textContent = "Confirm decision";
    }
}

$("#factList")?.addEventListener("click", event => {
    const button = event.target.closest("[data-review][data-id]");
    if (!button) return;

    openReview(button.dataset.id, button.dataset.review);
});

$("#factSearch")?.addEventListener("input", renderFacts);
$("#statusFilter")?.addEventListener("change", renderFacts);
$("#categoryFilter")?.addEventListener("change", renderFacts);
$("#reviewForm")?.addEventListener("submit", confirmReview);
$("#cancelReview")?.addEventListener("click", closeReview);

document.addEventListener("DOMContentLoaded", loadFacts);