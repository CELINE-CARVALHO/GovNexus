document.addEventListener("DOMContentLoaded", async () => {
    const api = window.SchemeSathiAPI;
    if (!api.requireCitizen()) return;

    const $ = id => document.getElementById(id);
    const labels = {
        planning: "Planning",
        submitted_externally: "Submitted externally",
        under_review: "Under review",
        additional_information_requested: "Additional information requested",
        approved: "Approved",
        rejected: "Rejected",
        withdrawn: "Withdrawn",
        completed: "Completed"
    };
    const pageSize = 20;
    let page = 1;
    let total = 0;
    let filteredTotal = 0;
    let records = [];
    let services = [];
    let selectedId = null;
    let toastTimer;
    document.body.setAttribute("aria-busy", "true");
    $("emptyState").classList.add("visible");
    $("emptyState").querySelector("h3").textContent = "Loading application records…";
    $("emptyState").querySelector("p").textContent = "Retrieving your citizen-recorded entries.";
    $("addApplication").disabled = true;
    $("emptyAdd").disabled = true;

    function notify(message) {
        const toast = $("toast");
        toast.textContent = message;
        toast.classList.add("show");
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => toast.classList.remove("show"), 3200);
    }

    function dateLabel(value) {
        if (!value) return "—";
        const date = new Date(`${value.slice(0, 10)}T00:00:00`);
        return Number.isNaN(date.getTime())
            ? value
            : date.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
    }

    function serviceLabel(application) {
        const id = application.service_id || application.service?.id;
        const service = services.find(item => item.id === id);
        return service?.title || application.service?.code || "Published service";
    }

    function makeCell(text, className) {
        const cell = document.createElement("td");
        if (className) cell.className = className;
        cell.textContent = text;
        return cell;
    }

    function render() {
        const query = $("searchInput").value.trim().toLowerCase();
        const filter = $("statusFilter").value;
        const filtered = records.filter(record =>
            (filter === "all" || record.status === filter) &&
            [serviceLabel(record), record.reference_number, record.notes]
                .join(" ").toLowerCase().includes(query)
        );
        filteredTotal = filtered.length;
        const pageCount = Math.max(1, Math.ceil(filteredTotal / pageSize));
        if (page > pageCount) page = pageCount;
        const visible = filtered.slice((page - 1) * pageSize, page * pageSize);
        const body = $("applicationRows");
        body.replaceChildren();

        visible.forEach(record => {
            const row = document.createElement("tr");
            const nameCell = document.createElement("td");
            const name = document.createElement("strong");
            name.textContent = serviceLabel(record);
            const date = document.createElement("small");
            date.textContent = record.application_date
                ? `Application date: ${dateLabel(record.application_date)}`
                : "Citizen-recorded record";
            nameCell.append(name, date);
            const reference = makeCell(record.reference_number || "Not added", "reference");
            const statusCell = document.createElement("td");
            const status = document.createElement("span");
            status.className = `status-pill status-${record.status}`;
            status.textContent = labels[record.status] || "Unspecified";
            statusCell.appendChild(status);
            const updated = record.updated_at || record.application_date;
            const updatedCell = makeCell(dateLabel(updated || ""), "");
            const actionCell = document.createElement("td");
            const view = document.createElement("button");
            view.type = "button";
            view.className = "row-action";
            view.dataset.view = record.id;
            view.textContent = "View";
            actionCell.appendChild(view);
            row.append(nameCell, reference, statusCell, updatedCell, actionCell);
            body.appendChild(row);
        });

        const empty = $("emptyState");
        const isEmpty = filteredTotal === 0;
        empty.classList.toggle("visible", isEmpty);
        empty.querySelector("h3").textContent = records.length
            ? "No matching records"
            : "No applications to show yet";
        empty.querySelector("p").textContent = records.length
            ? "Try changing your search or status filter."
            : "Add a citizen-recorded entry for a published service to organise your tracking information.";
        empty.querySelector(".add-btn").style.display = records.length ? "none" : "inline-block";

        const start = filteredTotal ? (page - 1) * pageSize + 1 : 0;
        const end = Math.min(page * pageSize, filteredTotal);
        $("recordCount").textContent = `Showing ${start}–${end} of ${filteredTotal} matching records`;
        $("previousPage").disabled = page <= 1;
        $("nextPage").disabled = page >= pageCount;

        $("totalCount").textContent = total;
        $("progressCount").textContent = records.filter(record =>
            ["planning", "submitted_externally", "under_review"].includes(record.status)
        ).length;
        $("completedCount").textContent = records.filter(record => record.status === "completed").length;
        $("attentionCount").textContent = records.filter(record =>
            record.status === "additional_information_requested"
        ).length;
    }

    async function loadRecords() {
        const result = await api.get("/users/me/applications?page=1&limit=100", "citizen");
        records = Array.isArray(result.items) ? result.items : [];
        total = Number(result.pagination?.total) || 0;
        const pages = Number(result.pagination?.pages) || 1;
        for (let currentPage = 2; currentPage <= pages; currentPage += 1) {
            const nextPage = await api.get(
                `/users/me/applications?page=${currentPage}&limit=100`,
                "citizen"
            );
            records.push(...(Array.isArray(nextPage.items) ? nextPage.items : []));
        }
        render();
    }

    async function loadServices(profile) {
        const language = profile.preferred_language_code || "en";
        const result = await api.get(
            `/services?language=${encodeURIComponent(language)}&page=1&limit=100`
        );
        services = Array.isArray(result.items) ? result.items : [];
        const select = $("serviceId");
        select.replaceChildren();
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = services.length
            ? "Select a published service"
            : "No published services are available";
        select.appendChild(placeholder);
        services.forEach(service => {
            const option = document.createElement("option");
            option.value = service.id;
            option.textContent = service.title || service.code;
            select.appendChild(option);
        });
        const requestedServiceId = new URLSearchParams(window.location.search).get("service_id");
        if (requestedServiceId && !services.some(service => service.id === requestedServiceId)) {
            try {
                const details = await api.get(
                    `/services/${encodeURIComponent(requestedServiceId)}/details?language=${encodeURIComponent(language)}`
                );
                if (details.service?.id) {
                    services.push({
                        id: details.service.id,
                        code: details.service.code,
                        title: details.service.title
                    });
                    const option = document.createElement("option");
                    option.value = details.service.id;
                    option.textContent = details.service.title || details.service.code;
                    select.appendChild(option);
                }
            } catch (error) {
                notify(`Selected service is unavailable for tracking: ${error.message}`);
            }
        }
        if (result.pagination?.pages > 1 && !requestedServiceId) {
            const note = document.createElement("small");
            note.textContent = "Search results include the first 100 published services.";
            select.insertAdjacentElement("afterend", note);
        }
        $("addApplication").disabled = services.length === 0;
        $("emptyAdd").disabled = services.length === 0;
        render();
    }

    function openForm(record = null) {
        $("applicationForm").reset();
        $("recordId").value = record?.id || "";
        $("modalTitle").textContent = record ? "Edit application record" : "Add an application record";
        $("serviceId").value = record?.service_id || "";
        $("serviceId").disabled = Boolean(record);
        $("referenceNumber").value = record?.reference_number || "";
        $("applicationStatus").value = record?.status || "planning";
        $("applicationDate").value = record?.application_date || "";
        $("applicationNotes").value = record?.notes || "";
        $("modalBackdrop").classList.add("open");
        $("serviceId").focus();
    }

    function closeForm() {
        $("modalBackdrop").classList.remove("open");
        $("serviceId").disabled = false;
    }

    function openDetails(id) {
        const record = records.find(item => item.id === id);
        if (!record) return;
        selectedId = id;
        $("detailTitle").textContent = serviceLabel(record);
        const content = $("detailContent");
        content.replaceChildren();
        const meta = document.createElement("div");
        meta.className = "detail-meta";
        [
            ["REFERENCE NUMBER", record.reference_number || "Not added"],
            ["YOUR STATUS", labels[record.status] || "Unspecified"],
            ["APPLICATION DATE", dateLabel(record.application_date)],
            ["RECORD SOURCE", "Citizen recorded"]
        ].forEach(([label, value]) => {
            const item = document.createElement("div");
            const small = document.createElement("small");
            small.textContent = label;
            const strong = document.createElement("strong");
            strong.textContent = value;
            item.append(small, strong);
            meta.appendChild(item);
        });
        const notes = document.createElement("div");
        notes.className = "detail-notes";
        const notesTitle = document.createElement("strong");
        notesTitle.textContent = "Personal notes";
        const notesBody = document.createElement("p");
        notesBody.textContent = record.notes || "No notes added.";
        notes.append(notesTitle, notesBody);
        const disclaimer = document.createElement("p");
        disclaimer.className = "detail-disclaimer";
        disclaimer.textContent = "This is a citizen-recorded record. It does not reflect live government application status.";
        content.append(meta, notes, disclaimer);
        $("detailBackdrop").classList.add("open");
    }

    $("addApplication").addEventListener("click", () => openForm());
    $("emptyAdd").addEventListener("click", () => openForm());
    $("closeModal").addEventListener("click", closeForm);
    $("cancelModal").addEventListener("click", closeForm);
    $("closeDetail").addEventListener("click", () => $("detailBackdrop").classList.remove("open"));
    $("modalBackdrop").addEventListener("click", event => {
        if (event.target === $("modalBackdrop")) closeForm();
    });
    $("detailBackdrop").addEventListener("click", event => {
        if (event.target === $("detailBackdrop")) $("detailBackdrop").classList.remove("open");
    });

    $("applicationForm").addEventListener("submit", async event => {
        event.preventDefault();
        const serviceId = $("serviceId").value;
        const reference = $("referenceNumber").value.trim();
        const date = $("applicationDate").value || null;
        const notes = $("applicationNotes").value.trim();
        if (!serviceId && !$("recordId").value) {
            notify("Select a published service.");
            $("serviceId").focus();
            return;
        }
        if (date && date > new Date().toISOString().slice(0, 10)) {
            notify("Application date cannot be in the future.");
            return;
        }

        const submit = $("applicationForm").querySelector('[type="submit"]');
        submit.disabled = true;
        try {
            const id = $("recordId").value;
            const payload = {
                reference_number: reference || null,
                application_date: date,
                status: $("applicationStatus").value,
                notes: notes || null
            };
            if (id) {
                await api.patch(`/users/me/applications/${encodeURIComponent(id)}`, payload, "citizen");
            } else {
                await api.post("/users/me/applications", {
                    ...payload,
                    service_id: serviceId
                }, "citizen");
            }
            closeForm();
            page = 1;
            await loadRecords();
            notify(id ? "Citizen-recorded application entry updated." : "Citizen-recorded application entry added.");
        } catch (error) {
            notify(error.message);
        } finally {
            submit.disabled = false;
        }
    });

    $("applicationRows").addEventListener("click", event => {
        const button = event.target.closest("[data-view]");
        if (button) openDetails(button.dataset.view);
    });
    $("editRecord").addEventListener("click", () => {
        const record = records.find(item => item.id === selectedId);
        $("detailBackdrop").classList.remove("open");
        if (record) openForm(record);
    });
    $("deleteRecord").hidden = true;
    $("searchInput").addEventListener("input", () => {
        page = 1;
        render();
    });
    $("statusFilter").addEventListener("change", () => {
        page = 1;
        render();
    });
    $("previousPage").addEventListener("click", async () => {
        if (page <= 1) return;
        page -= 1;
        render();
    });
    $("nextPage").addEventListener("click", async () => {
        if (page * pageSize >= filteredTotal) return;
        page += 1;
        render();
    });
    $("menuBtn").addEventListener("click", () => $("sidebar").classList.toggle("open"));
    document.addEventListener("click", event => {
        if (window.innerWidth <= 760 &&
            !$("sidebar").contains(event.target) &&
            !$("menuBtn").contains(event.target)) {
            $("sidebar").classList.remove("open");
        }
    });
    document.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            closeForm();
            $("detailBackdrop").classList.remove("open");
        }
    });

    try {
        const profile = await api.get("/users/me", "citizen");
        $("topAvatar").textContent = profile.display_name?.trim()?.charAt(0)?.toUpperCase() || "S";
        await Promise.all([loadRecords(), loadServices(profile)]);
        document.body.removeAttribute("aria-busy");
        const requestedServiceId = new URLSearchParams(window.location.search).get("service_id");
        if (requestedServiceId) {
            if (services.some(service => service.id === requestedServiceId)) {
                openForm();
                $("serviceId").value = requestedServiceId;
            } else {
                notify("That published service is not available for tracking.");
            }
        }
    } catch (error) {
        document.body.removeAttribute("aria-busy");
        notify(`Application data could not be loaded: ${error.message}`);
        $("emptyState").classList.add("visible");
        $("emptyState").querySelector("h3").textContent = "Application data unavailable";
        $("emptyState").querySelector("p").textContent = error.message;
        $("addApplication").disabled = true;
    }
});
