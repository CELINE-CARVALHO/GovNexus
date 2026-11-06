document.addEventListener("DOMContentLoaded", async () => {
    const api = window.SchemeSathiAPI;
    if (!api.requireCitizen()) return;

    const $ = id => document.getElementById(id);
    const languageFallback = "en";
    let profile = null;
    let savedServices = [];
    let applications = [];
    let categories = [];
    let toastTimer;

    function showToast(message) {
        const toast = $("dashboardToast");
        if (!toast) return;
        toast.textContent = message;
        toast.classList.add("show");
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => toast.classList.remove("show"), 3200);
    }

    function initials(name) {
        return String(name || "Citizen").trim().split(/\s+/).slice(0, 2)
            .map(part => part[0] || "").join("").toUpperCase() || "U";
    }

    function updateGreeting() {
        const name = profile?.display_name || "Citizen";
        const firstName = name.trim().split(/\s+/)[0] || "Citizen";
        const avatar = initials(name);
        $("welcomeName").textContent = firstName;
        $("sidebarName").textContent = name;
        $("sidebarAvatar").textContent = avatar;
        $("topbarAvatar").textContent = avatar;
        $("welcomeDate").textContent = new Intl.DateTimeFormat(
            profile?.preferred_language_code || languageFallback,
            { weekday: "long", day: "numeric", month: "long", year: "numeric" }
        ).format(new Date()).toUpperCase();

        const completionFields = [
            profile?.display_name,
            profile?.email,
            profile?.preferred_language_code,
            profile?.state_id
        ];
        const percent = Math.round(
            completionFields.filter(value => value !== null && value !== undefined && String(value).trim()).length /
            completionFields.length * 100
        );
        $("profileCompletion").textContent = `${percent}%`;
        $("progressValue").textContent = `${percent}%`;
        $("progressCircle").style.background =
            `conic-gradient(#6c59db ${percent}%, #eeeefa ${percent}%)`;
        $("profileProgressText").textContent =
            percent >= 75 ? "Your profile looks good" : "Complete your profile";
    }

    function updateStats() {
        $("savedCount").textContent = savedServices.length;
        $("applicationCount").textContent = applications.length;
        $("recentCount").textContent = "—";
    }

    async function getAllPages(path) {
        const items = [];
        let page = 1;
        let pages = 1;
        do {
            const separator = path.includes("?") ? "&" : "?";
            const result = await api.get(`${path}${separator}page=${page}&limit=100`, "citizen");
            items.push(...(Array.isArray(result.items) ? result.items : []));
            pages = Number(result.pagination?.pages) || 1;
            page += 1;
        } while (page <= pages);
        return items;
    }

    function createEmpty(message, detail, link) {
        const box = document.createElement("div");
        box.className = "empty-dashboard compact-empty";
        const title = document.createElement("h3");
        title.textContent = message;
        const paragraph = document.createElement("p");
        paragraph.textContent = detail;
        box.append(title, paragraph);
        if (link) {
            const anchor = document.createElement("a");
            anchor.href = link.href;
            anchor.textContent = link.label;
            box.appendChild(anchor);
        }
        return box;
    }

    function renderSaved() {
        const grid = $("savedGrid");
        grid.replaceChildren();
        if (!savedServices.length) {
            grid.appendChild(createEmpty(
                "No saved services yet",
                "Published services you save will appear here.",
                { href: "services.html", label: "Explore services →" }
            ));
            return;
        }

        savedServices.forEach(service => {
            const card = document.createElement("div");
            card.className = "saved-card";
            const info = document.createElement("div");
            info.className = "saved-card-info";
            const title = document.createElement("strong");
            title.textContent = service.title || service.code;
            const description = document.createElement("small");
            description.textContent = service.description || "Published service";
            info.append(title, description);
            const actions = document.createElement("div");
            actions.className = "saved-card-actions";
            const open = document.createElement("a");
            open.href = `service-detail.html?id=${encodeURIComponent(service.service_id)}`;
            open.textContent = "Open";
            const remove = document.createElement("button");
            remove.type = "button";
            remove.textContent = "Remove";
            remove.addEventListener("click", async () => {
                remove.disabled = true;
                try {
                    await api.delete(`/users/me/saved-services/${encodeURIComponent(service.service_id)}`, "citizen");
                    savedServices = savedServices.filter(item => item.service_id !== service.service_id);
                    renderSaved();
                    updateStats();
                    showToast("Saved service removed.");
                } catch (error) {
                    remove.disabled = false;
                    showToast(error.message);
                }
            });
            actions.append(open, remove);
            card.append(info, actions);
            grid.appendChild(card);
        });
    }

    function renderApplications() {
        const list = $("applicationsList");
        list.replaceChildren();
        if (!applications.length) {
            list.appendChild(createEmpty(
                "No applications tracked yet",
                "Add a citizen-recorded tracking entry for a published service. SchemeSathi does not receive live government portal status.",
                { href: "applications.html", label: "Open application tracker →" }
            ));
            return;
        }

        applications.slice(0, 5).forEach(application => {
            const row = document.createElement("div");
            row.className = "recent-item";
            const info = document.createElement("div");
            info.style.minWidth = "0";
            const title = document.createElement("strong");
            title.textContent = application.service?.code || "Published service";
            const detail = document.createElement("small");
            detail.textContent = `${application.reference_number || "No reference number"} · ${application.status.replaceAll("_", " ")}`;
            const status = document.createElement("span");
            status.className = "item-tag";
            status.textContent = application.status.replaceAll("_", " ");
            info.append(title, detail);
            row.append(info, status);
            list.appendChild(row);
        });
    }

    function renderCategories() {
        const list = document.querySelector(".recommendation-list");
        if (!list) return;
        list.replaceChildren();
        if (!categories.length) {
            list.appendChild(createEmpty(
                "Categories unavailable",
                "The published catalogue categories could not be loaded."
            ));
            return;
        }
        categories.forEach(category => {
            const link = document.createElement("a");
            link.href = `services.html?category=${encodeURIComponent(category.id)}`;
            const title = document.createElement("strong");
            title.textContent = category.name || category.code;
            const code = document.createElement("small");
            code.textContent = category.code;
            const text = document.createElement("span");
            text.append(title, code);
            link.append(text);
            list.appendChild(link);
        });
    }

    function renderRecentUnavailable() {
        const list = $("recentList");
        if (!list) return;
        list.replaceChildren(createEmpty(
            "Recent activity is unavailable",
            "The API does not expose a browsing-history endpoint."
        ));
    }

    function buildReminders() {
        const reminders = [];
        applications
            .filter(item => item.status === "additional_information_requested")
            .forEach(item => reminders.push({
                title: "Additional information recorded as requested",
                detail: `${item.service?.code || "A tracked service"}${item.reference_number ? ` · ${item.reference_number}` : ""}`,
                href: "applications.html"
            }));
        if (!profile?.state_id) {
            reminders.push({
                title: "Add your state to your profile",
                detail: "This helps SchemeSathi show services relevant to your area.",
                href: "profile.html"
            });
        }
        if (savedServices.length && !applications.length) {
            reminders.push({
                title: `You have ${savedServices.length} saved ${savedServices.length === 1 ? "service" : "services"}`,
                detail: "When you apply, record it in your application tracker.",
                href: "applications.html"
            });
        }
        return reminders;
    }

    function renderNotifications() {
        const list = $("notificationList");
        const reminders = buildReminders();
        list.replaceChildren();
        $("notificationDot").hidden = reminders.length === 0;
        $("notificationButton").setAttribute(
            "aria-label",
            reminders.length ? `Reminders, ${reminders.length}` : "Reminders"
        );
        if (!reminders.length) {
            const empty = document.createElement("p");
            empty.className = "notification-empty";
            empty.textContent = "You are all caught up. No reminders right now.";
            list.appendChild(empty);
            return;
        }
        reminders.forEach(reminder => {
            const link = document.createElement("a");
            link.className = "notification-item";
            link.href = reminder.href;
            const title = document.createElement("strong");
            title.textContent = reminder.title;
            const detail = document.createElement("span");
            detail.textContent = reminder.detail;
            link.append(title, detail);
            list.appendChild(link);
        });
    }

    function setNotificationPanel(open) {
        $("notificationPanel").hidden = !open;
        $("notificationButton").setAttribute("aria-expanded", String(open));
        if (open) $("closeNotifications").focus();
    }

    $("notificationButton")?.addEventListener("click", () => {
        setNotificationPanel($("notificationPanel").hidden);
    });
    $("closeNotifications")?.addEventListener("click", () => {
        setNotificationPanel(false);
        $("notificationButton").focus();
    });
    document.addEventListener("click", event => {
        if (!$("notificationPanel").hidden &&
            !event.target.closest(".notification-wrap")) {
            setNotificationPanel(false);
        }
    });
    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && !$("notificationPanel").hidden) {
            setNotificationPanel(false);
            $("notificationButton").focus();
        }
    });

    $("addApplicationButton")?.addEventListener("click", () => {
        window.location.href = "applications.html";
    });
    $("firstApplicationButton")?.addEventListener("click", () => {
        window.location.href = "applications.html";
    });
    $("logoutButton")?.addEventListener("click", async () => {
        if (!window.confirm("Sign out of SchemeSathi?")) return;
        try {
            await api.post("/auth/citizen/logout", undefined, "citizen");
            api.clearSession("citizen");
            window.location.replace("login.html");
        } catch (error) {
            showToast(`Could not contact the server to sign out: ${error.message}`);
        }
    });
    $("menuToggle")?.addEventListener("click", () => $("sidebar").classList.toggle("open"));
    document.querySelectorAll(".assistant-prompts a").forEach(link => {
        link.addEventListener("click", () => {
            try {
                sessionStorage.setItem("schemesathi_initial_prompt", link.dataset.prompt || "");
            } catch (error) {
                showToast("Could not save the assistant prompt in this browser session.");
            }
        });
    });

    try {
        profile = await api.get("/users/me", "citizen");
        const language = profile.preferred_language_code || languageFallback;
        const [savedResult, applicationItems, categoryItems] = await Promise.all([
            api.get(`/users/me/saved-services?language=${encodeURIComponent(language)}`, "citizen"),
            getAllPages("/users/me/applications"),
            getAllPages(`/categories?language=${encodeURIComponent(language)}&active_only=true`)
        ]);
        savedServices = Array.isArray(savedResult.items) ? savedResult.items : [];
        applications = applicationItems;
        categories = categoryItems;
        updateGreeting();
        updateStats();
        renderSaved();
        renderApplications();
        renderCategories();
        renderRecentUnavailable();
        renderNotifications();
    } catch (error) {
        renderNotifications();
        showToast(`Dashboard data could not be loaded: ${error.message}`);
        $("savedGrid").replaceChildren(createEmpty("Saved services unavailable", error.message));
        $("applicationsList").replaceChildren(createEmpty("Application records unavailable", error.message));
        renderRecentUnavailable();
    }
});