(() => {
    "use strict";

    const STORAGE_KEY = "schemesathi_admin_sources_v1";
    const $ = (id) => document.getElementById(id);

    const form = $("sourceForm");
    const modal = $("sourceModal");
    const tableBody = $("sourceTableBody");
    const emptyState = $("emptyState");

    let sources = loadSources();

    function loadSources() {
        try {
            const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
            return Array.isArray(value) ? value : [];
        } catch {
            return [];
        }
    }

    function persist() {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(sources));
    }

    function escapeHTML(value = "") {
        return String(value).replace(/[&<>"']/g, (char) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;",
            '"': "&quot;", "'": "&#39;"
        })[char]);
    }

    function statusLabel(status) {
        return ({
            unverified: "Unverified",
            under_review: "Under review",
            verified: "Verified",
            rejected: "Rejected"
        })[status] || "Unverified";
    }

    function render() {
        const query = $("searchSources").value.trim().toLowerCase();
        const status = $("statusFilter").value;

        $("totalCount").textContent = sources.length;
        $("verifiedCount").textContent = sources.filter(s => s.status === "verified").length;
        $("pendingCount").textContent = sources.filter(s => ["unverified", "under_review"].includes(s.status)).length;
        $("rejectedCount").textContent = sources.filter(s => s.status === "rejected").length;

        const filtered = sources.filter(source => {
            const matchesQuery = [
                source.publisher, source.url, source.jurisdiction,
                source.type, source.notes
            ].join(" ").toLowerCase().includes(query);

            return matchesQuery && (status === "all" || source.status === status);
        });

        $("resultCount").textContent = `${filtered.length} RECORD${filtered.length === 1 ? "" : "S"}`;
        emptyState.style.display = filtered.length ? "none" : "block";

        tableBody.innerHTML = filtered.map(source => `
            <tr>
                <td>
                    <span class="source-name">${escapeHTML(source.publisher)}</span>
                    <span class="source-url" title="${escapeHTML(source.url)}">${escapeHTML(source.url)}</span>
                </td>
                <td>${escapeHTML(source.type)}</td>
                <td>${escapeHTML(source.jurisdiction)}</td>
                <td>${escapeHTML(source.language || "en").toUpperCase()}</td>
                <td><span class="status-pill status-${escapeHTML(source.status)}">${statusLabel(source.status)}</span></td>
                <td><div class="row-actions">
                    <button class="row-action" data-edit="${escapeHTML(source.id)}">Edit</button>
                    <button class="row-action delete" data-delete="${escapeHTML(source.id)}">Delete</button>
                </div></td>
            </tr>
        `).join("");
    }

    function showToast(message) {
        const toast = $("toast");
        toast.textContent = message;
        toast.classList.add("show");
        window.clearTimeout(showToast.timer);
        showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2600);
    }

    function openModal(source = null) {
        form.reset();
        $("sourceId").value = source?.id || "";
        $("modalTitle").textContent = source ? "Edit source details" : "Register a source";
        $("saveSourceBtn").textContent = source ? "Update source" : "Save source";

        if (source) {
            $("publisher").value = source.publisher || "";
            $("sourceUrl").value = source.url || "";
            $("sourceType").value = source.type || "";
            $("jurisdiction").value = source.jurisdiction || "";
            $("sourceLanguage").value = source.language || "en";
            $("authorityStatus").value = source.status || "unverified";
            $("sourceNotes").value = source.notes || "";
        }

        modal.classList.add("open");
        $("publisher").focus();
    }

    function closeModal() {
        modal.classList.remove("open");
    }

    $("addSourceBtn").addEventListener("click", () => openModal());
    $("closeModal").addEventListener("click", closeModal);
    $("cancelModal").addEventListener("click", closeModal);

    modal.addEventListener("click", event => {
        if (event.target === modal) closeModal();
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape") closeModal();
    });

    $("searchSources").addEventListener("input", render);
    $("statusFilter").addEventListener("change", render);

    form.addEventListener("submit", event => {
        event.preventDefault();

        const urlValue = $("sourceUrl").value.trim();
        let parsedURL;

        try {
            parsedURL = new URL(urlValue);
        } catch {
            showToast("Enter a valid source URL.");
            return;
        }

        if (parsedURL.protocol !== "https:") {
            showToast("Please use an HTTPS source URL.");
            return;
        }

        const id = $("sourceId").value;
        const existing = sources.find(source => source.id === id);

        const record = {
            id: id || (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`),
            publisher: $("publisher").value.trim(),
            url: parsedURL.href,
            type: $("sourceType").value,
            jurisdiction: $("jurisdiction").value,
            language: $("sourceLanguage").value,
            status: $("authorityStatus").value,
            notes: $("sourceNotes").value.trim(),
            createdAt: existing?.createdAt || new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };

        if (!record.publisher || !record.type || !record.jurisdiction) {
            showToast("Complete all required fields.");
            return;
        }

        if (existing) {
            sources = sources.map(source => source.id === id ? record : source);
            showToast("Source details updated.");
        } else {
            const duplicate = sources.some(source => source.url.toLowerCase() === record.url.toLowerCase());
            if (duplicate) {
                showToast("This URL is already registered.");
                return;
            }
            sources.unshift(record);
            showToast("Source registered as unverified.");
        }

        persist();
        render();
        closeModal();
    });

    tableBody.addEventListener("click", event => {
        const editButton = event.target.closest("[data-edit]");
        const deleteButton = event.target.closest("[data-delete]");

        if (editButton) {
            const source = sources.find(item => item.id === editButton.dataset.edit);
            if (source) openModal(source);
        }

        if (deleteButton) {
            const id = deleteButton.dataset.delete;
            const source = sources.find(item => item.id === id);
            if (!source) return;

            if (window.confirm(`Delete the source "${source.publisher}" from this browser's preview registry?`)) {
                sources = sources.filter(item => item.id !== id);
                persist();
                render();
                showToast("Source removed from preview registry.");
            }
        }
    });

    $("exportSourcesBtn").addEventListener("click", () => {
        if (!sources.length) {
            showToast("There are no sources to export.");
            return;
        }

        const columns = ["publisher", "url", "type", "jurisdiction", "language", "status", "notes", "createdAt"];
        const csvCell = value => `"${String(value ?? "").replace(/"/g, '""')}"`;
        const csv = [
            columns.join(","),
            ...sources.map(source => columns.map(key => csvCell(source[key])).join(","))
        ].join("\r\n");

        const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = "schemesathi-source-registry.csv";
        anchor.click();
        URL.revokeObjectURL(url);
        showToast("Source registry CSV exported.");
    });

    render();
})();
