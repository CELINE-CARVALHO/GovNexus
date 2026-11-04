(() => {
    "use strict";

    const API_BASE = "http://127.0.0.1:8000/api/v1";

    const state = {
        categories: [],
        services: [],
        search: "",
        category: new URLSearchParams(window.location.search).get("category") || ""
    };

    const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);

    async function apiGet(path) {
        const response = await fetch(`${API_BASE}${path}`);

        if (!response.ok) {
            throw new Error(`API request failed (${response.status})`);
        }

        return response.json();
    }

    function createCatalogueSection() {
        let section = document.getElementById("liveCatalogue");

        if (section) return section;

        section = document.createElement("section");
        section.id = "liveCatalogue";
        section.className = "live-catalogue-section";

        const categoryGrid = document.getElementById("categoryGrid");

        if (categoryGrid) {
            categoryGrid.insertAdjacentElement("afterend", section);
        } else {
            document.querySelector("main")?.appendChild(section);
        }

        if (!section.isConnected) {
            document.body.appendChild(section);
        }

        return section;
    }

    function renderCategories() {
        const grid = document.getElementById("categoryGrid");
        if (!grid) return;

        const existingCards = grid.querySelectorAll(".category-card");

        existingCards.forEach((card) => {
            const code = card.dataset.category;
            const category = state.categories.find(item => item.code === code);

            if (category) {
                card.dataset.categoryId = category.id;
                card.dataset.title = category.name || code;
            }
        });

        // Keep existing cards and their visual design intact.
    }

    function getFilteredServices() {
        return state.services.filter(service => {
            const matchesSearch = !state.search || [
                service.title,
                service.description,
                service.code
            ].some(value => String(value || "")
                .toLowerCase()
                .includes(state.search));

            const matchesCategory = !state.category ||
                service.category_id === state.category ||
                service.category_code === state.category;

            return matchesSearch && matchesCategory;
        });
    }

    function renderServices() {
        const section = createCatalogueSection();
        const services = getFilteredServices();

        if (!section) return;

        if (state.services.length === 0) {
            section.innerHTML = `
                <div class="live-catalogue-heading">
                    <h2>Available government services</h2>
                    <p>Our catalogue is being populated with verified government information.</p>
                </div>
                <div class="live-catalogue-empty" role="status">
                    <h3>No published services yet</h3>
                    <p>Categories are available. Government services will appear here after their information and sources have been reviewed and published.</p>
                </div>
            `;
            return;
        }

        if (services.length === 0) {
            section.innerHTML = `
                <div class="live-catalogue-heading">
                    <h2>Available government services</h2>
                </div>
                <div class="live-catalogue-empty" role="status">
                    <h3>No matching services</h3>
                    <p>Try another search term or category.</p>
                </div>
            `;
            return;
        }

        section.innerHTML = `
            <div class="live-catalogue-heading">
                <h2>Available government services</h2>
                <p>${services.length} published service${services.length === 1 ? "" : "s"}</p>
            </div>
            <div class="live-catalogue-grid">
                ${services.map(service => `
                    <article class="live-service-card">
                        <div class="live-service-card-content">
                            <h3>${escapeHTML(service.title || service.code)}</h3>
                            <p>${escapeHTML(service.description || "View verified service information and application guidance.")}</p>
                        </div>
                        <a href="service-detail.html?id=${encodeURIComponent(service.id)}">
                            View details
                        </a>
                    </article>
                `).join("")}
            </div>
        `;
    }

    function bindSearch() {
        const searchInput = document.getElementById("serviceSearch");

        if (searchInput) {
            searchInput.addEventListener("input", () => {
                state.search = searchInput.value.trim().toLowerCase();
                renderServices();
            });
        }

        const searchButton = document.getElementById("searchButton");

        if (searchButton) {
            searchButton.addEventListener("click", (event) => {
                event.preventDefault();
                state.search = (searchInput?.value || "").trim().toLowerCase();
                renderServices();
            });
        }

        const clearButton = document.getElementById("clearSearch");

        if (clearButton) {
            clearButton.addEventListener("click", () => {
                if (searchInput) searchInput.value = "";
                state.search = "";
                renderServices();
            });
        }

        document.querySelectorAll('input[name="category"]').forEach(input => {
            input.addEventListener("change", () => {
                state.category = input.checked ? input.value : "";
                renderServices();
            });
        });

        document.querySelectorAll(".category-card").forEach(card => {
            card.addEventListener("click", () => {
                const code = card.dataset.category;
                if (!code) return;

                state.category = code;
                const matchingCategory = state.categories.find(item => item.code === code);

                if (matchingCategory) {
                    state.category = matchingCategory.id;
                }

                renderServices();
            });
        });
    }

    async function initialise() {
        createCatalogueSection();

        try {
            const [categoryResponse, serviceResponse] = await Promise.all([
                apiGet("/categories?language=en&active_only=true&limit=100"),
                apiGet("/services?language=en&active_only=true&limit=100")
            ]);

            state.categories = categoryResponse.items || [];
            state.services = serviceResponse.items || [];

            renderCategories();
            bindSearch();
            renderServices();

            console.info("SchemeSathi live catalogue connected.", {
                categories: state.categories.length,
                services: state.services.length
            });
        } catch (error) {
            console.error("SchemeSathi catalogue connection failed:", error);

            const section = createCatalogueSection();

            if (section) {
                section.innerHTML = `
                    <div class="live-catalogue-empty" role="alert">
                        <h3>Catalogue temporarily unavailable</h3>
                        <p>We could not connect to the services server. Please refresh the page after checking that the backend is running.</p>
                    </div>
                `;
            }
        }
    }

    document.addEventListener("DOMContentLoaded", initialise);
})();
