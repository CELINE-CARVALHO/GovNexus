document.addEventListener("DOMContentLoaded", () => {
    const api = window.SchemeSathiAPI;
    const $ = id => document.getElementById(id);
    const state = {
        categories: [],
        services: [],
        locations: [],
        categoryId: "",
        search: new URLSearchParams(window.location.search).get("q") || "",
        stateId: "",
        jurisdictionCode: "",
        level: "all",
        page: 1,
        pages: 1,
        demo: false,
        requestId: 0,
        timer: null,
        language: "en"
    };

    const categoryGrid = $("categoryGrid");
    const categoryFilters = $("categoryFilters");
    const searchInput = $("serviceSearch");
    const searchButton = $("searchButton");
    const clearButton = $("clearSearch");
    const stateFilter = $("stateFilter");
    const activeFilters = $("activeFilters");
    const emptyState = $("emptyState");
    const resultsCount = $("resultsCount");

    function createCatalogueSection() {
        let section = $("liveCatalogue");
        if (section) return section;
        section = document.createElement("section");
        section.id = "liveCatalogue";
        section.className = "live-catalogue-section";
        section.setAttribute("aria-live", "polite");
        categoryGrid.insertAdjacentElement("afterend", section);
        return section;
    }

    function showError(message) {
        const section = createCatalogueSection();
        section.replaceChildren();
        const error = document.createElement("div");
        error.className = "live-catalogue-empty";
        error.setAttribute("role", "alert");
        const heading = document.createElement("h3");
        heading.textContent = "Catalogue temporarily unavailable";
        const detail = document.createElement("p");
        detail.textContent = message;
        error.append(heading, detail);
        section.appendChild(error);
    }

    async function getAllPages(path) {
        const items = [];
        let page = 1;
        let pages = 1;
        do {
            const separator = path.includes("?") ? "&" : "?";
            const result = await api.get(`${path}${separator}page=${page}&limit=100`);
            items.push(...(Array.isArray(result.items) ? result.items : []));
            pages = Number(result.pagination?.pages) || 1;
            page += 1;
        } while (page <= pages);
        return items;
    }

    function renderCategories() {
        categoryGrid.replaceChildren();
        categoryFilters.replaceChildren();
        if (!state.categories.length) {
            categoryGrid.hidden = true;
            return;
        }
        categoryGrid.hidden = false;
        state.categories.forEach((category, index) => {
            const card = document.createElement("a");
            card.className = `category-card category-${["purple", "blue", "green", "orange", "pink", "yellow"][index % 6]}`;
            card.href = "#liveCatalogue";
            const title = document.createElement("h3");
            title.textContent = category.name || category.code;
            const description = document.createElement("p");
            description.textContent = "Browse published services in this category.";
            const link = document.createElement("span");
            link.className = "category-link";
            link.textContent = "Browse published services →";
            card.append(title, description, link);
            card.addEventListener("click", event => {
                event.preventDefault();
                state.categoryId = state.categoryId === category.id ? "" : category.id;
                state.page = 1;
                syncCategoryFilters();
                loadServices();
                $("liveCatalogue").scrollIntoView({ behavior: "smooth", block: "start" });
            });
            categoryGrid.appendChild(card);

            const label = document.createElement("label");
            label.className = "filter-option";
            const input = document.createElement("input");
            input.type = "checkbox";
            input.name = "category";
            input.value = category.id;
            input.checked = state.categoryId === category.id;
            input.addEventListener("change", () => {
                state.categoryId = input.checked ? category.id : "";
                state.page = 1;
                syncCategoryFilters();
                loadServices();
            });
            const text = document.createElement("span");
            text.textContent = category.name || category.code;
            label.append(input, text);
            categoryFilters.appendChild(label);
        });
    }

    function syncCategoryFilters() {
        categoryFilters.querySelectorAll('input[name="category"]').forEach(input => {
            input.checked = input.value === state.categoryId;
        });
    }

    function renderActiveFilters() {
        activeFilters.replaceChildren();
        const filters = [];
        if (state.search) filters.push(`Search: ${state.search}`);
        const category = state.categories.find(item => item.id === state.categoryId);
        if (category) filters.push(`Category: ${category.name || category.code}`);
        const location = state.locations.find(item => item.id === state.stateId);
        if (location) filters.push(`State: ${location.name}`);
        filters.forEach(text => {
            const chip = document.createElement("span");
            chip.className = "filter-chip";
            chip.textContent = text;
            activeFilters.appendChild(chip);
        });
    }

    function renderServices() {
        const section = createCatalogueSection();
        section.replaceChildren();
        const heading = document.createElement("div");
        heading.className = "live-catalogue-heading";
        const title = document.createElement("h2");
        title.textContent = state.demo ? "Available scheme information" : "Published services";
        const count = document.createElement("p");
        count.textContent = state.services.length
            ? `${state.services.length} result${state.services.length === 1 ? "" : "s"} · page ${state.page} of ${state.pages}`
            : state.demo
                ? "AI-researched information — pending human verification. Confirm details on the official page."
                : "Only currently published services are shown.";
        heading.append(title, count);
        section.appendChild(heading);

        if (!state.services.length) {
            const empty = document.createElement("div");
            empty.className = "live-catalogue-empty";
            empty.setAttribute("role", "status");
            const emptyTitle = document.createElement("h3");
            const filtered = Boolean(state.search || state.categoryId || state.stateId || state.jurisdictionCode || (state.level && state.level !== "all"));
            emptyTitle.textContent = filtered
                ? "No matching schemes in this view"
                : "No published services available";
            const detail = document.createElement("p");
            detail.textContent = state.level === "state"
                ? "No state or Union Territory scheme is recorded for this selection. GovNexus does not invent schemes to fill a state. Choose Central schemes or another jurisdiction."
                : filtered
                    ? "Try another search, category, or jurisdiction. Only records with a source link are shown."
                    : "Services will appear after their information and sources have been reviewed and published.";
            empty.append(emptyTitle, detail);
            section.appendChild(empty);
        } else {
            const grid = document.createElement("div");
            grid.className = "live-catalogue-grid";
            state.services.forEach(service => {
                const card = document.createElement("article");
                card.className = "live-service-card";
                const cardContent = document.createElement("div");
                cardContent.className = "live-service-card-content";
                const badge = document.createElement("span");
                badge.className = "status-pill";
                const level = String(service.level || service.jurisdiction_code || "").toLowerCase();
                if (level === "central" || level === "in") badge.textContent = "Central scheme";
                else if (level === "state" || service.jurisdiction) badge.textContent = service.jurisdiction || "State scheme";
                else badge.textContent = service.demo ? "Pending verification" : "Published";
                cardContent.appendChild(badge);
                const name = document.createElement("h3");
                name.textContent = service.title || service.code;
                const description = document.createElement("p");
                description.textContent = service.description || "";
                cardContent.append(name);
                if (description.textContent) cardContent.appendChild(description);
                const link = document.createElement("a");
                link.href = `service-detail.html?id=${encodeURIComponent(service.id)}`;
                link.textContent = "View details";
                card.append(cardContent, link);
                grid.appendChild(card);
            });
            section.appendChild(grid);
        }

        if (state.pages > 1) {
            const pagination = document.createElement("div");
            pagination.className = "live-catalogue-pagination";
            const previous = document.createElement("button");
            previous.type = "button";
            previous.textContent = "Previous";
            previous.disabled = state.page <= 1;
            previous.addEventListener("click", () => {
                state.page -= 1;
                loadServices();
            });
            const next = document.createElement("button");
            next.type = "button";
            next.textContent = "Next";
            next.disabled = state.page >= state.pages;
            next.addEventListener("click", () => {
                state.page += 1;
                loadServices();
            });
            pagination.append(previous, next);
            section.appendChild(pagination);
        }
        window.GovNexusI18n?.apply();
    }

    async function loadServices() {
        const requestId = ++state.requestId;
        state.search = searchInput.value.trim();
        if (state.search.length > 150) {
            showError("Search text must be 150 characters or fewer.");
            return;
        }
        const params = new URLSearchParams({
            language: state.language,
            page: String(state.page),
            limit: "20"
        });
        if (state.search) params.set("search", state.search);
        if (state.categoryId) params.set("category_id", state.categoryId);
        if (state.stateId) params.set("state_id", state.stateId);
        if (state.jurisdictionCode) params.set("jurisdiction_code", state.jurisdictionCode);
        if (state.level && state.level !== "all") params.set("level", state.level);
        const section = createCatalogueSection();
        section.setAttribute("aria-busy", "true");
        try {
            const useDemoFirst = Boolean(state.jurisdictionCode) || (state.level && state.level !== "all");
            let result = { items: [], pagination: { page: 1, pages: 1, total: 0 } };
            if (!useDemoFirst) {
                result = await api.get(`/services?${params}`);
            }
            if (requestId !== state.requestId) return;
            state.demo = false;
            state.services = Array.isArray(result.items) ? result.items : [];
            if (!state.services.length) {
                const demoResult = await api.get(`/demo/services?${params}`);
                if (requestId !== state.requestId) return;
                state.demo = true;
                state.services = Array.isArray(demoResult.items) ? demoResult.items : [];
                result.pagination = demoResult.pagination;
            }
            state.page = Number(result.pagination?.page) || 1;
            state.pages = Number(result.pagination?.pages) || 1;
            const total = result.pagination?.total || 0;
            const noun = total === 1 ? "service" : "services";
            resultsCount.textContent = state.demo
                ? `${total} ${noun} with available scheme information`
                : `${total} published ${noun}`;
            emptyState.hidden = true;
            renderActiveFilters();
            renderServices();
        } catch (error) {
            if (requestId === state.requestId) showError(error.message);
        } finally {
            if (requestId === state.requestId) {
                section.setAttribute("aria-busy", "false");
                clearButton.style.display = state.search ? "block" : "none";
            }
        }
    }

    function scheduleLoad() {
        window.clearTimeout(state.timer);
        state.page = 1;
        state.timer = window.setTimeout(loadServices, 250);
    }

    searchInput.addEventListener("input", scheduleLoad);
    searchButton.addEventListener("click", event => {
        event.preventDefault();
        window.clearTimeout(state.timer);
        state.page = 1;
        loadServices();
    });
    searchInput.addEventListener("keydown", event => {
        if (event.key === "Enter") {
            event.preventDefault();
            window.clearTimeout(state.timer);
            state.page = 1;
            loadServices();
        }
    });
    clearButton.addEventListener("click", () => {
        searchInput.value = "";
        state.search = "";
        state.page = 1;
        loadServices();
        searchInput.focus();
    });
    document.querySelectorAll(".popular-searches button").forEach(button => {
        button.addEventListener("click", () => {
            searchInput.value = button.dataset.query || "";
            state.page = 1;
            loadServices();
        });
    });
    stateFilter.addEventListener("change", () => {
        const option = stateFilter.selectedOptions[0];
        const code = option?.dataset.code || "";
        if (!option || option.value === "all") {
            state.stateId = "";
            state.jurisdictionCode = "";
        } else if (code) {
            state.stateId = "";
            state.jurisdictionCode = code;
        } else {
            state.stateId = option.value;
            state.jurisdictionCode = "";
        }
        state.page = 1;
        loadServices();
    });
    $("levelFilter").addEventListener("change", () => {
        state.level = $("levelFilter").value || "all";
        state.page = 1;
        loadServices();
    });
    $("jurisdictionSearch").addEventListener("input", () => {
        const query = $("jurisdictionSearch").value.trim().toLowerCase();
        [...stateFilter.options].forEach(option => {
            option.hidden = option.value !== "all" && query && !option.textContent.toLowerCase().includes(query);
        });
    });
    $("sortSelect").addEventListener("change", () => {
        const direction = $("sortSelect").value;
        state.services.sort((left, right) => {
            const comparison = (left.title || left.code).localeCompare(right.title || right.code);
            return direction === "za" ? -comparison : comparison;
        });
        renderServices();
    });
    $("resetFilters").addEventListener("click", () => {
        searchInput.value = "";
        state.search = "";
        state.categoryId = "";
        state.stateId = "";
        state.jurisdictionCode = "";
        state.level = "all";
        state.page = 1;
        stateFilter.value = "all";
        $("levelFilter").value = "all";
        $("jurisdictionSearch").value = "";
        syncCategoryFilters();
        loadServices();
    });
    $("emptyReset").addEventListener("click", () => $("resetFilters").click());
    $("mobileMenu").addEventListener("click", () => {
        document.querySelector(".main-nav").classList.toggle("open");
    });

    async function initialise() {
        searchInput.value = state.search;
        categoryGrid.replaceChildren();
        categoryGrid.hidden = true;
        try {
            const [categories, locations] = await Promise.all([
                getAllPages("/categories?language=en&active_only=true"),
                getAllPages("/locations?location_type=state%2Cunion_territory&language=en&active_only=true")
            ]);
            state.categories = categories;
            const jurisdictionResponse = await api.get("/demo/jurisdictions");
            const catalogueLocations = locations.filter(item =>
                item.location_type === "state" || item.location_type === "union_territory"
            );
            const byName = new Map(
                catalogueLocations.map(item => [String(item.name || "").toLowerCase(), item])
            );
            state.locations = (jurisdictionResponse.items || []).map(item => {
                const existing = byName.get(item.name.toLowerCase());
                return existing
                    ? { ...existing, code: existing.code || item.code }
                    : { id: item.code, code: item.code, name: item.name, location_type: item.type, useCode: true };
            });
            renderCategories();

            state.locations.forEach(location => {
                const option = document.createElement("option");
                option.value = location.useCode ? location.code : location.id;
                option.textContent = location.name || location.code;
                if (location.useCode) option.dataset.code = location.code;
                else if (location.code) option.dataset.catalogueCode = location.code;
                stateFilter.appendChild(option);
            });
            const params = new URLSearchParams(window.location.search);
            const requestedCategory = params.get("category") || "";
            const match = state.categories.find(item =>
                item.id === requestedCategory ||
                item.code.toLowerCase() === requestedCategory.toLowerCase()
            );
            state.categoryId = match?.id || "";
            syncCategoryFilters();

            if (await api.isAuthenticated("citizen")) {
                try {
                    const profile = await api.get("/users/me", "citizen");
                    state.language = profile.preferred_language_code || "en";
                } catch (error) {
                    showError(`Could not load your language preference: ${error.message}`);
                    return;
                }
            }
            await loadServices();
            window.GovNexusI18n?.apply();
        } catch (error) {
            showError(error.message);
        }
    }

    initialise();
});
