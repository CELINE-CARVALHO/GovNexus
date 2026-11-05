document.addEventListener("DOMContentLoaded", async () => {
    const api = window.SchemeSathiAPI;
    if (!api.requireCitizen()) return;

    const $ = id => document.getElementById(id);
    const ACCESSIBILITY_KEY = "schemesathi_accessibility_v1";
    const form = $("profileForm");
    let profile = null;
    let states = [];
    let districts = [];
    let toastTimer;

    function notify(message) {
        const toast = $("toast");
        toast.textContent = message;
        toast.classList.add("show");
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => toast.classList.remove("show"), 2800);
    }

    function readAccessibility() {
        try {
            return JSON.parse(localStorage.getItem(ACCESSIBILITY_KEY) || "{}");
        } catch (error) {
            throw new Error("Could not read local accessibility settings.");
        }
    }

    function saveAccessibility(settings) {
        try {
            localStorage.setItem(ACCESSIBILITY_KEY, JSON.stringify(settings));
        } catch (error) {
            throw new Error("Could not save local accessibility settings.");
        }
    }

    function applyAccessibility(settings) {
        document.body.classList.toggle("large-text", Boolean(settings.largeText));
        document.body.classList.toggle("reduced-motion", Boolean(settings.reducedMotion));
    }

    function updateSummary(data) {
        const name = data.display_name?.trim() || "Welcome!";
        const email = data.email?.trim() || "No email address";
        const initial = name.charAt(0).toUpperCase() || "S";
        $("displayName").textContent = name;
        $("displayEmail").textContent = email;
        $("largeAvatar").textContent = initial;
        $("topAvatar").textContent = initial;
        const checks = [
            Boolean(data.display_name?.trim()),
            Boolean(data.email?.trim()),
            Boolean(data.phone_number?.trim()),
            Boolean(data.state_id),
            Boolean(data.district_id),
            Boolean(data.preferred_language_code)
        ];
        const percent = Math.round(checks.filter(Boolean).length / checks.length * 100);
        $("completionText").textContent = `${percent}%`;
        $("completionBar").style.width = `${percent}%`;
    }

    function fillOptions(select, items, placeholder, selectedId = "") {
        select.replaceChildren();
        const first = document.createElement("option");
        first.value = "";
        first.textContent = placeholder;
        select.appendChild(first);
        items.forEach(item => {
            const option = document.createElement("option");
            option.value = item.id;
            option.textContent = item.name || item.code;
            select.appendChild(option);
        });
        select.value = items.some(item => item.id === selectedId) ? selectedId : "";
    }

    async function loadLocations(path, expectedType) {
        const items = [];
        let page = 1;
        let pages = 1;
        do {
            const result = await api.get(
                `${path}&page=${page}&limit=100`
            );
            items.push(...(Array.isArray(result.items) ? result.items : []));
            pages = Number(result.pagination?.pages) || 1;
            page += 1;
        } while (page <= pages);
        return items.filter(item => item.location_type === expectedType);
    }

    async function loadDistricts(stateId, selectedId = "") {
        const select = $("district");
        if (!stateId) {
            districts = [];
            fillOptions(select, districts, "Select a state first");
            select.disabled = true;
            return;
        }
        select.disabled = true;
        select.replaceChildren(new Option("Loading districts…", ""));
        const result = await api.get(
            `/locations?location_type=district&parent_id=${encodeURIComponent(stateId)}&active_only=true&page=1&limit=100&language=en`
        );
        districts = Array.isArray(result.items) ? result.items : [];
        fillOptions(select, districts, "Select your district", selectedId);
        select.disabled = false;
        if (result.pagination?.pages > 1) {
            notify("Only the first 100 districts are shown for this state.");
        }
    }

    $("state").addEventListener("change", async () => {
        try {
            await loadDistricts($("state").value);
        } catch (error) {
            notify(`Districts could not be loaded: ${error.message}`);
        }
    });

    form.addEventListener("submit", async event => {
        event.preventDefault();
        const name = $("fullName").value.trim();
        if (!name) {
            $("fullName").focus();
            $("saveMessage").textContent = "Enter your name.";
            return;
        }
        if ($("district").value && !$("state").value) {
            $("saveMessage").textContent = "Select a state for the chosen district.";
            return;
        }

        const saveButton = form.querySelector('[type="submit"]');
        saveButton.disabled = true;
        $("saveMessage").textContent = "Saving…";
        try {
            profile = await api.patch("/users/me", {
                display_name: name,
                preferred_language_code: $("preferredLanguage").value,
                state_id: $("state").value || null,
                district_id: $("district").value || null
            }, "citizen");
        } catch (error) {
            $("saveMessage").textContent = error.message;
            notify(`Could not save account profile: ${error.message}`);
            saveButton.disabled = false;
            return;
        }
        try {
            const accessibility = {
                largeText: $("largeText").checked,
                reducedMotion: $("reducedMotion").checked
            };
            saveAccessibility(accessibility);
            applyAccessibility(accessibility);
            updateSummary(profile);
            $("saveMessage").textContent = "Profile updated.";
            notify("Your profile has been updated.");
        } catch (error) {
            updateSummary(profile);
            $("saveMessage").textContent = `Account profile saved, but accessibility settings could not be saved: ${error.message}`;
            notify("Account profile saved; accessibility settings were not saved.");
        } finally {
            saveButton.disabled = false;
        }
    });

    $("privacyInfo").addEventListener("click", event => {
        event.preventDefault();
        notify("Profile data is retrieved from your signed-in SchemeSathi account.");
    });
    $("menuBtn").addEventListener("click", () => $("sidebar").classList.toggle("open"));
    document.addEventListener("click", event => {
        if (window.innerWidth <= 760 &&
            !$("sidebar").contains(event.target) &&
            !$("menuBtn").contains(event.target)) {
            $("sidebar").classList.remove("open");
        }
    });

    try {
        const [profileResult, languagesResult] = await Promise.all([
            api.get("/users/me", "citizen"),
            api.get("/languages?active_only=true")
        ]);
        profile = profileResult;
        const languages = Array.isArray(languagesResult.items) ? languagesResult.items : [];
        const languageSelect = $("preferredLanguage");
        languageSelect.replaceChildren();
        languages.forEach(language => {
            const option = document.createElement("option");
            option.value = language.code;
            option.textContent = language.native_name
                ? `${language.native_name} (${language.english_name})`
                : language.english_name;
            languageSelect.appendChild(option);
        });
        languageSelect.value = profile.preferred_language_code || "";
        if (!languages.some(item => item.code === languageSelect.value)) {
            languageSelect.value = "";
        }

        const locationResult = await loadLocations(
            "/locations?location_type=state%2Cunion_territory&active_only=true&language=en",
            "state"
        );
        states = locationResult;
        fillOptions($("state"), states, "Select your state", profile.state_id || "");
        await loadDistricts($("state").value, profile.district_id || "");
        $("email").value = profile.email || "";
        $("phone").value = profile.phone_number || "";

        let accessibility = {};
        try {
            accessibility = readAccessibility();
        } catch (error) {
            notify(error.message);
        }
        $("largeText").checked = Boolean(accessibility.largeText);
        $("reducedMotion").checked = Boolean(accessibility.reducedMotion);
        applyAccessibility(accessibility);
        updateSummary(profile);
    } catch (error) {
        $("saveMessage").textContent = `Profile could not be loaded: ${error.message}`;
        notify(`Profile could not be loaded: ${error.message}`);
        form.querySelector('[type="submit"]').disabled = true;
    }
});
