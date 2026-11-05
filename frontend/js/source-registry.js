document.addEventListener("DOMContentLoaded", () => {
    const api = window.SchemeSathiAPI;
    if (!api.requireAdmin()) return;

    document.querySelectorAll(
        "#addSourceBtn, #exportSourcesBtn, #sourceForm input, #sourceForm select, #sourceForm textarea, #sourceForm button, #searchSources, #statusFilter"
    ).forEach(control => {
        control.disabled = true;
    });
    document.getElementById("sourceTableBody").replaceChildren();
    document.getElementById("emptyState").style.display = "block";
    ["totalCount", "verifiedCount", "pendingCount", "rejectedCount"].forEach(id => {
        document.getElementById(id).textContent = "Unavailable";
    });
});
