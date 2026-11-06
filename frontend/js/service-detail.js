document.addEventListener("DOMContentLoaded", async () => {
    const api = window.SchemeSathiAPI;
    const $ = id => document.getElementById(id);
    const params = new URLSearchParams(window.location.search);
    const serviceId = params.get("id");
    const languageFallback = "en";
    let service = null;
    let isDemoRecord = false;
    let toastTimer;

    function notify(message) {
        const toast = $("toast");
        toast.textContent = message;
        toast.classList.add("show");
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => toast.classList.remove("show"), 2800);
    }

    function element(tag, text, className) {
        const node = document.createElement(tag);
        if (text !== undefined && text !== null) node.textContent = String(text);
        if (className) node.className = className;
        return node;
    }

    function setEmpty(sectionId, message) {
        const section = $(sectionId);
        const intro = section.querySelector(".section-intro");
        if (!intro) return;
        intro.textContent = message;
        intro.setAttribute("role", "status");
        section.querySelectorAll(
            ".overview-grid, .data-placeholder, .locked-panel, .document-empty, .process-empty, .source-status"
        ).forEach(node => node.remove());
    }

    function renderEvidenceList(container, evidence) {
        container.replaceChildren();
        if (!Array.isArray(evidence) || !evidence.length) {
            container.appendChild(element("div", "No verified evidence is available for this information."));
            return;
        }
        evidence.forEach(item => {
            const article = element("article", undefined, "evidence-item");
            article.append(element("strong", item.fact_type || item.fact_key || "Verified fact"));
            const value = element("pre", JSON.stringify(item.value ?? {}, null, 2));
            article.appendChild(value);
            container.appendChild(article);
        });
    }

    function officialLink(url, label) {
        return safeOfficialLink(url, label);
    }

    function renderBenefits(data) {
        const benefits = Array.isArray(data.benefits) ? data.benefits : [];
        const overview = $("overview");
        const existing = overview.querySelector(".benefit-list");
        if (existing) existing.remove();
        if (!benefits.length) return;
        const list = element("div", undefined, "benefit-list");
        list.append(element("h3", "Documented benefits"));
        benefits.forEach(item => {
            const row = element("article", undefined, "locked-panel");
            row.append(element("p", item.description || ""));
            if (item.source_url) {
                const link = officialLink(item.source_url, "Official source");
                if (link) row.appendChild(link);
            }
            if (item.retrieved_on) row.append(element("p", `Retrieved on ${item.retrieved_on}`));
            list.appendChild(row);
        });
        overview.appendChild(list);
    }

    function mountEligibilityChecker(data) {
        const section = $("eligibility");
        section.querySelector(".eligibility-checker")?.remove();
        const items = (data.eligibility || []).filter(item => item && item.prompt && item.input === "yes_no" && item.expected);
        const box = element("div", undefined, "eligibility-checker");
        const source = data.evidence?.items?.[0]?.source?.url || data.service?.application_url;
        if (!items.length) {
            box.append(
                element("strong", "Eligibility could not be confirmed from a structured condition in this record."),
                element("p", "I couldn't confirm a checkable eligibility rule from the stored government source. Review the official page before you apply.")
            );
            const link = source ? officialLink(source, "Open the official source") : null;
            if (link) box.appendChild(link);
            section.appendChild(box);
            return;
        }
        box.append(element("h3", "Check the documented conditions"));
        box.append(element("p", "GovNexus asks only for the conditions stored with this scheme. It does not ask for Aadhaar, PAN, bank account, OTP, or password. This is not an approval."));
        const form = document.createElement("form");
        items.forEach((item, index) => {
            const field = element("fieldset");
            field.append(element("legend", item.prompt));
            field.append(element("p", `Why this is asked: ${item.why || item.description || "The stored source lists this condition."}`));
            ["yes", "no", "unknown"].forEach(value => {
                const label = document.createElement("label");
                const input = document.createElement("input");
                input.type = "radio";
                input.name = `condition-${index}`;
                input.value = value;
                input.required = true;
                label.append(input, document.createTextNode(value === "yes" ? " Yes" : value === "no" ? " No" : " I don't know"));
                field.appendChild(label);
            });
            form.appendChild(field);
        });
        const result = element("div", undefined, "eligibility-result");
        result.setAttribute("role", "status");
        const button = document.createElement("button");
        button.type = "submit";
        button.className = "primary-btn";
        button.textContent = "Check these conditions";
        form.appendChild(button);
        form.addEventListener("submit", event => {
            event.preventDefault();
            const failed = [];
            const met = [];
            const unknown = [];
            items.forEach((item, index) => {
                const selected = form.querySelector(`input[name="condition-${index}"]:checked`)?.value;
                if (selected === "unknown" || !selected) unknown.push(item);
                else if (selected === item.expected) met.push(item);
                else failed.push(item);
            });
            result.replaceChildren();
            if (failed.length) {
                result.append(element("strong", "You may not qualify based on a condition you reported."));
                failed.forEach(item => result.append(element("p", item.description)));
                result.append(element("p", "Additional verification may be required. This is not a government decision."));
            } else if (unknown.length) {
                result.append(element("strong", "Eligibility could not be confirmed."));
                result.append(element("p", "Some listed conditions were not answered. You may be eligible only if those conditions are also met."));
            } else {
                result.append(element("strong", "You appear to meet the listed conditions."));
                result.append(element("p", "You may be eligible. Additional verification may be required. GovNexus cannot approve an application or guarantee a benefit."));
            }
            if (met.length) result.append(element("p", `${met.length} listed condition${met.length === 1 ? "" : "s"} appear satisfied from your answers.`));
            const link = source ? officialLink(source, "Official scheme source") : null;
            if (link) result.appendChild(link);
        });
        box.append(form, result);
        section.appendChild(box);
    }

    function mountDocumentChecklist(data) {
        const section = $("documents");
        section.querySelector(".document-checklist")?.remove();
        const documents = Array.isArray(data.required_documents) ? data.required_documents : [];
        const box = element("div", undefined, "document-checklist");
        const source = data.evidence?.items?.[0]?.source?.url || data.service?.application_url;
        if (!documents.length) {
            box.append(
                element("strong", "No documented requirements are stored for this scheme."),
                element("p", "I couldn't confirm the document list from a reliable government source in this record. Do not upload identity documents here.")
            );
            const link = source ? officialLink(source, "Check the official source") : null;
            if (link) box.appendChild(link);
            section.appendChild(box);
            return;
        }
        const storageKey = `govnexus_documents_${data.service?.id || "scheme"}`;
        let saved = {};
        try { saved = JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch { saved = {}; }
        const progress = element("p");
        const missing = element("div");
        function persist() {
            const state = {};
            box.querySelectorAll("select[data-doc]").forEach(select => { state[select.dataset.doc] = select.value; });
            try { localStorage.setItem(storageKey, JSON.stringify(state)); } catch { /* private mode */ }
            const values = Object.values(state);
            const available = values.filter(value => value === "available").length;
            progress.textContent = `${available} of ${documents.length} marked available.`;
            missing.replaceChildren();
            documents.forEach(item => {
                const name = item.name || item.document_code || "Document";
                if ((state[name] || "pending") !== "available") missing.append(element("p", `Still to prepare: ${name}`));
            });
        }
        documents.forEach(item => {
            const name = item.name || item.document_code || "Document";
            const row = element("article", undefined, "document-empty");
            row.append(element("strong", name));
            if (item.description) row.append(element("p", item.description));
            row.append(element("p", `Why it is listed: ${item.why || item.description || "The stored source names this document."}`));
            const status = item.is_mandatory === false ? "Optional in the stored record" : "Required in the stored record";
            const extras = [status];
            if (item.copies_required != null) extras.push(`Copies: ${item.copies_required}`);
            if (Array.isArray(item.accepted_formats) && item.accepted_formats.length) extras.push(`Accepted format: ${item.accepted_formats.join(", ")}`);
            if (item.stage) extras.push(`Stage: ${item.stage}`);
            row.append(element("p", extras.join(" · ")));
            if (item.source_url) {
                const link = officialLink(item.source_url, "Official source");
                if (link) row.appendChild(link);
            }
            const select = document.createElement("select");
            select.dataset.doc = name;
            select.setAttribute("aria-label", `Status for ${name}`);
            [["pending", "Pending"], ["available", "Available"]].forEach(([value, label]) => {
                const option = document.createElement("option");
                option.value = value;
                option.textContent = label;
                select.appendChild(option);
            });
            select.value = saved[name] === "available" ? "available" : "pending";
            select.addEventListener("change", persist);
            row.appendChild(select);
            box.appendChild(row);
        });
        box.append(progress, missing);
        section.appendChild(box);
        persist();
    }

    function renderService(data) {
        service = data.service;
        isDemoRecord = Boolean(data.demo);
        document.title = `${service.title || service.code} | GovNexus`;
        $("categoryTag").textContent = service.category?.name || service.category?.code || "PUBLISHED SERVICE";
        $("serviceTitle").textContent = service.title || service.code;
        $("serviceDescription").textContent =
            service.description || "No published service description is available.";

        const previewTag = document.querySelector(".preview-tag");
        if (previewTag) previewTag.textContent = data.demo ? "PENDING VERIFICATION" : "PUBLISHED VERSION";
        const meta = document.querySelector(".hero-meta");
        meta.replaceChildren();
        const jurisdictions = Array.isArray(data.jurisdictions)
            ? data.jurisdictions.map(item => item.location?.name).filter(Boolean)
            : [];
        meta.append(
            element("span", `Jurisdiction: ${jurisdictions.length ? jurisdictions.join(", ") : "not available"}`),
            element("span", `Version ${data.version?.number ?? "—"}`),
            element("span", `Effective from: ${data.version?.effective_from || "not provided"}`)
        );
        const notice = document.querySelector(".notice-bar p");
        if (notice) {
            notice.replaceChildren(
                element("strong", "Information status: "),
                document.createTextNode(data.disclaimer || "Only published service information is shown.")
            );
        }

        const overview = $("overview");
        overview.querySelector(".section-intro").textContent =
            service.description || "The published service record does not include a description.";
        let overviewGrid = overview.querySelector(".overview-grid");
        if (!overviewGrid) {
            overviewGrid = element("div", undefined, "overview-grid");
            overview.querySelector(".section-intro").insertAdjacentElement("afterend", overviewGrid);
        }
        overviewGrid.replaceChildren();
        const department = element("article", undefined, "info-tile");
        department.append(element("strong", service.department?.name || service.department?.code || "Department unavailable"));
        department.append(element("p", service.department?.website_url || "No department website was provided."));
        const category = element("article", undefined, "info-tile");
        category.append(element("strong", service.category?.name || service.category?.code || "Category unavailable"));
        category.append(element("p", String(service.code || "").replace(/^DEMO-/i, "")));
        const publication = element("article", undefined, "info-tile");
        publication.append(element("strong", `Published version ${data.version?.number ?? "—"}`));
        publication.append(element("p", data.version?.change_summary || "No change summary was provided."));
        overviewGrid.append(department, category, publication);
        if (service.application_url) {
            const application = element("article", undefined, "info-tile");
            application.append(element("strong", "Official application channel"));
            const link = safeOfficialLink(service.application_url, "Open application channel");
            if (link) {
                application.appendChild(link);
            } else {
                application.append(element("p", service.application_url));
            }
            overviewGrid.appendChild(application);
        }
        const overviewEvidence = element("div", undefined, "data-placeholder");
        const evidenceTitle = element("strong", "Verified evidence");
        const evidenceContent = element("div");
        const relevantEvidence = (data.evidence?.items || []).filter(item =>
            ["fee", "deadline", "contact_information", "location", "general_information"].includes(item.relationship_type)
        );
        renderEvidenceList(evidenceContent, relevantEvidence);
        overviewEvidence.append(evidenceTitle, evidenceContent);
        const oldEvidence = overview.querySelector(".data-placeholder");
        if (oldEvidence) oldEvidence.replaceWith(overviewEvidence);
        else overview.appendChild(overviewEvidence);

        renderListSection(
            "eligibility",
            data.eligibility,
            item => {
                const row = element("article", undefined, "locked-panel");
                row.append(element("strong", item.description || "Published eligibility condition"));
                row.append(element("span", item.is_mandatory ? "Mandatory" : "Optional", "status-pill"));
                return row;
            },
            "No verified eligibility information is available for this published version."
        );
        renderListSection(
            "documents",
            data.required_documents,
            item => {
                const row = element("article", undefined, "document-empty");
                row.append(element("strong", item.name || item.document_code || "Document"));
                if (item.description) row.append(element("p", item.description));
                const details = [];
                if (item.is_mandatory !== undefined) details.push(item.is_mandatory ? "Mandatory" : "Optional");
                if (item.copies_required !== null && item.copies_required !== undefined) {
                    details.push(`Copies: ${item.copies_required}`);
                }
                if (Array.isArray(item.accepted_formats) && item.accepted_formats.length) {
                    details.push(`Accepted formats: ${item.accepted_formats.join(", ")}`);
                }
                if (details.length) row.append(element("p", details.join(" · ")));
                return row;
            },
            "No verified document requirements are available for this published version."
        );
        renderListSection(
            "process",
            data.application_steps,
            item => {
                const row = element("article", undefined, "process-step");
                row.append(element("span", String(item.step_number || "")));
                const details = element("div");
                details.append(element("strong", item.title || "Application step"));
                if (item.instructions) details.append(element("p", item.instructions));
                if (item.official_url) {
                    const link = safeOfficialLink(item.official_url, "Open official instructions");
                    if (link) details.appendChild(link);
                }
                row.appendChild(details);
                return row;
            },
            "No verified application steps are available for this published version."
        );
        renderBenefits(data);
        mountEligibilityChecker(data);
        mountDocumentChecklist(data);

        const sourceList = $("sources");
        sourceList.querySelectorAll(".source-status, .data-placeholder").forEach(node => node.remove());
        const sources = [...new Map((data.evidence?.items || [])
            .map(item => [item.source?.url, item.source])
            .filter(([url, source]) => url && source)).values()];
        if (!sources.length) {
            sourceList.appendChild(element("div", "No verified official sources are linked to the published evidence.", "source-status"));
        } else {
            const list = element("div", undefined, "source-status");
            sources.forEach(source => {
                const row = element("div");
                row.append(element("strong", source.publisher || "Official source"));
                const link = safeOfficialLink(source.url, source.url);
                if (link) row.appendChild(link);
                row.append(element("p", `Authority status: ${source.authority_status || "not provided"}`));
                list.appendChild(row);
            });
            sourceList.appendChild(list);
        }
        document.querySelector(".verification-legend")?.setAttribute("hidden", "");
        window.GovNexusI18n?.apply();

        if (!data.demo) {
            const track = element("a", "Track this service");
            track.className = "secondary-btn";
            track.href = `applications.html?service_id=${encodeURIComponent(service.id)}`;
            document.querySelector(".hero-actions").appendChild(track);
            updateSavedState(data);
        }
    }

    function renderListSection(id, items, renderItem, emptyMessage) {
        const section = $(id);
        const intro = section.querySelector(".section-intro");
        intro.textContent = items?.length
            ? (isDemoRecord ? "AI-researched information — pending human verification." : "Information shown below comes from the current published service record.")
            : emptyMessage;
        const old = section.querySelector(".locked-panel, .document-empty, .process-empty");
        if (old) old.remove();
        if (!Array.isArray(items) || !items.length) {
            return;
        }
        const list = element("div", undefined, id === "process" ? "process-empty" : "");
        items.forEach(item => list.appendChild(renderItem(item)));
        section.appendChild(list);
    }

    function safeOfficialLink(url, label) {
        try {
            const parsed = new URL(url);
            if (parsed.protocol !== "https:") return null;
            const link = element("a", label);
            link.href = parsed.href;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            return link;
        } catch (error) {
            return null;
        }
    }

    async function updateSavedState(data) {
        const button = $("saveService");
        try {
            if (!await api.isAuthenticated("citizen")) {
                button.textContent = "♡ Save service";
                return;
            }
        } catch (error) {
            notify(error.message);
            return;
        }
        try {
            const language = data.language?.requested || languageFallback;
            const result = await api.get(
                `/users/me/saved-services?language=${encodeURIComponent(language)}`,
                "citizen"
            );
            const saved = (result.items || []).some(item => item.service_id === service.id);
            button.textContent = saved ? "♥ Saved" : "♡ Save service";
        } catch (error) {
            notify(`Could not check saved services: ${error.message}`);
        }
    }

    function askAssistant(prompt) {
        const initialPrompt = `I am exploring ${service?.title || service?.code || "a government service"}. ${prompt}`;
        try {
            sessionStorage.setItem("schemesathi_initial_prompt", initialPrompt);
            window.location.href = "assistant.html";
        } catch (error) {
            notify("Could not open the assistant prompt in this browser session.");
        }
    }

    $("saveService").addEventListener("click", async () => {
        if (!service) return;
        try {
            if (!api.requireCitizen()) return;
        } catch (error) {
            notify(error.message);
            return;
        }
        const button = $("saveService");
        button.disabled = true;
        try {
            await api.put(`/users/me/saved-services/${encodeURIComponent(service.id)}`, undefined, "citizen");
            button.textContent = "♥ Saved";
            notify("Published service saved to your account.");
        } catch (error) {
            notify(`Could not save this service: ${error.message}`);
        } finally {
            button.disabled = false;
        }
    });

    $("askAI").addEventListener("click", () =>
        askAssistant("Explain the verified information currently published for this service.")
    );
    $("openAssistant").addEventListener("click", () =>
        askAssistant("Help me understand the verified information available for this service.")
    );
    document.querySelectorAll("[data-prompt]").forEach(button => {
        button.addEventListener("click", () => askAssistant(button.dataset.prompt || ""));
    });
    document.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
            const target = document.getElementById(tab.dataset.target);
            if (!target) return;
            document.querySelectorAll(".tab").forEach(item =>
                item.classList.toggle("active", item === tab)
            );
            target.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    });
    const observer = new IntersectionObserver(entries => {
        const visible = entries.filter(entry => entry.isIntersecting)
            .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
        if (!visible) return;
        document.querySelectorAll(".tab").forEach(tab =>
            tab.classList.toggle("active", tab.dataset.target === visible.target.id)
        );
    }, { rootMargin: "-18% 0px -65% 0px", threshold: [0, .15, .4] });
    document.querySelectorAll(".detail-section").forEach(section => observer.observe(section));
    $("mobileMenu").addEventListener("click", () =>
        document.querySelector(".main-nav").classList.toggle("open")
    );

    $("serviceTitle").textContent = "Loading published service information";
    $("serviceDescription").textContent = "Retrieving the current published service record.";
    $("categoryTag").textContent = "LOADING";
    document.querySelector(".preview-tag").textContent = "LOADING";
    document.querySelector(".notice-bar p").textContent = "Loading service details and verified evidence…";
    document.querySelector(".verification-legend")?.setAttribute("hidden", "");
    ["overview", "eligibility", "documents", "process", "sources"].forEach(id =>
        setEmpty(id, "Loading published service information…")
    );
    document.querySelector(".hero-actions").querySelectorAll("button").forEach(button => {
        button.disabled = true;
    });

    if (!serviceId) {
        $("serviceTitle").textContent = "Select a published service";
        $("serviceDescription").textContent = "Choose a service from the catalogue to view its published information.";
        $("categoryTag").textContent = "NO SERVICE SELECTED";
        document.querySelector(".preview-tag").textContent = "UNAVAILABLE";
        document.querySelector(".notice-bar p").textContent =
            "Service-specific information is only available after selecting a currently published service.";
        document.querySelector(".hero-actions").replaceChildren();
        ["overview", "eligibility", "documents", "process", "sources"].forEach(id =>
            setEmpty(id, "No service was selected. Return to the catalogue and choose a published service.")
        );
        return;
    }

    try {
        let language = languageFallback;
        if (await api.isAuthenticated("citizen")) {
            try {
                const profile = await api.get("/users/me", "citizen");
                language = profile.preferred_language_code || languageFallback;
            } catch (error) {
                notify(`Could not load your preferred language: ${error.message}`);
            }
        }
        const detailPath = serviceId.startsWith("demo-")
            ? `/demo/services/${encodeURIComponent(serviceId)}`
            : `/services/${encodeURIComponent(serviceId)}/details?language=${encodeURIComponent(language)}`;
        const result = await api.get(detailPath);
        renderService(result);
        document.querySelector(".hero-actions").querySelectorAll("button").forEach(button => {
            button.disabled = false;
        });
    } catch (error) {
        $("serviceTitle").textContent = "Service details unavailable";
        $("serviceDescription").textContent = error.message;
        $("categoryTag").textContent = "UNAVAILABLE";
        document.querySelector(".preview-tag").textContent = "UNAVAILABLE";
        document.querySelector(".notice-bar p").textContent =
            "The published service record could not be retrieved. No service requirements are shown.";
        document.querySelector(".hero-actions").replaceChildren();
        ["overview", "eligibility", "documents", "process", "sources"].forEach(id =>
            setEmpty(id, "Published service information could not be loaded.")
        );
    }
});
