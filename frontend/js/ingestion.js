document.addEventListener("DOMContentLoaded", () => {
    const api = window.SchemeSathiAPI;
    if (!api.requireAdmin()) return;

    document.getElementById("documentInput").disabled = true;
    document.getElementById("uploadZone").setAttribute("aria-disabled", "true");
    document.querySelector(".upload-button").setAttribute("aria-disabled", "true");
    document.querySelector(".upload-button").style.pointerEvents = "none";
    ["dragover", "drop"].forEach(eventName => {
        document.addEventListener(eventName, event => {
            event.preventDefault();
            event.stopPropagation();
        });
    });
    document.querySelectorAll("#documentSearch, #documentFilter, #clearQueue").forEach(control => {
        control.disabled = true;
    });
    document.getElementById("documentList").replaceChildren();
    document.getElementById("emptyQueue").style.display = "block";
    ["selectedCount", "pdfCount", "otherCount", "readyCount"].forEach(id => {
        document.getElementById(id).textContent = "Unavailable";
    });
    document.getElementById("queueCount").textContent = "UNAVAILABLE";
});
