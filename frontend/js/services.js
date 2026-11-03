document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("serviceSearch");
    const searchButton = document.getElementById("searchButton");
    const clearSearch = document.getElementById("clearSearch");
    const categoryGrid = document.getElementById("categoryGrid");
    const emptyState = document.getElementById("emptyState");
    const resultsCount = document.getElementById("resultsCount");
    const sortSelect = document.getElementById("sortSelect");
    const stateFilter = document.getElementById("stateFilter");
    const activeFilters = document.getElementById("activeFilters");
    const resetFilters = document.getElementById("resetFilters");
    const emptyReset = document.getElementById("emptyReset");
    const mobileMenu = document.getElementById("mobileMenu");
    const mainNav = document.getElementById("mainNav");

    const cards = Array.from(document.querySelectorAll(".category-card"));

    const categoryNames = {
        identity: "Identity & certificates",
        education: "Education & scholarships",
        finance: "Financial assistance",
        health: "Health & welfare",
        employment: "Employment & skills",
        business: "Business & agriculture"
    };

    function getSelectedLevel() {
        return document.querySelector('input[name="level"]:checked')?.value || "all";
    }

    function getSelectedCategories() {
        return Array.from(
            document.querySelectorAll('input[name="category"]:checked')
        ).map(input => input.value);
    }

    function updateResults() {
        const query = searchInput.value.trim().toLowerCase();
        const level = getSelectedLevel();
        const state = stateFilter.value;
        const selectedCategories = getSelectedCategories();
        const sort = sortSelect.value;

        let visibleCards = cards.filter(card => {
            const title = (card.dataset.title || "").toLowerCase();
            const category = card.dataset.category;

            const matchesSearch =
                !query ||
                title.includes(query) ||
                category.includes(query);

            const matchesCategory =
                selectedCategories.length === 0 ||
                selectedCategories.includes(category);

            return matchesSearch && matchesCategory;
        });

        // Jurisdiction filters are intentionally not applied to generic
        // category cards. Real service records will carry jurisdiction data.
        const hasUnsupportedJurisdictionFilter =
            level !== "all" || state !== "all";

        if (sort === "az") {
            visibleCards.sort((a, b) =>
                a.dataset.title.localeCompare(b.dataset.title)
            );
        } else if (sort === "za") {
            visibleCards.sort((a, b) =>
                b.dataset.title.localeCompare(a.dataset.title)
            );
        }

        cards.forEach(card => {
            card.style.display = "none";
        });

        visibleCards.forEach(card => {
            card.style.display = "flex";
            categoryGrid.appendChild(card);
        });

        const showEmpty =
            visibleCards.length === 0 || hasUnsupportedJurisdictionFilter;

        categoryGrid.hidden = showEmpty;
        emptyState.hidden = !showEmpty;

        if (hasUnsupportedJurisdictionFilter && visibleCards.length > 0) {
            resultsCount.textContent =
                "Category discovery only — jurisdiction-specific service records are not connected yet.";

            emptyState.querySelector("h3").textContent =
                "Verified jurisdiction data is not connected yet";

            emptyState.querySelector("p").textContent =
                "The state and government-level filters will become available when verified service records are added.";
        } else if (visibleCards.length === 0) {
            resultsCount.textContent = "No matching categories";
            emptyState.querySelector("h3").textContent =
                "No matching categories found";
            emptyState.querySelector("p").textContent =
                "Try another search or reset your filters.";
        } else {
            resultsCount.textContent =
                `${visibleCards.length} service categor${visibleCards.length === 1 ? "y" : "ies"} available for discovery`;
        }

        clearSearch.style.display = query ? "block" : "none";

        renderActiveFilters(query, selectedCategories, level, state);
    }

    function renderActiveFilters(query, categories, level, state) {
        activeFilters.innerHTML = "";

        const filters = [];

        if (query) filters.push(`Search: ${query}`);
        if (level !== "all") filters.push(`Level: ${level}`);
        if (state !== "all") {
            filters.push(`State: ${state.replaceAll("-", " ")}`);
        }

        categories.forEach(category => {
            filters.push(categoryNames[category] || category);
        });

        filters.forEach(filter => {
            const chip = document.createElement("span");
            chip.className = "filter-chip";
            chip.textContent = filter;
            activeFilters.appendChild(chip);
        });
    }

    function clearAllFilters() {
        searchInput.value = "";

        document.querySelectorAll('input[name="level"]').forEach(input => {
            input.checked = input.value === "all";
        });

        document.querySelectorAll('input[name="category"]').forEach(input => {
            input.checked = false;
        });

        stateFilter.value = "all";
        sortSelect.value = "featured";

        updateResults();
    }

    searchInput.addEventListener("input", updateResults);
    searchButton.addEventListener("click", updateResults);

    searchInput.addEventListener("keydown", event => {
        if (event.key === "Enter") {
            updateResults();
        }
    });

    clearSearch.addEventListener("click", () => {
        searchInput.value = "";
        updateResults();
        searchInput.focus();
    });

    document.querySelectorAll(".popular-searches button").forEach(button => {
        button.addEventListener("click", () => {
            searchInput.value = button.dataset.query;
            updateResults();
            searchInput.focus();
        });
    });

    document.querySelectorAll('input[name="level"]').forEach(input => {
        input.addEventListener("change", updateResults);
    });

    document.querySelectorAll('input[name="category"]').forEach(input => {
        input.addEventListener("change", updateResults);
    });

    stateFilter.addEventListener("change", updateResults);
    sortSelect.addEventListener("change", updateResults);

    resetFilters.addEventListener("click", clearAllFilters);
    emptyReset.addEventListener("click", clearAllFilters);

    mobileMenu.addEventListener("click", () => {
        mainNav.classList.toggle("open");
    });

    // Read search query passed from the homepage.
    const params = new URLSearchParams(window.location.search);
    const initialQuery = params.get("q");

    if (initialQuery) {
        searchInput.value = initialQuery;
    }

    updateResults();
});
