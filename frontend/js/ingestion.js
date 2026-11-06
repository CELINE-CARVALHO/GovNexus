document.addEventListener("DOMContentLoaded", async () => {
    const api = window.SchemeSathiAPI;
    if (!api.requireAdmin()) return;

    const $ = id => document.getElementById(id);
    let jobs = [];
    let toastTimer;

    function setText(id, value) {
        const element = $(id);
        if (element) element.textContent = value;
    }

    function notify(message) {
        const toast = $("ingestToast");
        if (!toast) return;
        toast.textContent = message;
        toast.classList.add("show");
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => toast.classList.remove("show"), 3000);
    }

    function formatDateTime(value) {
        if (!value) return "—";
        const timestamp = String(value);
        const date = new Date(
            timestamp.endsWith("Z") || timestamp.includes("+")
                ? timestamp
                : `${timestamp}Z`
        );
        if (Number.isNaN(date.getTime())) return "—";
        return new Intl.DateTimeFormat("en-IN", {
            day: "numeric", month: "short", hour: "2-digit", minute: "2-digit"
        }).format(date);
    }

    function render() {
        const status = $("jobFilter")?.value || "all";
        const rows = jobs.filter(job => status === "all" || job.status === status);
        const list = $("jobList");
        const empty = $("emptyJobs");
        setText("queueCount", `${rows.length} ${rows.length === 1 ? "JOB" : "JOBS"}`);
        if (empty) empty.hidden = rows.length > 0;
        if (!list) return;
        list.replaceChildren();
        if (empty) {
            setText("emptyJobsTitle", "No ingestion jobs found");
            setText("emptyJobsDetail", "No ingestion jobs match this status filter.");
        }
        rows.forEach(job => {
            const row = document.createElement("div");
            row.className = "job-row";
            const info = document.createElement("div");
            const title = document.createElement("strong");
            title.textContent = String(job.job_type || "job").replaceAll("_", " ");
            const detail = document.createElement("small");
            detail.textContent =
                `Scheduled ${formatDateTime(job.scheduled_at)} · ` +
                `Started ${formatDateTime(job.started_at)} · ` +
                `Completed ${formatDateTime(job.completed_at)} · ` +
                `Attempt ${job.attempt_count ?? "—"} of ${job.max_attempts ?? "—"}`;
            info.append(title, detail);
            const pill = document.createElement("span");
            pill.className = "job-status";
            if (/^[a-z_-]+$/i.test(job.status || "")) {
                pill.classList.add(job.status);
            }
            pill.textContent = String(job.status || "unknown").replaceAll("_", " ");
            row.append(info, pill);
            list.appendChild(row);
        });
    }

    $("jobFilter")?.addEventListener("change", render);
    $("retryJobs")?.addEventListener("click", loadJobs);

    async function loadJobs() {
        const retry = $("retryJobs");
        if (retry) {
            retry.hidden = true;
            retry.disabled = true;
        }
        setText("ingestEnv", "LOADING");
        setText("jobsSubtitle", "Loading recent ingestion jobs…");
        setText("queueCount", "LOADING");
        const list = $("jobList");
        if (list) {
            const loading = document.createElement("div");
            loading.className = "empty-ingest";
            loading.textContent = "Loading ingestion jobs…";
            list.replaceChildren(loading);
        }

        try {
            const [dashboard, recent] = await Promise.all([
                api.get("/admin/dashboard", "admin"),
                api.get("/admin/ingestion-jobs?limit=25", "admin")
            ]);
            const ingestion = dashboard?.ingestion || {};
            setText("jobTotal", String(ingestion.total_jobs ?? "—"));
            setText("jobPending", String(ingestion.pending ?? "—"));
            setText("jobRunning", String(ingestion.running ?? "—"));
            setText("jobFailed", String(ingestion.failed ?? "—"));
            jobs = Array.isArray(recent?.items) ? recent.items : [];
            setText("ingestEnv", "LIVE DATA");
            setText(
                "jobsSubtitle",
                `Showing the ${jobs.length} most recent of ${recent?.total ?? jobs.length} jobs.`
            );
            render();
            if (retry) retry.disabled = false;
        } catch (error) {
            setText("ingestEnv", "UNAVAILABLE");
            setText("jobsSubtitle", "Ingestion jobs could not be loaded.");
            const empty = $("emptyJobs");
            if (empty) empty.hidden = false;
            setText("emptyJobsTitle", "Ingestion data unavailable");
            setText("emptyJobsDetail", error.message);
            const listOnError = $("jobList");
            if (listOnError) listOnError.replaceChildren();
            setText("queueCount", "UNAVAILABLE");
            if (retry) {
                retry.disabled = false;
                retry.hidden = false;
            }
            notify(`Ingestion data could not be loaded: ${error.message}`);
        }
    }

    await loadJobs();
});