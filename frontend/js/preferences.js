document.addEventListener("DOMContentLoaded", async () => {
    const api = window.SchemeSathiAPI;
    if (!api.requireCitizen()) return;

    const $ = id => document.getElementById(id);
    const channelControls = {
        email: "emailNotifications",
        sms: "smsNotifications",
        in_app: "inAppNotifications"
    };
    let profile = null;
    let toastTimer;

    function notify(message) {
        $("toast").textContent = message;
        $("toast").classList.add("show");
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => $("toast").classList.remove("show"), 2800);
    }

    function applyAccessibility(settings) {
        api.applyAccessibilityPreferences(settings);
    }

    function updateAvatar() {
        $("topAvatar").textContent = profile?.display_name?.trim()?.charAt(0)?.toUpperCase() || "S";
    }

    function getNotificationPreferences() {
        const values = {};
        Object.entries(channelControls).forEach(([key, id]) => {
            values[key] = $(id).checked;
        });
        return values;
    }

    function getAccessibilityPreferences() {
        return {
            font_size: $("fontSize").value,
            text_scale_percent: Number($("textScale").value),
            high_contrast: $("highContrast").checked,
            increased_spacing: $("increasedSpacing").checked,
            large_buttons: $("largeButtons").checked,
            simple_mode: $("simpleMode").checked,
            read_aloud: $("readAloud").checked,
            reduced_motion: $("reducedMotion").checked
        };
    }

    function setAccessibilityControls(settings) {
        const preferences = {
            ...api.getAccessibilityPreferences(),
            ...(settings || {})
        };
        $("fontSize").value = preferences.font_size;
        $("textScale").value = String(preferences.text_scale_percent);
        $("textScaleValue").value = `${preferences.text_scale_percent}%`;
        $("textScaleValue").textContent = `${preferences.text_scale_percent}%`;
        $("highContrast").checked = Boolean(preferences.high_contrast);
        $("increasedSpacing").checked = Boolean(preferences.increased_spacing);
        $("largeButtons").checked = Boolean(preferences.large_buttons);
        $("simpleMode").checked = Boolean(preferences.simple_mode);
        $("readAloud").checked = Boolean(preferences.read_aloud);
        $("reducedMotion").checked = Boolean(preferences.reduced_motion);
        applyAccessibility(preferences);
    }

    const fontScalePresets = {
        small: 90,
        medium: 100,
        large: 120,
        extra_large: 140
    };

    function fontSizeForScale(value) {
        if (value <= 95) return "small";
        if (value <= 110) return "medium";
        if (value <= 130) return "large";
        return "extra_large";
    }

    $("fontSize").addEventListener("change", () => {
        $("textScale").value = String(fontScalePresets[$("fontSize").value]);
        $("textScale").dispatchEvent(new Event("input"));
    });

    $("textScale").addEventListener("input", () => {
        const value = Number($("textScale").value);
        $("fontSize").value = fontSizeForScale(value);
        $("textScaleValue").value = `${value}%`;
        $("textScaleValue").textContent = `${value}%`;
        applyAccessibility(getAccessibilityPreferences());
    });

    [
        "highContrast",
        "increasedSpacing",
        "largeButtons",
        "simpleMode",
        "readAloud",
        "reducedMotion"
    ].forEach(id => {
        $(id).addEventListener("change", () =>
            applyAccessibility(getAccessibilityPreferences())
        );
    });

    $("readAloudPreview").addEventListener("click", async () => {
        const language = `${(document.documentElement.lang || "en").split("-")[0]}-IN`;
        try {
            const audioBlob = await api.request("/voice/synthesize", {
                method: "POST",
                responseType: "blob",
                body: JSON.stringify({
                    text: "GovNexus can read this preview only through Prism. Text settings still work when voice is unavailable.",
                    language_code: language,
                    speed: 1
                })
            });
            if (!audioBlob.size) throw new Error("Prism returned no audio.");
            const audio = new Audio(URL.createObjectURL(audioBlob));
            await audio.play();
        } catch (error) {
            notify(error.message || "Prism speech is not available. Text preferences still work.");
        }
    });

    $("saveSettings").addEventListener("click", async () => {
        const saveButton = $("saveSettings");
        saveButton.disabled = true;
        $("saveMessage").textContent = "Saving…";
        try {
            profile = await api.patch("/users/me", {
                preferred_language_code: $("language").value,
                notification_preferences: getNotificationPreferences(),
                accessibility_preferences: getAccessibilityPreferences()
            }, "citizen");
            api.cachePreferredLanguage(profile.preferred_language_code);
            applyAccessibility(profile.accessibility_preferences);
            $("saveMessage").textContent = "Account and accessibility preferences saved.";
            notify("Your preferences have been saved.");
        } catch (error) {
            $("saveMessage").textContent = error.message;
            notify(`Could not save preferences: ${error.message}`);
        } finally {
            saveButton.disabled = false;
        }
    });

    $("resetSettings").addEventListener("click", async () => {
        if (!window.confirm("Reset notification and accessibility preferences? Your preferred language will not change.")) return;
        const resetButton = $("resetSettings");
        resetButton.disabled = true;
        try {
            profile = await api.patch("/users/me", {
                notification_preferences: { email: false, sms: false, in_app: false },
                accessibility_preferences: {
                    font_size: "medium",
                    text_scale_percent: 100,
                    high_contrast: false,
                    increased_spacing: false,
                    large_buttons: false,
                    simple_mode: false,
                    read_aloud: false,
                    reduced_motion: false
                }
            }, "citizen");
            $("emailNotifications").checked = false;
            $("smsNotifications").checked = false;
            $("inAppNotifications").checked = false;
            setAccessibilityControls(profile.accessibility_preferences);
            $("saveMessage").textContent = "Notification and accessibility preferences reset.";
            notify("Preferences have been reset.");
        } catch (error) {
            $("saveMessage").textContent = error.message;
            notify(`Could not reset preferences: ${error.message}`);
        } finally {
            resetButton.disabled = false;
        }
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
        const languageSelect = $("language");
        const languages = Array.isArray(languagesResult.items) ? languagesResult.items : [];
        languageSelect.replaceChildren();
        languages.forEach(language => {
            const option = document.createElement("option");
            option.value = language.code;
            option.textContent = language.native_name
                ? `${language.native_name} — ${language.english_name}`
                : language.english_name;
            languageSelect.appendChild(option);
        });
        languageSelect.value = profile.preferred_language_code || "";
        Object.entries(channelControls).forEach(([key, id]) => {
            $(id).checked = Boolean(profile.notification_preferences?.[key]);
        });
        setAccessibilityControls(profile.accessibility_preferences);
        updateAvatar();
    } catch (error) {
        $("saveMessage").textContent = `Preferences could not be loaded: ${error.message}`;
        notify(`Preferences could not be loaded: ${error.message}`);
        $("saveSettings").disabled = true;
        $("resetSettings").disabled = true;
    }
});
