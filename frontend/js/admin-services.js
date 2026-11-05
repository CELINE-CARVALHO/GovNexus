document.addEventListener("DOMContentLoaded", async () => {
    const api = window.SchemeSathiAPI;
    const $ = id => document.getElementById(id);
    const pageSize = 20;
    const state = {
        services: [],
        departments: [],
        categories: [],
        languages: [],
        page: 1,
        total: 0,
        currentService: null,
        versions: []
    };

    function notify(message) {
        const toast = $("catalogToast");
        toast.textContent = message;
        toast.classList.add("show");
        window.clearTimeout(notify.timer);
        notify.timer = window.setTimeout(() => toast.classList.remove("show"), 3200);
    }

    async function getAllPages(path, limit = 100) {
        const items = [];
        let page = 1;
        let pages = 1;
        do {
            const separator = path.includes("?") ? "&" : "?";
            const result = await api.get(`${path}${separator}page=${page}&limit=${limit}`);
            items.push(...(Array.isArray(result.items) ? result.items : []));
            pages = Number(result.pagination?.pages) || 1;
            page += 1;
        } while (page <= pages);
        return items;
    }

    function fillSelect(select, items, placeholder) {
        select.replaceChildren(new Option(placeholder, ""));
        items.forEach(item => {
            const option = new Option(
                item.name ? `${item.name} (${item.code})` : item.code,
                item.id || item.code
            );
            select.appendChild(option);
        });
    }

    function filteredServices() {
        const query = $("serviceSearch").value.trim().toLowerCase();
        const filter = $("statusFilter").value;
        return state.services.filter(service => {
            const statusMatches = filter === "all" ||
                (filter === "active" && service.is_active) ||
                (filter === "inactive" && !service.is_active && service.status !== "archived") ||
                (filter === "archived" && service.status === "archived");
            return statusMatches &&
                `${service.code} ${service.slug} ${service.status}`.toLowerCase().includes(query);
        });
    }

    function render() {
        const filtered = filteredServices();
        const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
        if (state.page > pageCount) state.page = pageCount;
        const start = (state.page - 1) * pageSize;
        const visible = filtered.slice(start, start + pageSize);
        const body = $("serviceTableBody");
        body.replaceChildren();

        visible.forEach(service => {
            const row = document.createElement("tr");
            const code = document.createElement("td");
            const codeValue = document.createElement("span");
            codeValue.className = "service-name";
            codeValue.textContent = service.code;
            const id = document.createElement("span");
            id.className = "service-code";
            id.textContent = service.id;
            code.append(codeValue, id);

            const slug = document.createElement("td");
            slug.textContent = service.slug || "—";
            const status = document.createElement("td");
            const statusLabel = document.createElement("span");
            statusLabel.className = `publication-status ${service.status}`;
            statusLabel.textContent = service.status || "Unspecified";
            status.appendChild(statusLabel);
            const active = document.createElement("td");
            active.textContent = service.is_active ? "Active" : "Inactive";
            const versions = document.createElement("td");
            const manageVersions = document.createElement("button");
            manageVersions.type = "button";
            manageVersions.className = "row-action";
            manageVersions.dataset.versions = service.id;
            manageVersions.textContent = "Manage";
            versions.appendChild(manageVersions);

            const actions = document.createElement("td");
            const toggle = document.createElement("button");
            toggle.type = "button";
            toggle.className = "row-action";
            toggle.dataset.toggle = service.id;
            toggle.textContent = service.is_active ? "Deactivate" : "Activate";
            const archive = document.createElement("button");
            archive.type = "button";
            archive.className = "row-action delete";
            archive.dataset.archive = service.id;
            archive.textContent = "Archive";
            actions.append(toggle);
            if (service.status !== "archived") actions.appendChild(archive);
            row.append(code, slug, status, active, versions, actions);
            body.appendChild(row);
        });

        $("totalServices").textContent = state.total;
        $("draftServices").textContent = state.services.filter(item => item.is_active).length;
        $("reviewServices").textContent = state.services.filter(item => !item.is_active).length;
        $("publishedServices").textContent = visible.length;
        $("serviceResultCount").textContent = `${filtered.length} RECORD${filtered.length === 1 ? "" : "S"}`;
        $("serviceEmpty").style.display = visible.length ? "none" : "block";
        $("serviceEmpty").querySelector("strong").textContent = filtered.length
            ? "No matching services"
            : "No service records available";
        $("servicePageLabel").textContent = `Page ${state.page} of ${pageCount}`;
        $("previousServices").disabled = state.page <= 1;
        $("nextServices").disabled = state.page >= pageCount;
    }

    async function loadServices() {
        const records = [];
        let offset = 0;
        let total = 0;
        do {
            const result = await api.get(`/admin/services?active_only=false&limit=200&offset=${offset}`, "admin");
            records.push(...(Array.isArray(result.items) ? result.items : []));
            total = Number(result.total) || 0;
            offset += Number(result.limit) || 200;
        } while (offset < total);
        state.services = records;
        state.total = total;
        render();
    }

    async function loadDictionaries() {
        const [departments, categories, languages] = await Promise.all([
            getAllPages("/departments?language=en&active_only=true"),
            getAllPages("/categories?language=en&active_only=true"),
            api.get("/languages?active_only=true")
        ]);
        state.departments = departments;
        state.categories = categories;
        state.languages = Array.isArray(languages.items) ? languages.items : [];
        fillSelect($("departmentName"), departments, "Select a department");
        fillSelect($("serviceCategory"), categories, "Select a category");
        const languageItems = state.languages.map(item => ({
            ...item,
            name: item.native_name ? `${item.native_name} — ${item.english_name}` : item.english_name
        }));
        fillSelect($("serviceLanguage"), languageItems, "Select a language");
        fillSelect($("translationLanguage"), languageItems, "Select a language");
    }

    function openCreateForm() {
        $("serviceForm").reset();
        $("serviceId").value = "";
        $("serviceModal").classList.add("open");
        $("serviceCode").focus();
    }

    function closeCreateForm() {
        $("serviceModal").classList.remove("open");
    }

    function showFactLinks(version, items) {
        const list = $("versionList");
        list.replaceChildren();
        const heading = document.createElement("p");
        heading.className = "version-form-note";
        heading.textContent = `Verified facts linked to version ${version.version_number}: ${items.length}`;
        list.appendChild(heading);
        if (!items.length) {
            const empty = document.createElement("p");
            empty.className = "version-form-note";
            empty.textContent = "No facts are linked to this version yet.";
            list.appendChild(empty);
        }
        items.forEach(item => {
            const row = document.createElement("div");
            row.className = "version-row";
            const text = document.createElement("span");
            text.textContent = `${item.fact_type} · ${item.relationship_type} · ${item.source_fact_id}`;
            row.appendChild(text);
            if (version.publication_status !== "published") {
                const remove = document.createElement("button");
                remove.type = "button";
                remove.className = "row-action delete";
                remove.dataset.unlink = item.link_id;
                remove.dataset.version = version.id;
                remove.textContent = "Unlink";
                row.appendChild(remove);
            }
            list.appendChild(row);
        });
    }

    function renderVersions() {
        const list = $("versionList");
        list.replaceChildren();
        if (!state.versions.length) {
            const empty = document.createElement("p");
            empty.className = "version-form-note";
            empty.textContent = "No versions have been created for this service.";
            list.appendChild(empty);
        }
        state.versions.forEach(version => {
            const row = document.createElement("div");
            row.className = "version-row";
            const summary = document.createElement("span");
            summary.textContent =
                `Version ${version.version_number} · ${version.publication_status} · effective ${version.effective_from || "date not set"}`;
            const actions = document.createElement("div");
            actions.className = "version-actions";
            const facts = document.createElement("button");
            facts.type = "button";
            facts.dataset.facts = version.id;
            facts.textContent = "View linked facts";
            actions.appendChild(facts);
            if (version.publication_status !== "published") {
                const translation = document.createElement("button");
                translation.type = "button";
                translation.dataset.translation = version.id;
                translation.textContent = "Add / update translation";
                const link = document.createElement("button");
                link.type = "button";
                link.dataset.link = version.id;
                link.textContent = "Link verified fact";
                const publish = document.createElement("button");
                publish.type = "button";
                publish.dataset.publish = version.id;
                publish.textContent = "Publish";
                actions.append(translation, link, publish);
            }
            row.append(summary, actions);
            list.appendChild(row);
        });
    }

    async function loadVersions() {
        const result = await api.get(
            `/services/${encodeURIComponent(state.currentService.id)}/versions`,
            "admin"
        );
        state.versions = Array.isArray(result.items) ? result.items : [];
        renderVersions();
    }

    async function openVersions(service) {
        state.currentService = service;
        $("versionsTitle").textContent = `Versions · ${service.code}`;
        $("versionForm").hidden = true;
        $("translationForm").hidden = true;
        $("factLinkForm").hidden = true;
        $("versionsModal").classList.add("open");
        try {
            await loadVersions();
        } catch (error) {
            notify(`Could not load service versions: ${error.message}`);
        }
    }

    async function openFactLinkForm(versionId) {
        const form = $("factLinkForm");
        form.reset();
        $("factVersionId").value = versionId;
        $("linkableFact").replaceChildren(new Option("Loading verified facts…", ""));
        form.hidden = false;
        try {
            const result = await api.get(
                `/services/${encodeURIComponent(state.currentService.id)}/versions/${encodeURIComponent(versionId)}/linkable-facts`,
                "admin"
            );
            const items = Array.isArray(result.items) ? result.items : [];
            const options = items.map(fact => ({
                id: fact.id,
                code: `${fact.fact_type} · ${fact.fact_key} · ${JSON.stringify(fact.value_data)}`
            }));
            fillSelect($("linkableFact"), options, items.length ? "Select a verified fact" : "No verified facts available");
            if (!items.length) notify("There are no unlinked verified facts available.");
        } catch (error) {
            notify(`Could not load verified facts: ${error.message}`);
        }
    }

    $("addServiceBtn").addEventListener("click", openCreateForm);
    $("closeServiceModal").addEventListener("click", closeCreateForm);
    $("cancelServiceModal").addEventListener("click", closeCreateForm);
    $("serviceModal").addEventListener("click", event => {
        if (event.target === $("serviceModal")) closeCreateForm();
    });
    $("closeVersionsModal").addEventListener("click", () => $("versionsModal").classList.remove("open"));
    $("versionsModal").addEventListener("click", event => {
        if (event.target === $("versionsModal")) $("versionsModal").classList.remove("open");
    });
    $("openVersionForm").addEventListener("click", () => {
        $("versionForm").reset();
        $("versionEffectiveFrom").value = new Date().toISOString().slice(0, 10);
        $("versionForm").hidden = false;
        $("translationForm").hidden = true;
        $("factLinkForm").hidden = true;
    });
    $("serviceSearch").addEventListener("input", () => {
        state.page = 1;
        render();
    });
    $("statusFilter").addEventListener("change", () => {
        state.page = 1;
        render();
    });
    $("previousServices").addEventListener("click", () => {
        if (state.page > 1) {
            state.page -= 1;
            render();
        }
    });
    $("nextServices").addEventListener("click", () => {
        state.page += 1;
        render();
    });

    $("serviceForm").addEventListener("submit", async event => {
        event.preventDefault();
        const submit = $("serviceForm").querySelector('[type="submit"]');
        submit.disabled = true;
        let createdService = null;
        try {
            createdService = await api.post("/services", {
                code: $("serviceCode").value.trim(),
                slug: $("serviceSlug").value.trim(),
                department_id: $("departmentName").value,
                category_id: $("serviceCategory").value
            }, "admin");
            const versionResult = await api.post(`/services/${encodeURIComponent(createdService.id)}/versions`, {
                effective_from: $("effectiveFrom").value,
                effective_to: $("effectiveTo").value || null,
                change_summary: $("versionSummary").value.trim() || null
            }, "admin");
            await api.put(
                `/services/${encodeURIComponent(createdService.id)}/versions/${encodeURIComponent(versionResult.version.id)}/translations`,
                {
                    language_code: $("serviceLanguage").value,
                    title: $("serviceName").value.trim(),
                    description: $("serviceDescription").value.trim() || null,
                    application_url: $("applicationUrl").value.trim() || null
                },
                "admin"
            );
            closeCreateForm();
            await loadServices();
            notify("Service and initial draft version created. Link verified facts before publishing.");
        } catch (error) {
            if (createdService?.id) {
                closeCreateForm();
                try {
                    await loadServices();
                } catch (refreshError) {
                    notify(`Service ${createdService.id} was created, but a later draft request or refresh failed: ${error.message}; ${refreshError.message}`);
                    return;
                }
                notify(`Service ${createdService.id} was created, but its initial version or translation could not be completed: ${error.message}`);
            } else {
                notify(`Service could not be created: ${error.message}`);
            }
        } finally {
            submit.disabled = false;
        }
    });

    $("versionForm").addEventListener("submit", async event => {
        event.preventDefault();
        const button = $("versionForm").querySelector('[type="submit"]');
        button.disabled = true;
        try {
            await api.post(`/services/${encodeURIComponent(state.currentService.id)}/versions`, {
                effective_from: $("versionEffectiveFrom").value,
                effective_to: $("versionEffectiveTo").value || null,
                change_summary: $("versionChangeSummary").value.trim() || null
            }, "admin");
            $("versionForm").hidden = true;
            await loadVersions();
            notify("Draft version created.");
        } catch (error) {
            notify(`Draft version could not be created: ${error.message}`);
        } finally {
            button.disabled = false;
        }
    });

    $("translationForm").addEventListener("submit", async event => {
        event.preventDefault();
        const versionId = $("translationVersionId").value;
        const button = $("translationForm").querySelector('[type="submit"]');
        button.disabled = true;
        try {
            await api.put(
                `/services/${encodeURIComponent(state.currentService.id)}/versions/${encodeURIComponent(versionId)}/translations`,
                {
                    language_code: $("translationLanguage").value,
                    title: $("translationTitle").value.trim(),
                    description: $("translationDescription").value.trim() || null,
                    application_url: $("translationApplicationUrl").value.trim() || null
                },
                "admin"
            );
            $("translationForm").hidden = true;
            notify("Draft translation saved.");
        } catch (error) {
            notify(`Translation could not be saved: ${error.message}`);
        } finally {
            button.disabled = false;
        }
    });

    $("factLinkForm").addEventListener("submit", async event => {
        event.preventDefault();
        const versionId = $("factVersionId").value;
        const button = $("factLinkForm").querySelector('[type="submit"]');
        button.disabled = true;
        try {
            await api.post(
                `/services/${encodeURIComponent(state.currentService.id)}/versions/${encodeURIComponent(versionId)}/facts`,
                {
                    source_fact_id: $("linkableFact").value,
                    relationship_type: $("factRelationship").value
                },
                "admin"
            );
            $("factLinkForm").hidden = true;
            await loadVersions();
            notify("Verified fact linked to the draft version.");
        } catch (error) {
            notify(`Fact could not be linked: ${error.message}`);
        } finally {
            button.disabled = false;
        }
    });

    $("versionList").addEventListener("click", async event => {
        const button = event.target.closest("button");
        if (!button) return;
        const version = state.versions.find(item =>
            item.id === button.dataset.translation ||
            item.id === button.dataset.link ||
            item.id === button.dataset.publish ||
            item.id === button.dataset.facts
        );
        if (button.dataset.translation) {
            $("translationForm").reset();
            $("translationVersionId").value = version.id;
            $("translationForm").hidden = false;
            $("factLinkForm").hidden = true;
            return;
        }
        if (button.dataset.link) {
            $("translationForm").hidden = true;
            await openFactLinkForm(button.dataset.link);
            return;
        }
        if (button.dataset.facts) {
            try {
                const result = await api.get(
                    `/services/${encodeURIComponent(state.currentService.id)}/versions/${encodeURIComponent(button.dataset.facts)}/facts`,
                    "admin"
                );
                showFactLinks(version, Array.isArray(result.items) ? result.items : []);
            } catch (error) {
                notify(`Could not load linked facts: ${error.message}`);
            }
            return;
        }
        if (button.dataset.publish) {
            if (!window.confirm(`Publish version ${version.version_number}? Published versions cannot be edited.`)) return;
            button.disabled = true;
            try {
                await api.post(
                    `/services/${encodeURIComponent(state.currentService.id)}/versions/${encodeURIComponent(version.id)}/publish`,
                    undefined,
                    "admin"
                );
                await loadVersions();
                notify("Service version published.");
            } catch (error) {
                notify(`Version could not be published: ${error.message}`);
            } finally {
                button.disabled = false;
            }
        }
    });

    $("versionList").addEventListener("click", async event => {
        const button = event.target.closest("[data-unlink]");
        if (!button || !window.confirm("Unlink this fact from the draft? The source fact itself will not be deleted.")) return;
        button.disabled = true;
        try {
            await api.delete(
                `/services/${encodeURIComponent(state.currentService.id)}/versions/${encodeURIComponent(button.dataset.version)}/facts/${encodeURIComponent(button.dataset.unlink)}`,
                "admin"
            );
            await loadVersions();
            notify("Fact unlinked from the service version.");
        } catch (error) {
            notify(`Fact could not be unlinked: ${error.message}`);
        } finally {
            button.disabled = false;
        }
    });

    $("serviceTableBody").addEventListener("click", async event => {
        const button = event.target.closest("button");
        if (!button) return;
        const service = state.services.find(item =>
            item.id === button.dataset.versions ||
            item.id === button.dataset.toggle ||
            item.id === button.dataset.archive
        );
        if (!service) return;
        if (button.dataset.versions) {
            await openVersions(service);
            return;
        }
        const archive = Boolean(button.dataset.archive);
        const nextStatus = archive ? "archived" : service.is_active ? "inactive" : "active";
        const nextActive = nextStatus === "active";
        if (!window.confirm(`Set ${service.code} to ${nextStatus}?`)) return;
        button.disabled = true;
        try {
            await api.patch(`/services/${encodeURIComponent(service.id)}`, {
                status: nextStatus,
                is_active: nextActive
            }, "admin");
            await loadServices();
            notify(`Service status updated to ${nextStatus}.`);
        } catch (error) {
            notify(`Service status could not be updated: ${error.message}`);
        } finally {
            button.disabled = false;
        }
    });

    $("exportServicesBtn").addEventListener("click", () => {
        const columns = ["id", "code", "slug", "status", "is_active"];
        const records = filteredServices().slice((state.page - 1) * pageSize, state.page * pageSize);
        if (!records.length) {
            notify("There are no service records on this page to export.");
            return;
        }
        const csvCell = value => `"${String(value ?? "").replace(/"/g, '""')}"`;
        const csv = [
            columns.join(","),
            ...records.map(item => columns.map(key => csvCell(item[key])).join(","))
        ].join("\r\n");
        const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = "schemesathi-admin-services.csv";
        anchor.click();
        URL.revokeObjectURL(url);
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            closeCreateForm();
            $("versionsModal").classList.remove("open");
        }
    });

    try {
        await Promise.all([loadDictionaries(), loadServices()]);
    } catch (error) {
        notify(`Service administration data could not be loaded: ${error.message}`);
        $("serviceEmpty").style.display = "block";
        $("serviceEmpty").querySelector("strong").textContent = "Service data unavailable";
        $("serviceEmpty").appendChild(document.createTextNode(error.message));
        $("addServiceBtn").disabled = true;
        $("exportServicesBtn").disabled = true;
    }
});
