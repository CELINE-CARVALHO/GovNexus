(() => {
    const api = window.SchemeSathiAPI;
    if (!api?.requireAdmin()) return;

    const sidebar = document.getElementById("adminSidebar");
    const menuButton = document.getElementById("mobileMenu");

    if (sidebar && menuButton) {
        menuButton.addEventListener("click", () => {
            sidebar.classList.toggle("open");
        });

        document.addEventListener("click", (event) => {
            if (
                window.innerWidth <= 800 &&
                sidebar.classList.contains("open") &&
                !sidebar.contains(event.target) &&
                !menuButton.contains(event.target)
            ) {
                sidebar.classList.remove("open");
            }
        });
    }

    const dateElement = document.getElementById("currentDate");

    if (dateElement) {
        dateElement.textContent = new Intl.DateTimeFormat("en-IN", {
            weekday: "short",
            day: "numeric",
            month: "long",
            year: "numeric"
        }).format(new Date());
    }

    const adminUser = document.querySelector(".admin-user");
    if (adminUser) {
        adminUser.querySelector("strong").textContent = "Administrator";
        adminUser.querySelector("small").textContent = "Authenticated session";
        const logout = document.createElement("button");
        logout.type = "button";
        logout.className = "admin-logout";
        logout.textContent = "Sign out";
        logout.addEventListener("click", async () => {
            logout.disabled = true;
            try {
                await api.post("/auth/admin/logout");
                api.clearSession("admin");
                window.location.replace("login.html");
            } catch (error) {
                logout.disabled = false;
                window.alert(`Could not sign out: ${error.message}`);
            }
        });
        adminUser.appendChild(logout);
    }

    api.get("/admin/dashboard", "admin").then(data => {
        const dashboard = document.getElementById("adminDashboard");
        if (!dashboard) return;
        const values = {
            totalServices: data.services?.total,
            totalSources: data.sources?.total,
            pendingFacts: data.facts?.pending_review,
            verifiedFacts: data.facts?.verified,
            openTasks: data.review?.open_tasks,
            openTasksTotal: data.review?.open_tasks,
            duplicateSuggestions: data.review?.pending_duplicate_suggestions,
            failedIngestion: data.ingestion?.failed
        };
        Object.entries(values).forEach(([id, value]) => {
            const node = document.getElementById(id);
            if (node) node.textContent = Number.isFinite(Number(value)) ? String(value) : "—";
        });
        const notice = document.getElementById("dashboardNotice");
        if (notice) {
            notice.querySelector("strong").textContent = "Live administration data";
            notice.querySelector("p").textContent =
                "Metrics are retrieved from the authenticated administration API.";
        }
        const footer = document.getElementById("dashboardDataStatus");
        if (footer) footer.textContent = "Live data · authenticated API";
    }).catch(error => {
        const notice = document.getElementById("dashboardNotice");
        if (notice) {
            notice.querySelector("strong").textContent = "Dashboard data unavailable";
            notice.querySelector("p").textContent = error.message;
        }
    });
})();
