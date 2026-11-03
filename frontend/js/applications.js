(() => {
  const STORAGE_KEY = "schemesathi_application_records";
  const $ = id => document.getElementById(id);
  let records = [];
  let selectedId = null;
  let toastTimer;

  const statuses = {
    draft: "Draft",
    in_progress: "In progress",
    submitted: "Submitted",
    follow_up: "Needs follow-up",
    completed: "Completed"
  };

  const makeId = () => `app_${Date.now()}_${Math.random().toString(36).slice(2,8)}`;
  const dateLabel = value => {
    if (!value) return "—";
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"});
  };

  function loadRecords() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      records = Array.isArray(saved) ? saved.map(item => ({
        id: item.id || item.recordId || makeId(),
        name: item.name || item.serviceName || item.title || "Untitled application",
        reference: item.reference || item.referenceNumber || "",
        status: statuses[item.status] ? item.status : "in_progress",
        date: item.date || item.applicationDate || "",
        followUpDate: item.followUpDate || "",
        notes: item.notes || "",
        updatedAt: item.updatedAt || item.createdAt || ""
      })) : [];
    } catch { records = []; }
  }

  function persist() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
  }

  function notify(message) {
    $("toast").textContent = message;
    $("toast").classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $("toast").classList.remove("show"),2600);
  }

  function updateStats() {
    $("totalCount").textContent = records.length;
    $("progressCount").textContent = records.filter(r => r.status === "in_progress" || r.status === "submitted").length;
    $("completedCount").textContent = records.filter(r => r.status === "completed").length;
    $("attentionCount").textContent = records.filter(r => r.status === "follow_up").length;
  }

  function render() {
    const query = $("searchInput").value.trim().toLowerCase();
    const filter = $("statusFilter").value;
    const visible = records.filter(record => {
      const matchesText = [record.name,record.reference,record.notes].join(" ").toLowerCase().includes(query);
      return matchesText && (filter === "all" || record.status === filter);
    });

    $("applicationRows").innerHTML = visible.map(record => `
      <tr>
        <td><strong>${escapeHTML(record.name)}</strong><small>${record.date ? `Application date: ${dateLabel(record.date)}` : "Personal record"}</small></td>
        <td><span class="reference">${escapeHTML(record.reference || "Not added")}</span></td>
        <td><span class="status-pill status-${record.status}">${statuses[record.status]}</span></td>
        <td>${dateLabel(record.updatedAt ? record.updatedAt.slice(0,10) : record.date)}</td>
        <td><button class="row-action" data-view="${escapeHTML(record.id)}">View</button></td>
      </tr>`).join("");

    const isEmpty = visible.length === 0;
    $("emptyState").classList.toggle("visible",isEmpty);
    $("emptyState").querySelector("h3").textContent = records.length ? "No matching records" : "No applications to show yet";
    $("emptyState").querySelector("p").textContent = records.length ? "Try changing your search or status filter." : "Add an application record to start organising your personal tracking information.";
    $("emptyState").querySelector(".add-btn").style.display = records.length ? "none" : "inline-block";
    $("recordCount").textContent = `Showing ${visible.length} of ${records.length} records`;
    updateStats();
  }

  function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
      "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
    })[char]);
  }

  function openForm(record = null) {
    $("applicationForm").reset();
    $("recordId").value = record?.id || "";
    $("modalTitle").textContent = record ? "Edit application" : "Add an application";
    $("serviceName").value = record?.name || "";
    $("referenceNumber").value = record?.reference || "";
    $("applicationStatus").value = record?.status || "draft";
    $("applicationDate").value = record?.date || "";
    $("followUpDate").value = record?.followUpDate || "";
    $("applicationNotes").value = record?.notes || "";
    $("modalBackdrop").classList.add("open");
    $("serviceName").focus();
  }

  function closeForm() {
    $("modalBackdrop").classList.remove("open");
  }

  function openDetails(id) {
    const record = records.find(item => item.id === id);
    if (!record) return;
    selectedId = id;
    $("detailTitle").textContent = record.name;
    $("detailContent").innerHTML = `
      <div class="detail-meta">
        <div><small>REFERENCE NUMBER</small><strong>${escapeHTML(record.reference || "Not added")}</strong></div>
        <div><small>YOUR STATUS</small><strong>${statuses[record.status]}</strong></div>
        <div><small>APPLICATION DATE</small><strong>${dateLabel(record.date)}</strong></div>
        <div><small>NEXT FOLLOW-UP</small><strong>${dateLabel(record.followUpDate)}</strong></div>
      </div>
      <div class="detail-notes"><strong>Personal notes</strong><p>${escapeHTML(record.notes || "No notes added.")}</p></div>
      <p class="detail-disclaimer">This is a personal record. It does not reflect a live government application status.</p>`;
    $("detailBackdrop").classList.add("open");
  }

  $("addApplication").addEventListener("click",() => openForm());
  $("emptyAdd").addEventListener("click",() => openForm());
  $("closeModal").addEventListener("click",closeForm);
  $("cancelModal").addEventListener("click",closeForm);
  $("closeDetail").addEventListener("click",() => $("detailBackdrop").classList.remove("open"));
  $("modalBackdrop").addEventListener("click",event => {if(event.target === $("modalBackdrop")) closeForm();});
  $("detailBackdrop").addEventListener("click",event => {if(event.target === $("detailBackdrop")) $("detailBackdrop").classList.remove("open");});

  $("applicationForm").addEventListener("submit",event => {
    event.preventDefault();
    const id = $("recordId").value;
    const previous = records.find(item => item.id === id);
    const record = {
      id: id || makeId(),
      name: $("serviceName").value.trim(),
      reference: $("referenceNumber").value.trim(),
      status: $("applicationStatus").value,
      date: $("applicationDate").value,
      followUpDate: $("followUpDate").value,
      notes: $("applicationNotes").value.trim(),
      updatedAt: new Date().toISOString()
    };

    if (!record.name) return;
    if (previous) records = records.map(item => item.id === id ? record : item);
    else records.unshift(record);

    try {
      persist();
      render();
      closeForm();
      notify(previous ? "Application record updated." : "Application record added.");
    } catch {
      notify("Unable to save. Check browser storage settings.");
    }
  });

  $("applicationRows").addEventListener("click",event => {
    const button = event.target.closest("[data-view]");
    if (button) openDetails(button.dataset.view);
  });

  $("editRecord").addEventListener("click",() => {
    const record = records.find(item => item.id === selectedId);
    $("detailBackdrop").classList.remove("open");
    if (record) openForm(record);
  });

  $("deleteRecord").addEventListener("click",() => {
    if (!selectedId) return;
    if (!window.confirm("Delete this personal application record?")) return;
    records = records.filter(item => item.id !== selectedId);
    persist();
    render();
    selectedId = null;
    $("detailBackdrop").classList.remove("open");
    notify("Application record deleted.");
  });

  $("searchInput").addEventListener("input",render);
  $("statusFilter").addEventListener("change",render);
  $("menuBtn").addEventListener("click",() => $("sidebar").classList.toggle("open"));
  document.addEventListener("click",event => {
    if (window.innerWidth <= 760 && !$("sidebar").contains(event.target) && !$("menuBtn").contains(event.target)) {
      $("sidebar").classList.remove("open");
    }
  });
  document.addEventListener("keydown",event => {
    if (event.key === "Escape") {
      closeForm();
      $("detailBackdrop").classList.remove("open");
    }
  });

  try {
    loadRecords();
    persist();
    render();
    const profile = JSON.parse(localStorage.getItem("schemesathi_profile") || "{}");
    $("topAvatar").textContent = profile.fullName?.trim()?.charAt(0)?.toUpperCase() || "S";
  } catch {
    notify("Could not load local application records.");
  }
})();
