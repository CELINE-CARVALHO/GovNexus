document.addEventListener("DOMContentLoaded", async () => {
    const api = window.SchemeSathiAPI;
    if (!api.requireAdmin()) return;

    const $ = id => document.getElementById(id);
    const VERIFIED = new Set(["verified", "official", "authoritative"]);
    let sources = [];
    let toastTimer;

    function notify(message) {
        const toast = $("toast");
        if (!toast) return;
        toast.textContent = message;
        toast.classList.add("show");
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => toast.classList.remove("show"), 3000);
    }

    function label(value) {
        return String(value || "—").replaceAll("_", " ");
    }

    function formatDate(value) {
        if (!value) return "Never";
        const date = new Date(value.endsWith("Z") || value.includes("+") ? value : `${value}Z`);
        if (Number.isNaN(date.getTime())) return "—";
        return new Intl.DateTimeFormat("en-IN", {
            day: "numeric", month: "short", year: "numeric"
        }).format(date);
    }

    function pillClass(status) {
        if (VERIFIED.has(status)) return "status-verified";
        if (status === "rejected") return "status-rejected";
        return "status-unverified";
    }

    function filteredSources() {
        const query = $("searchSources").value.trim().toLowerCase();
        const status = $("statusFilter").value;
        return sources.filter(source => {
            if (status !== "all" && source.authority_status !== status) return false;
            if (!query) return true;
            return [source.publisher_name, source.url, source.source_type, source.language_code]
                .some(value => String(value || "").toLowerCase().includes(query));
        });
    }

    function updateStats() {
        $("totalCount").textContent = String(sources.length);
        $("verifiedCount").textContent = String(
            sources.filter(item => VERIFIED.has(item.authority_status)).length
        );
        $("pendingCount").textContent = String(
            sources.filter(item => item.authority_status === "unverified").length
        );
        $("rejectedCount").textContent = String(
            sources.filter(item => item.authority_status === "rejected").length
        );
    }

    function render() {
        const rows = filteredSources();
        const body = $("sourceTableBody");
        body.replaceChildren();
        $("resultCount").textContent = `${rows.length} ${rows.length === 1 ? "RECORD" : "RECORDS"}`;
        $("emptyState").hidden = rows.length > 0;
        if (!rows.length) {
            $("emptyDetail").textContent = sources.length
                ? "No registered sources match your search or filter."
                : "No sources have been registered yet.";
        }
        rows.forEach(source => {
            const row = document.createElement("tr");

            const nameCell = document.createElement("td");
            const name = document.createElement("span");
            name.className = "source-name";
            name.textContent = source.publisher_name || "Unnamed publisher";
            const url = document.createElement("a");
            url.className = "source-url";
            url.href = source.url;
            url.target = "_blank";
            url.rel = "noopener noreferrer";
            url.title = source.url;
            url.textContent = source.url;
            nameCell.append(name, url);

            const typeCell = document.createElement("td");
            typeCell.textContent = label(source.source_type);

            const languageCell = document.createElement("td");
            languageCell.textContent = (source.language_code || "—").toUpperCase();

            const statusCell = document.createElement("td");
            const pill = document.createElement("span");
            pill.className = `status-pill ${pillClass(source.authority_status)}`;
            pill.textContent = label(source.authority_status);
            statusCell.appendChild(pill);

            const checkedCell = document.createElement("td");
            checkedCell.textContent = formatDate(source.last_checked_at);

            const activeCell = document.createElement("td");
            activeCell.className = source.is_active ? "active-yes" : "active-no";
            activeCell.textContent = source.is_active ? "Active" : "Inactive";

            row.append(nameCell, typeCell, languageCell, statusCell, checkedCell, activeCell);
            body.appendChild(row);
        });
    }

    function csvCell(value) {
        let text = String(value ?? "");
        if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
        return `"${text.replaceAll('"', '""')}"`;
    }

    $("exportSourcesBtn").addEventListener("click", () => {
        const rows = filteredSources();
        if (!rows.length) {
            notify("There are no sources to export.");
            return;
        }
        const header = ["Publisher", "URL", "Source type", "Language", "Authority status", "Active", "Last checked"];
        const lines = [header.map(csvCell).join(",")].concat(
            rows.map(source => [
                source.publisher_name,
                source.url,
                source.source_type,
                source.language_code || "",
                source.authority_status,
                source.is_active ? "yes" : "no",
                source.last_checked_at || ""
            ].map(csvCell).join(","))
        );
        const blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "schemesathi-sources.csv";
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
        notify(`Exported ${rows.length} ${rows.length === 1 ? "source" : "sources"}.`);
    });

    let searchTimer;
    $("searchSources").addEventListener("input", () => {
        window.clearTimeout(searchTimer);
        searchTimer = window.setTimeout(render, 150);
    });
    $("statusFilter").addEventListener("change", render);

    try {
        const limit = 200;
        let offset = 0;
        let total = 0;
        do {
            const result = await api.get(
                `/admin/sources?active_only=false&limit=${limit}&offset=${offset}`,
                "admin"
            );
            sources.push(...(Array.isArray(result.items) ? result.items : []));
            total = Number(result.total) || 0;
            offset += limit;
        } while (sources.length < total && offset < 10000);
        $("registryEnv").textContent = "LIVE DATA";
        $("registrySubtitle").textContent = "Records are read live from the administration API.";
        updateStats();
        render();
    } catch (error) {
        $("registryEnv").textContent = "UNAVAILABLE";
        $("registrySubtitle").textContent = "Source records could not be loaded.";
        ["totalCount", "verifiedCount", "pendingCount", "rejectedCount"].forEach(id => {
            $(id).textContent = "—";
        });
        $("emptyState").hidden = false;
        $("emptyDetail").textContent = error.message;
        $("resultCount").textContent = "0 RECORDS";
        notify(`Sources could not be loaded: ${error.message}`);
    }
});