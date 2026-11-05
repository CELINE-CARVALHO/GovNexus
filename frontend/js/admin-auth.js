document.addEventListener("DOMContentLoaded", async () => {
    const api = window.SchemeSathiAPI;
    const form = document.getElementById("adminAuthForm");
    const message = document.getElementById("adminAuthMessage");
    const submit = document.getElementById("adminSubmitButton");

    function showMessage(text, type = "error") {
        message.textContent = text;
        message.className = `auth-message ${type}`;
        message.hidden = false;
    }

    function nextPath() {
        const candidate = new URLSearchParams(window.location.search).get("next");
        if (!candidate) return "dashboard.html";
        const target = new URL(candidate, window.location.href);
        if (target.origin !== window.location.origin ||
            !target.pathname.includes("/pages/admin/") ||
            target.pathname.endsWith("/login.html")) {
            return "dashboard.html";
        }
        return `${target.pathname}${target.search}${target.hash}`;
    }

    try {
        if (await api.isAuthenticated("admin")) {
            window.location.replace(nextPath());
            return;
        }
    } catch (error) {
        showMessage(`Could not check your admin session: ${error.message}`, "info");
    }
    if (new URLSearchParams(window.location.search).has("expired")) {
        showMessage("Your administrator session expired. Please sign in again.", "info");
    }

    form.addEventListener("submit", async event => {
        event.preventDefault();
        const email = document.getElementById("adminEmail").value.trim();
        const password = document.getElementById("adminPassword").value;
        if (!email || !password) {
            showMessage("Enter your administrator email and password.");
            return;
        }

        submit.disabled = true;
        message.hidden = true;
        try {
            const result = await api.post("/auth/admin/login", { email, password });
            api.markAuthenticated("admin");
            window.location.replace(nextPath());
        } catch (error) {
            showMessage(error.message || "Administrator sign in failed.");
        } finally {
            submit.disabled = false;
        }
    });
});
