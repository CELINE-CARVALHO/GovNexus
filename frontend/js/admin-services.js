(() => {
    "use strict";

    const STORAGE_KEY = "schemesathi_admin_services_v1";
    const $ = id => document.getElementById(id);

    const form = $("serviceForm");
    const modal = $("serviceModal");
    const tableBody = $("serviceTableBody");

    let services = loadServices();

    function loadServices() {
        try {
            const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
            return Array.isArray(parsed) ? parsed : [];
        } catch {
            return [];
        }
    }

    function persist() {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(services));
    }

    function escapeHTML(value = "") {
        return String(value).replace(/[&<>"']/g, char => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;",
            '"': "&quot;", "'": "&#39;"
        })[char]);
    }

    function statusLabel(status) {
        return ({
            draft: "Draft",
            in_review: "In review",
            published: "Published · preview",
            archived: "Archived"
        })[status] || "Draft";
    }

    function render() {
        const query = $("serviceSearch").value.trim().toLowerCase();
        const category = $("categoryFilter").value;
        const status = $("statusFilter").value;

        $("totalServices").textContent = services.length;
        $("draftServices").textContent = services.filter(s => s.status === "draft").length;
        $("reviewServices").textContent = services.filter(s => s.status === "in_review").length;
        $("publishedServices").textContent = services.filter(s => s.status === "published").length;

        const filtered = services.filter(service => {
            const searchText = [
                service.name, service.code, service.department,
                service.jurisdiction, service.description
            ].join(" ").toLowerCase();

            return searchText.includes(query) &&
                (category === "all" || service.category === category) &&
                (status === "all" || service.status === status);
        });

        $("serviceResultCount").textContent =
            `${filtered.length} RECORD${filtered.length === 1 ? "" : "S"}`;

        $("serviceEmpty").style.display = filtered.length ? "none" : "block";

        tableBody.innerHTML = filtered.map(service => `
            <tr>
                <td>
                    <span class="service-name">${escapeHTML(service.name)}</span>
                    <span class="service-code">${escapeHTML(service.code)}</span>
                </td>
                <td><span class="category-pill">${escapeHTML(service.category)}</span></td>
                <td><span class="service-department">${escapeHTML(service.department)}</span></td>
                <td><span class="service-jurisdiction">${escapeHTML(service.jurisdiction)}</span></td>
                <td><span class="publication-status ${escapeHTML(service.status)}">${escapeHTML(statusLabel(service.status))}</span></td>
                <td>
                    <div class="catalog-row-actions">
                        <button type="button" data-edit="${escapeHTML(service.id)}">Edit</button>
                        <button type="button" class="delete" data-delete="${escapeHTML(service.id)}">Delete</button>
                    </div>
                </td>
            </tr>
        `).join("");
    }

    function notify(message) {
        const toast = $("catalogToast");
        toast.textContent = message;
        toast.classList.add("show");
        clearTimeout(notify.timer);
        notify.timer = setTimeout(() => toast.classList.remove("show"), 2700);
    }

    function openModal(service = null) {
        form.reset();
        $("serviceId").value = service?.id || "";
        $("serviceModalTitle").textContent = service ? "Edit service record" : "Add service record";

        if (service) {
            $("serviceName").value = service.name || "";
            $("serviceCode").value = service.code || "";
            $("serviceCategory").value = service.category || "";
            $("departmentName").value = service.department || "";
            $("serviceJurisdiction").value = service.jurisdiction || "";
            $("serviceStatus").value = service.status || "draft";
            $("serviceDescription").value = service.description || "";
            $("serviceSourceUrl").value = service.sourceUrl || "";
        }

        modal.classList.add("open");
        $("serviceName").focus();
    }

    function closeModal() {
        modal.classList.remove("open");
    }

    $("addServiceBtn").addEventListener("click", () => openModal());
    $("closeServiceModal").addEventListener("click", closeModal);
    $("cancelServiceModal").addEventListener("click", closeModal);

    modal.addEventListener("click", event => {
        if (event.target === modal) closeModal();
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape") closeModal();
    });

    ["serviceSearch", "categoryFilter", "statusFilter"].forEach(id => {
        $(id).addEventListener(id === "serviceSearch" ? "input" : "change", render);
    });

    form.addEventListener("submit", event => {
        event.preventDefault();

        const id = $("serviceId").value;
        const code = $("serviceCode").value.trim().toUpperCase();
        const existing = services.find(service => service.id === id);

        const duplicateCode = services.some(service =>
            service.code.toLowerCase() === code.toLowerCase() && service.id !== id
        );

        if (duplicateCode) {
            notify("That service code is already registered.");
            $("serviceCode").focus();
            return;
        }

        const sourceUrl = $("serviceSourceUrl").value.trim();

        if (sourceUrl) {
            try {
                const parsed = new URL(sourceUrl);
                if (parsed.protocol !== "https:") {
                    notify("Use an HTTPS official source URL.");
                    return;
                }
            } catch {
                notify("Enter a valid source URL.");
                return;
            }
        }

        const record = {
            id: id || (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`),
            name: $("serviceName").value.trim(),
            code,
            category: $("serviceCategory").value,
            department: $("departmentName").value.trim(),
            jurisdiction: $("serviceJurisdiction").value,
            status: $("serviceStatus").value,
            description: $("serviceDescription").value.trim(),
            sourceUrl,
            createdAt: existing?.createdAt || new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };

        if (!record.name || !record.code || !record.category ||
            !record.department || !record.jurisdiction) {
            notify("Complete all required fields.");
            return;
        }

        if (existing) {
            services = services.map(service => service.id === id ? record : service);
            notify("Service record updated.");
        } else {
            services.unshift(record);
            notify("Service record created as a local preview.");
        }

        persist();
        render();
        closeModal();
    });

    tableBody.addEventListener("click", event => {
        const editButton = event.target.closest("[data-edit]");
        const deleteButton = event.target.closest("[data-delete]");

        if (editButton) {
            const service = services.find(item => item.id === editButton.dataset.edit);
            if (service) openModal(service);
        }

        if (deleteButton) {
            const id = deleteButton.dataset.delete;
            const service = services.find(item => item.id === id);
            if (!service) return;

            if (confirm(`Delete "${service.name}" from the local preview catalogue?`)) {
                services = services.filter(item => item.id !== id);
                persist();
                render();
                notify("Service removed from preview catalogue.");
            }
        }
    });

    $("exportServicesBtn").addEventListener("click", () => {
        if (!services.length) {
            notify("There are no service records to export.");
            return;
        }

        const columns = [
            "name", "code", "category", "department",
            "jurisdiction", "status", "description", "sourceUrl", "createdAt"
        ];

        const cell = value => `"${String(value ?? "").replace(/"/g, '""')}"`;

        const csv = [
            columns.join(","),
            ...services.map(service =>
                columns.map(key => cell(service[key])).join(",")
            )
        ].join("\r\n");

        const blob = new Blob(["\uFEFF" + csv], {
            type: "text/csv;charset=utf-8"
        });

        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = "schemesathi-service-catalogue.csv";
        anchor.click();
        URL.revokeObjectURL(url);

        notify("Service catalogue CSV exported.");
    });

    render();
})();
