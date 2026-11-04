(() => {
    "use strict";

    const MAX_FILE_SIZE = 20 * 1024 * 1024;
    const ALLOWED = new Set(["pdf", "docx", "txt", "md", "csv"]);

    const $ = id => document.getElementById(id);
    const input = $("documentInput");
    const zone = $("uploadZone");

    // File objects intentionally stay in memory; they are not persisted.
    let files = [];

    function extension(name) {
        return name.includes(".") ? name.split(".").pop().toLowerCase() : "";
    }

    function formatSize(bytes) {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }

    function escapeHTML(value = "") {
        return String(value).replace(/[&<>"']/g, char => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;",
            '"': "&quot;", "'": "&#39;"
        })[char]);
    }

    function notify(message) {
        const toast = $("ingestToast");
        toast.textContent = message;
        toast.classList.add("show");
        clearTimeout(notify.timer);
        notify.timer = setTimeout(() => toast.classList.remove("show"), 2800);
    }

    function addFiles(selectedFiles) {
        let added = 0;

        for (const file of selectedFiles) {
            const ext = extension(file.name);

            if (!ALLOWED.has(ext)) {
                notify(`Unsupported file format: ${file.name}`);
                continue;
            }

            if (file.size > MAX_FILE_SIZE) {
                notify(`${file.name} exceeds the 20 MB limit.`);
                continue;
            }

            if (files.some(item =>
                item.name.toLowerCase() === file.name.toLowerCase() &&
                item.size === file.size &&
                item.lastModified === file.lastModified
            )) {
                continue;
            }

            files.unshift({
                id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
                name: file.name,
                size: file.size,
                type: ext,
                lastModified: file.lastModified,
                addedAt: new Date().toISOString()
            });

            added++;
        }

        render();

        if (added) notify(`${added} document${added === 1 ? "" : "s"} added to the local queue.`);
        input.value = "";
    }

    function render() {
        const query = $("documentSearch").value.trim().toLowerCase();
        const filter = $("documentFilter").value;

        $("selectedCount").textContent = files.length;
        $("pdfCount").textContent = files.filter(file => file.type === "pdf").length;
        $("otherCount").textContent = files.filter(file => file.type !== "pdf").length;
        $("readyCount").textContent = files.length;

        const filtered = files.filter(file => {
            const matchesSearch = file.name.toLowerCase().includes(query);
            const matchesType =
                filter === "all" ||
                (filter === "pdf" && file.type === "pdf") ||
                (filter === "docx" && file.type === "docx") ||
                (filter === "other" && !["pdf", "docx"].includes(file.type));

            return matchesSearch && matchesType;
        });

        $("queueCount").textContent = `${filtered.length} FILE${filtered.length === 1 ? "" : "S"}`;
        $("emptyQueue").style.display = filtered.length ? "none" : "block";

        $("documentList").innerHTML = filtered.map(file => {
            const iconClass = file.type === "docx" ? "doc" :
                ["txt", "md", "csv"].includes(file.type) ? "text" : "";

            return `
                <article class="document-row">
                    <div class="file-icon ${iconClass}">${escapeHTML(file.type.toUpperCase())}</div>
                    <div class="file-main">
                        <strong title="${escapeHTML(file.name)}">${escapeHTML(file.name)}</strong>
                        <small>${formatSize(file.size)} · Added ${new Date(file.addedAt).toLocaleString("en-IN")}</small>
                    </div>
                    <span class="file-status">Ready for integration</span>
                    <div class="file-actions">
                        <button type="button" data-remove="${escapeHTML(file.id)}">Remove</button>
                    </div>
                </article>
            `;
        }).join("");
    }

    input.addEventListener("change", () => addFiles(Array.from(input.files || [])));

    ["dragenter", "dragover"].forEach(eventName => {
        zone.addEventListener(eventName, event => {
            event.preventDefault();
            zone.classList.add("dragover");
        });
    });

    ["dragleave", "drop"].forEach(eventName => {
        zone.addEventListener(eventName, event => {
            event.preventDefault();
            zone.classList.remove("dragover");
        });
    });

    zone.addEventListener("drop", event => {
        addFiles(Array.from(event.dataTransfer?.files || []));
    });

    $("documentSearch").addEventListener("input", render);
    $("documentFilter").addEventListener("change", render);

    $("documentList").addEventListener("click", event => {
        const button = event.target.closest("[data-remove]");
        if (!button) return;

        files = files.filter(file => file.id !== button.dataset.remove);
        render();
        notify("Document removed from the local queue.");
    });

    $("clearQueue").addEventListener("click", () => {
        if (!files.length) {
            notify("The document queue is already empty.");
            return;
        }

        if (confirm("Remove all selected documents from this browser queue?")) {
            files = [];
            render();
            notify("Document queue cleared.");
        }
    });

    render();
})();
