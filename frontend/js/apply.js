(() => {
  const root = document.getElementById("applyRoot");
  const api = window.SchemeSathiAPI;
  const params = new URLSearchParams(window.location.search);
  const schemeId = params.get("scheme") || params.get("id") || "";
  const stages = ["understand", "eligibility", "documents", "form", "answers", "review", "apply", "after"];
  let packet = null;
  let draft = loadDraft();

  function t(text) {
    return window.GovNexusI18n?.t?.(text) || text;
  }

  function confirmText(text) {
    return window.GovNexusI18n?.t?.(text) || text;
  }

  function storageKey() {
    return `govnexus_guidance_draft_v1_${schemeId}`;
  }

  function loadDraft() {
    try {
      return JSON.parse(localStorage.getItem(storageKey()) || "null");
    } catch {
      return null;
    }
  }

  function saveDraft(next) {
    draft = next;
    localStorage.setItem(storageKey(), JSON.stringify(next));
  }

  function emptyDraft() {
    return {
      stage: "understand",
      answers: {},
      eligibility: {},
      documents: {},
      question: 0,
      visited: [],
      updatedAt: new Date().toISOString(),
    };
  }

  function stageIndex(id) {
    return stages.indexOf(id);
  }

  function available(id) {
    return packet.stages.find(stage => stage.id === id)?.available !== false;
  }

  function render() {
    if (!packet) return;
    const stage = stages.includes(draft.stage) ? draft.stage : "understand";
    root.replaceChildren();
    const summary = document.createElement("section");
    summary.className = "scheme-summary";
    const title = document.createElement("h1");
    title.textContent = packet.title;
    const journey = document.createElement("p");
    journey.className = "journey-links";
    [
      ["View scheme details", `service-detail.html?id=${encodeURIComponent(packet.scheme_id)}`],
      ["Ask GovNexus AI", `assistant.html?scheme=${encodeURIComponent(packet.scheme_id)}&stage=${encodeURIComponent(draft.stage || "understand")}`],
    ].forEach(([label, href]) => {
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.textContent = t(label);
      journey.appendChild(anchor);
    });
    const status = document.createElement("p");
    status.className = "verification";
    status.textContent = packet.verification_label || t("AI-researched information — pending human verification.");
    const notice = document.createElement("p");
    notice.textContent = packet.draft_notice;
    summary.append(title, status, notice, journey);
    root.append(summary, stepper(stage), panel(stage));
    window.GovNexusI18n?.apply();
  }

  function stepper(current) {
    const nav = document.createElement("nav");
    nav.className = "stepper";
    nav.setAttribute("aria-label", "Application guidance");
    packet.stages.forEach(stage => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = t(stage.label);
      button.disabled = stage.available === false && stage.id !== "understand" && stage.id !== "review";
      if (!stage.available && stage.id !== "understand" && stage.id !== "review") button.classList.add("unavailable");
      if ((draft.visited || []).includes(stage.id) && stage.id !== current && stage.available !== false) button.classList.add("done");
      if (stage.id === current) button.setAttribute("aria-current", "step");
      button.addEventListener("click", () => {
        if (button.disabled) return;
        draft.stage = stage.id;
        saveDraft(draft);
        render();
      });
      nav.appendChild(button);
    });
    return nav;
  }

  function actions(stage) {
    const bar = document.createElement("div");
    bar.className = "stage-actions";
    const index = stageIndex(stage);
    if (index > 0) {
      const back = document.createElement("button");
      back.type = "button";
      back.className = "secondary";
      back.textContent = t("Back");
      back.addEventListener("click", () => move(-1));
      bar.appendChild(back);
    }
    if (index < stages.length - 1) {
      const next = document.createElement("button");
      next.type = "button";
      next.textContent = t("Save and continue");
      next.addEventListener("click", () => move(1));
      bar.appendChild(next);
    }
    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "secondary";
    clear.textContent = t("Clear draft");
    clear.addEventListener("click", () => {
      if (!window.confirm(confirmText("Clear this draft? This cannot be undone."))) return;
      localStorage.removeItem(storageKey());
      draft = emptyDraft();
      render();
    });
    bar.appendChild(clear);
    return bar;
  }

  function move(direction) {
    let index = stageIndex(draft.stage) + direction;
    while (index >= 0 && index < stages.length && !available(stages[index]) && stages[index] !== "review") {
      index += direction;
    }
    if (index < 0 || index >= stages.length) return;
    if (!draft.visited) draft.visited = [];
    if (!draft.visited.includes(draft.stage) && available(draft.stage)) draft.visited.push(draft.stage);
    draft.stage = stages[index];
    saveDraft(draft);
    render();
  }

  function panel(stage) {
    const section = document.createElement("section");
    section.className = "stage-panel";
    const heading = document.createElement("h2");
    const label = packet.stages.find(item => item.id === stage)?.label || stage;
    heading.textContent = t(label);
    section.appendChild(heading);
    const stageHelp = packet.stages.find(item => item.id === stage)?.explanation;
    if (stageHelp) section.append(paragraph(t(stageHelp)));
    if (!available(stage) && stage !== "review") {
      section.append(paragraph(packet.unavailable_message));
      section.appendChild(actions(stage));
      return section;
    }
    if (stage === "understand") renderUnderstand(section);
    if (stage === "eligibility") renderEligibility(section);
    if (stage === "documents") renderDocuments(section);
    if (stage === "form") renderForm(section);
    if (stage === "answers") renderAnswers(section);
    if (stage === "review") renderReview(section);
    if (stage === "apply") renderPortal(section);
    if (stage === "after") renderAfter(section);
    section.appendChild(actions(stage));
    return section;
  }

  function paragraph(text) {
    const node = document.createElement("p");
    node.textContent = text;
    return node;
  }

  function renderUnderstand(section) {
    section.append(paragraph("This guidance uses the stored scheme record. It is not an approval and GovNexus does not submit the application."));
    if (packet.description) {
      const about = document.createElement("article");
      about.append(heading3("What the source says"), paragraph(packet.description));
      section.appendChild(about);
    }
    const facts = document.createElement("dl");
    facts.className = "fact-list";
    [
      ["Category", packet.category],
      ["Jurisdiction", packet.jurisdiction],
      ["Official application destination", packet.official_application_url],
    ].forEach(([label, value]) => {
      if (!value) return;
      const term = document.createElement("dt");
      term.textContent = t(label);
      const detail = document.createElement("dd");
      detail.textContent = value;
      facts.append(term, detail);
    });
    if (facts.childNodes.length) section.appendChild(facts);
    (packet.benefits || []).forEach(item => {
      const benefit = document.createElement("article");
      benefit.append(heading3("Documented benefit"), paragraph(item.description || packet.unavailable_message));
      if (item.source_url?.startsWith("https://")) benefit.appendChild(link(item.source_url, "Official source"));
      section.appendChild(benefit);
    });
    (packet.steps || []).forEach(step => {
      const item = document.createElement("article");
      const title = document.createElement("h3");
      title.textContent = `${step.step_number || ""}. ${step.title || "Application step"}`.trim();
      item.append(title, paragraph(step.instructions || packet.unavailable_message));
      if (step.official_url?.startsWith("https://")) item.appendChild(link(step.official_url, "Official source"));
      section.appendChild(item);
    });
    if (!packet.steps?.length) section.append(paragraph(packet.unavailable_message));
  }

  function statusLabel(status) {
    if (status === "appears_satisfied") return t("Appears satisfied");
    if (status === "not_satisfied") return t("Does not appear satisfied");
    return t("Cannot determine");
  }

  function renderEligibility(section) {
    section.append(paragraph("Compare your situation with the documented conditions. This is not a government decision."));
    const items = packet.eligibility || [];
    const index = Math.min(draft.question || 0, Math.max(items.length - 1, 0));
    const item = items[index];
    if (!item) {
      section.append(paragraph(packet.unavailable_message));
      return;
    }
    const field = document.createElement("fieldset");
    const legend = document.createElement("legend");
    legend.textContent = `${index + 1} of ${items.length}. ${item.prompt || item.description}`;
    field.append(legend);
    if (item.description) field.append(paragraph(`${t("Official wording")}: ${item.description}`));
    if (item.why && item.why !== item.description) field.append(paragraph(`${t("What this means")}: ${item.why}`));
    ["yes", "no", "unknown"].forEach(value => {
      const label = document.createElement("label");
      label.className = "choice";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "eligibility-current";
      input.value = value;
      input.checked = draft.eligibility[index] === value;
      input.addEventListener("change", () => {
        draft.eligibility[index] = value;
        saveDraft(draft);
        render();
      });
      label.append(input, document.createTextNode(value === "yes" ? ` ${t("Yes")}` : value === "no" ? ` ${t("No")}` : ` ${t("I don't know")}`));
      field.appendChild(label);
    });
    section.appendChild(field);
    const nav = document.createElement("div");
    nav.className = "stage-actions";
    if (index > 0) nav.appendChild(questionButton("Previous question", -1));
    if (index < items.length - 1) nav.appendChild(questionButton("Next question", 1));
    section.appendChild(nav);
    section.appendChild(assessmentList(items));
  }

  function questionButton(label, direction) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = t(label);
    button.addEventListener("click", () => {
      draft.question = (draft.question || 0) + direction;
      saveDraft(draft);
      render();
    });
    return button;
  }

  function assessmentList(items) {
    const list = document.createElement("div");
    list.className = "review-list";
    items.forEach((item, index) => {
      const answer = draft.eligibility[index];
      const expected = item.expected;
      let status = "cannot_determine";
      if (answer === "yes" || answer === "no") {
        status = expected && answer === expected ? "appears_satisfied" : expected ? "not_satisfied" : "cannot_determine";
      }
      const row = document.createElement("p");
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "secondary";
      edit.textContent = t("Edit");
      edit.addEventListener("click", () => {
        draft.question = index;
        saveDraft(draft);
        render();
      });
      row.append(`${item.prompt || item.description}: ${statusLabel(status)}`, edit);
      list.appendChild(row);
    });
    return list;
  }

  function renderDocuments(section) {
    const guidance = packet.document_guidance || {};
    const confirmed = guidance.confirmed || [];
    const useful = guidance.commonly_useful || [];
    if (guidance.message) section.append(paragraph(t(guidance.message)));
    if (guidance.aadhaar_note) section.append(paragraph(t(guidance.aadhaar_note)));
    if (guidance.progress_note) section.append(paragraph(t(guidance.progress_note)));
    const rows = confirmed.map(item => ({ ...item, group: "confirmed" }))
      .concat(useful.map(item => ({ ...item, group: "useful" })));
    if (!rows.length) {
      section.append(paragraph(t(packet.document_unavailable_message || packet.unavailable_message)));
      return;
    }
    if (useful.length) section.append(heading3(guidance.section_title || "Commonly useful documents — confirm before applying."));
    const counts = { available: 0, obtain: 0, confirm: 0, not_applicable: 0 };
    rows.forEach((item, index) => {
      const name = item.name || "Document";
      const row = document.createElement("article");
      row.append(heading3(name));
      if (item.why) row.append(paragraph(item.why));
      const requirement = item.requirement === "mandatory"
        ? "Required in the stored record"
        : item.requirement === "conditional"
          ? "Conditional in the stored record"
          : item.confirmed
            ? "Named in the stored record"
            : "Preparation suggestion — confirm before applying";
      row.append(paragraph(t(requirement)));
      if (Array.isArray(item.alternatives) && item.alternatives.length) {
        row.append(paragraph(`${t("Accepted alternatives")}: ${item.alternatives.join(", ")}`));
      }
      if (item.source_url?.startsWith("https://")) row.appendChild(link(item.source_url, "Official source"));
      const select = document.createElement("select");
      select.setAttribute("aria-label", `Status for ${name}`);
      const options = [
        ["available", "Available"],
        ["obtain", "Need to obtain"],
        ["not_applicable", "Not applicable"],
        ["confirm", "Need to confirm"]
      ];
      options.forEach(([value, label]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = t(label);
        select.appendChild(option);
      });
      select.value = ["available", "obtain", "not_applicable", "confirm"].includes(draft.documents[index])
        ? draft.documents[index]
        : "confirm";
      select.addEventListener("change", () => {
        draft.documents[index] = select.value;
        saveDraft(draft);
        render();
      });
      counts[select.value] = (counts[select.value] || 0) + 1;
      row.appendChild(select);
      const ask = document.createElement("a");
      ask.href = `assistant.html?scheme=${encodeURIComponent(packet.scheme_id)}&stage=documents`;
      ask.textContent = t("Ask about this document");
      row.appendChild(ask);
      section.appendChild(row);
    });
    section.append(paragraph(`${counts.available || 0} marked available. ${counts.obtain || 0} still to obtain. ${counts.confirm || 0} need confirmation. ${counts.not_applicable || 0} marked not applicable.`));
  }

  function renderForm(section) {
    if (packet.portal_only_fields?.length) {
      packet.portal_only_fields.forEach(field => {
        section.append(paragraph(`${field.official_label}: ${field.instruction}`));
      });
    }
    if (!packet.form_fields?.length && !packet.portal_only_fields?.length) {
      section.append(paragraph("Field-by-field assistance is not currently available for this scheme."));
      section.append(paragraph(packet.unavailable_message));
      if (packet.official_application_url) section.appendChild(link(packet.official_application_url, "Open official application portal"));
    }
    packet.form_fields.forEach(field => {
      section.append(paragraph(`${field.official_label} — ${field.required_status}`));
      if (field.explanation) section.append(paragraph(field.explanation));
    });
  }

  function renderAnswers(section) {
    section.append(paragraph("Only non-sensitive fields listed by the stored form can be drafted here."));
    packet.form_fields.forEach(field => {
      const label = document.createElement("label");
      label.textContent = field.official_label;
      const input = document.createElement("input");
      input.value = draft.answers[field.field_key] || "";
      input.addEventListener("change", () => {
        const next = input.value.trim();
        if (/\b(aadhaar|aadhar|pan|otp|password)\b/i.test(`${field.official_label} ${next}`)) {
          input.value = "";
          section.querySelector(".error")?.remove();
          const error = paragraph("GovNexus does not collect Aadhaar, PAN, bank details, OTPs, or passwords.");
          error.className = "error";
          section.appendChild(error);
          return;
        }
        draft.answers[field.field_key] = next;
        saveDraft(draft);
      });
      label.appendChild(input);
      section.appendChild(label);
    });
  }

  function renderReview(section) {
    section.append(paragraph(`${t("Scheme")}: ${packet.title}`));
    const missing = [];
    (packet.eligibility || []).forEach((item, index) => {
      const answer = draft.eligibility[index];
      let status = "cannot_determine";
      if (answer === "yes" || answer === "no") {
        status = item.expected && answer === item.expected ? "appears_satisfied" : item.expected ? "not_satisfied" : "cannot_determine";
      }
      section.append(paragraph(`${item.prompt || item.description}: ${statusLabel(status)}`));
      if (status !== "appears_satisfied") missing.push(item.prompt || "Eligibility condition");
    });
    const guidanceRows = [
      ...(packet.document_guidance?.confirmed || []),
      ...(packet.document_guidance?.commonly_useful || [])
    ];
    if (!guidanceRows.length) missing.push("Document list");
    else guidanceRows.forEach((item, index) => {
      const state = draft.documents[index] || "confirm";
      section.append(paragraph(`${item.name || "Document"}: ${state}`));
      if (state !== "available" && state !== "not_applicable") missing.push(item.name || "Document");
    });
    Object.entries(draft.answers || {}).forEach(([key, value]) => {
      if (value) section.append(paragraph(`${key}: ${value}`));
    });
    (packet.portal_only_fields || []).forEach(field => {
      section.append(paragraph(`${field.official_label}: ${field.instruction}`));
    });
    if (!packet.form_fields.length) missing.push("Form-field guide");
    if (packet.official_application_url) section.append(paragraph(packet.official_application_url));
    const box = document.createElement("div");
    box.className = "warning";
    box.append(paragraph(missing.length ? "Needs confirmation" : "Review complete"));
    missing.forEach(item => box.append(paragraph(item)));
    box.append(paragraph("The official authority decides eligibility and approval. This draft has not been submitted. This is not an approval score."));
    section.appendChild(box);
  }

  function heading3(text) {
    const node = document.createElement("h3");
    node.textContent = t(text);
    return node;
  }

  function renderPortal(section) {
    section.append(paragraph("You are leaving GovNexus. Enter sensitive information on the official portal, review the application, and submit it yourself. GovNexus has not submitted an application."));
    if (packet.official_application_url) {
      const anchor = link(packet.official_application_url, "Open official application portal");
      anchor.classList.add("portal-link");
      section.appendChild(anchor);
    } else {
      section.append(paragraph(packet.unavailable_message));
    }
  }

  function renderAfter(section) {
    const after = packet.post_submission;
    if (!after) {
      section.append(paragraph(t("Keep the application reference number if the official portal gives you one, and check the status on that portal. A processing time or approval date is not available from the stored record.")));
      return;
    }
    if (after.timing_available === false) {
      section.append(paragraph(t("A processing time or approval date is not available from the stored record.")));
    }
    if (after.acknowledgement) section.append(paragraph(after.acknowledgement));
    if (after.status_url?.startsWith("https://")) section.appendChild(link(after.status_url, "Check status on the official portal"));
  }

  function link(url, label) {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
    anchor.textContent = t(label);
    return anchor;
  }

  async function start() {
    if (!schemeId) {
      root.textContent = "Choose a scheme before starting application guidance.";
      return;
    }
    try {
      packet = await api.get(`/guidance/schemes/${encodeURIComponent(schemeId)}`);
      if (!draft || draft.scheme && draft.scheme !== schemeId) draft = emptyDraft();
      if (!draft) draft = emptyDraft();
      draft.eligibility = draft.eligibility || {};
      draft.documents = draft.documents || {};
      draft.answers = draft.answers || {};
      draft.visited = draft.visited || [];
      draft.question = draft.question || 0;
      document.title = `${packet.title} | Help me apply`;
      render();
    } catch (error) {
      root.textContent = error.message || "Application guidance is not available for this scheme.";
    }
  }

  if (!draft) draft = emptyDraft();
  start();
})();
