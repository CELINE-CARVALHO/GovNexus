document.addEventListener("DOMContentLoaded", () => {
    const $ = id => document.getElementById(id);

    const categoryData = {
        identity: {
            name: "Identity & certificates",
            icon: "▤",
            description: "Documentation services"
        },
        education: {
            name: "Education & scholarships",
            icon: "✎",
            description: "Student support"
        },
        finance: {
            name: "Financial assistance",
            icon: "₹",
            description: "Financial support"
        },
        health: {
            name: "Health & welfare",
            icon: "♡",
            description: "Citizen wellbeing"
        },
        employment: {
            name: "Employment & skills",
            icon: "⌁",
            description: "Career opportunities"
        },
        business: {
            name: "Business & agriculture",
            icon: "⌂",
            description: "Enterprise and farming"
        }
    };

    const STORAGE_KEYS = {
        profile: "schemesathi_profile",
        saved: "schemesathi_saved_services",
        applications: "schemesathi_application_records",
        recent: "schemesathi_recent_services"
    };

    function readStorage(key, fallback) {
        try {
            const value = localStorage.getItem(key);
            return value ? JSON.parse(value) : fallback;
        } catch {
            return fallback;
        }
    }

    function writeStorage(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch {
            showToast("Browser storage is unavailable. Your changes could not be saved.");
            return false;
        }
    }

    function getProfile() {
        return readStorage(STORAGE_KEYS.profile, {});
    }

    function getArray(key) {
        const value = readStorage(key, []);
        return Array.isArray(value) ? value : [];
    }

    function showToast(text) {
        const toast = $("dashboardToast");
        toast.textContent = text;
        toast.classList.add("show");

        window.clearTimeout(showToast.timer);
        showToast.timer = window.setTimeout(() => {
            toast.classList.remove("show");
        }, 3000);
    }

    function initials(name) {
        const parts = String(name || "Citizen").trim().split(/\s+/);
        return parts.slice(0, 2).map(part => part[0]).join("").toUpperCase() || "U";
    }

    function updateGreeting() {
        const profile = getProfile();

        const name = profile.fullName || profile.name || "there";
        const displayName = String(name).trim().split(/\s+/)[0] || "there";
        const avatar = initials(name);

        $("welcomeName").textContent = displayName;
        $("sidebarName").textContent = name;
        $("sidebarAvatar").textContent = avatar;
        $("topbarAvatar").textContent = avatar;

        $("welcomeDate").textContent = new Intl.DateTimeFormat(
            profile.preferredLanguage || "en",
            { weekday: "long", day: "numeric", month: "long", year: "numeric" }
        ).format(new Date()).toUpperCase();

        const fields = [
            profile.fullName || profile.name,
            profile.email,
            profile.preferredLanguage,
            profile.state,
            profile.phone
        ];

        const completed = fields.filter(value =>
            value !== null && value !== undefined && String(value).trim() !== ""
        ).length;

        const percent = Math.round(completed / fields.length * 100);

        $("profileCompletion").textContent = `${percent}%`;
        $("progressValue").textContent = `${percent}%`;
        $("progressCircle").style.background =
            `conic-gradient(#6c59db ${percent}%, #eeeefa ${percent}%)`;

        $("profileProgressText").textContent =
            percent >= 80 ? "Your profile looks good" : "Complete your profile";
    }

    function updateStats() {
        const saved = getArray(STORAGE_KEYS.saved);
        const applications = getArray(STORAGE_KEYS.applications);
        const recent = getArray(STORAGE_KEYS.recent);

        $("savedCount").textContent = saved.length;
        $("applicationCount").textContent = applications.length;
        $("recentCount").textContent = recent.length;
    }

    function renderSaved() {
        const saved = getArray(STORAGE_KEYS.saved);
        const grid = $("savedGrid");
        grid.replaceChildren();

        if (!saved.length) {
            const empty = document.createElement("div");
            empty.className = "empty-dashboard compact-empty";
            empty.innerHTML = `
                <div class="empty-dashboard-icon">♡</div>
                <h3>No saved services yet</h3>
                <p>Explore the directory and save categories you want to revisit.</p>
                <a href="services.html">Explore services →</a>
            `;
            grid.appendChild(empty);
            return;
        }

        saved.forEach(item => {
            const data = categoryData[item.category];

            if (!data) return;

            const card = document.createElement("div");
            card.className = "saved-card";

            const icon = document.createElement("span");
            icon.className = "recommendation-icon purple-bg";
            icon.textContent = data.icon;

            const info = document.createElement("div");
            info.className = "saved-card-info";

            const title = document.createElement("strong");
            title.textContent = data.name;

            const description = document.createElement("small");
            description.textContent = data.description;

            info.append(title, description);

            const actions = document.createElement("div");
            actions.className = "saved-card-actions";

            const open = document.createElement("a");
            open.href = `service-detail.html?category=${encodeURIComponent(item.category)}`;
            open.textContent = "Open";

            const remove = document.createElement("button");
            remove.type = "button";
            remove.textContent = "Remove";
            remove.addEventListener("click", () => {
                const updated = getArray(STORAGE_KEYS.saved)
                    .filter(savedItem => savedItem.category !== item.category);

                writeStorage(STORAGE_KEYS.saved, updated);
                renderSaved();
                updateStats();
                showToast("Saved category removed.");
            });

            actions.append(open, remove);
            card.append(icon, info, actions);
            grid.appendChild(card);
        });
    }

    function renderApplications() {
        const applications = getArray(STORAGE_KEYS.applications);
        const list = $("applicationsList");
        list.replaceChildren();

        if (!applications.length) {
            const empty = document.createElement("div");
            empty.className = "empty-dashboard";
            empty.innerHTML = `
                <div class="empty-dashboard-icon">▤</div>
                <h3>No applications tracked yet</h3>
                <p>Add an application record to organise your progress. SchemeSathi does not automatically know the status of applications submitted on government portals.</p>
                <button type="button" id="firstApplicationButton">Add an application record</button>
            `;

            list.appendChild(empty);
            $("firstApplicationButton").addEventListener("click", openModal);
            return;
        }

        applications.forEach((application, index) => {
            const row = document.createElement("div");
            row.className = "recent-item";

            const icon = document.createElement("span");
            icon.className = "recent-item-icon";
            icon.textContent = "▤";

            const info = document.createElement("div");
            info.style.minWidth = "0";

            const title = document.createElement("strong");
            title.textContent = application.name;

            const detail = document.createElement("small");
            detail.textContent = [
                application.reference ? `Ref: ${application.reference}` : "Personal record",
                application.status || "Planning"
            ].join(" · ");

            info.append(title, detail);

            const status = document.createElement("span");
            status.className = "item-tag";
            status.textContent = application.status || "Planning";

            const remove = document.createElement("button");
            remove.type = "button";
            remove.textContent = "×";
            remove.title = "Remove record";
            remove.style.marginLeft = "auto";
            remove.style.border = "0";
            remove.style.background = "transparent";
            remove.style.color = "#bd7777";
            remove.style.cursor = "pointer";
            remove.addEventListener("click", () => {
                const updated = getArray(STORAGE_KEYS.applications);
                updated.splice(index, 1);
                writeStorage(STORAGE_KEYS.applications, updated);
                renderApplications();
                updateStats();
                showToast("Application record removed.");
            });

            row.append(icon, info, status, remove);
            list.appendChild(row);
        });
    }

    function renderRecent() {
        const recent = getArray(STORAGE_KEYS.recent);
        const list = $("recentList");
        list.replaceChildren();

        if (!recent.length) {
            const empty = document.createElement("div");
            empty.className = "empty-dashboard compact-empty";
            empty.innerHTML = `
                <div class="empty-dashboard-icon">◷</div>
                <h3>No recent activity</h3>
                <p>Services you explore will appear here when browsing history is connected.</p>
            `;
            list.appendChild(empty);
            return;
        }

        recent.slice(0, 5).forEach(item => {
            const row = document.createElement("div");
            row.className = "recent-item";

            const icon = document.createElement("span");
            icon.className = "recent-item-icon";
            icon.textContent = categoryData[item.category]?.icon || "⌕";

            const info = document.createElement("div");
            const title = document.createElement("strong");
            title.textContent = item.title || categoryData[item.category]?.name || "Service";

            const date = document.createElement("small");
            date.textContent = item.viewedAt
                ? new Date(item.viewedAt).toLocaleDateString()
                : "Recently viewed";

            info.append(title, date);

            const link = document.createElement("a");
            link.href = item.serviceId
                ? `service-detail.html?id=${encodeURIComponent(item.serviceId)}`
                : `service-detail.html?category=${encodeURIComponent(item.category || "")}`;
            link.textContent = "→";

            row.append(icon, info, link);
            list.appendChild(row);
        });
    }

    function openModal() {
        $("applicationModal").hidden = false;
        $("applicationName").focus();
    }

    function closeModal() {
        $("applicationModal").hidden = true;
        $("applicationForm").reset();
    }

    $("addApplicationButton").addEventListener("click", openModal);
    $("firstApplicationButton")?.addEventListener("click", openModal);
    $("closeModal").addEventListener("click", closeModal);
    $("cancelModal").addEventListener("click", closeModal);

    $("applicationModal").addEventListener("click", event => {
        if (event.target === $("applicationModal")) {
            closeModal();
        }
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && !$("applicationModal").hidden) {
            closeModal();
        }
    });

    $("applicationForm").addEventListener("submit", event => {
        event.preventDefault();

        const name = $("applicationName").value.trim();

        if (!name) {
            showToast("Please enter an application name.");
            return;
        }

        const applications = getArray(STORAGE_KEYS.applications);

        applications.unshift({
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            name,
            reference: $("applicationReference").value.trim(),
            status: $("applicationStatus").value,
            notes: $("applicationNotes").value.trim(),
            createdAt: new Date().toISOString()
        });

        if (writeStorage(STORAGE_KEYS.applications, applications)) {
            closeModal();
            renderApplications();
            updateStats();
            showToast("Your personal application record has been saved.");
        }
    });

    $("notificationButton").addEventListener("click", () => {
        showToast("You don't have any connected government notifications yet.");
    });

    $("logoutButton").addEventListener("click", () => {
        const confirmed = window.confirm("Sign out of this dashboard?");

        if (!confirmed) return;

        // Frontend preview only. Real authentication must clear the backend session.
        window.location.href = "login.html";
    });

    $("menuToggle").addEventListener("click", () => {
        $("sidebar").classList.toggle("open");
    });

    document.querySelectorAll(".assistant-prompts a").forEach(link => {
        link.addEventListener("click", () => {
            try {
                sessionStorage.setItem(
                    "schemesathi_initial_prompt",
                    link.dataset.prompt || ""
                );
            } catch {
                // Continue to the assistant without prefilled text.
            }
        });
    });

    updateGreeting();
    updateStats();
    renderSaved();
    renderApplications();
    renderRecent();

    // Expose a small helper so other frontend pages can save a category.
    window.SchemeSathiDashboard = {
        saveCategory(category) {
            if (!categoryData[category]) return false;

            const saved = getArray(STORAGE_KEYS.saved);

            if (saved.some(item => item.category === category)) {
                showToast("This category is already saved.");
                return false;
            }

            saved.unshift({
                category,
                savedAt: new Date().toISOString()
            });

            const success = writeStorage(STORAGE_KEYS.saved, saved);

            if (success) {
                renderSaved();
                updateStats();
                showToast("Category saved to your dashboard.");
            }

            return success;
        },

        addRecent(category, title, serviceId = null) {
            const recent = getArray(STORAGE_KEYS.recent).filter(item =>
                !(item.category === category && item.serviceId === serviceId)
            );

            recent.unshift({
                category,
                title,
                serviceId,
                viewedAt: new Date().toISOString()
            });

            writeStorage(STORAGE_KEYS.recent, recent.slice(0, 10));
            renderRecent();
            updateStats();
        }
    };
});
