document.addEventListener("DOMContentLoaded", async () => {
    const api = window.SchemeSathiAPI;
    const $ = id => document.getElementById(id);
    const form = $("authForm");
    const loginTab = $("loginTab");
    const registerTab = $("registerTab");
    const switchMode = $("switchMode");
    const switchText = $("switchText");
    const heading = $("formHeading");
    const subheading = $("formSubheading");
    const submitLabel = $("submitLabel");
    const submitButton = $("submitButton");
    const message = $("authMessage");
    const nameField = $("nameField");
    const confirmField = $("confirmField");
    const languageField = $("languageField");
    const termsRow = $("termsRow");
    const rememberRow = $("rememberRow");
    const forgotPassword = $("forgotPassword");
    const strengthPanel = $("passwordStrength");
    const password = $("password");
    const languageSelect = $("preferredLanguage");

    let mode = "login";
    let languagesLoaded = false;

    function showMessage(text, type = "error") {
        message.textContent = text;
        message.className = `auth-message ${type}`;
        message.hidden = false;
    }

    function clearMessage() {
        message.textContent = "";
        message.hidden = true;
    }

    function clearErrors() {
        ["nameError", "emailError", "passwordError", "confirmError", "termsError"]
            .forEach(id => $(id).textContent = "");
    }

    function setMode(nextMode) {
        mode = nextMode;
        const isRegister = mode === "register";
        clearMessage();
        clearErrors();
        form.reset();

        loginTab.classList.toggle("active", !isRegister);
        registerTab.classList.toggle("active", isRegister);
        nameField.hidden = !isRegister;
        confirmField.hidden = !isRegister;
        languageField.hidden = !isRegister;
        termsRow.hidden = !isRegister;
        rememberRow.hidden = isRegister;
        forgotPassword.hidden = isRegister;
        strengthPanel.hidden = true;
        password.autocomplete = isRegister ? "new-password" : "current-password";
        heading.textContent = isRegister ? "Create your account." : "Welcome back.";
        subheading.textContent = isRegister
            ? "Start your GovNexus journey."
            : "Sign in to continue your journey.";
        submitLabel.textContent = isRegister ? "Create account" : "Sign in";
        switchText.textContent = isRegister
            ? "Already have an account?"
            : "Don't have an account?";
        switchMode.textContent = isRegister ? "Sign in" : "Create one";
        submitButton.disabled = isRegister && !languagesLoaded;
    }

    function setError(id, text) {
        $(id).textContent = text;
    }

    function validateEmail(value) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
    }

    function getPasswordStrength(value) {
        let score = 0;
        if (value.length >= 12) score++;
        if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score++;
        if (/\d/.test(value)) score++;
        if (/[^A-Za-z0-9]/.test(value)) score++;
        return score;
    }

    function updatePasswordStrength() {
        const value = password.value;
        const strength = getPasswordStrength(value);
        const labels = ["Very weak", "Weak", "Fair", "Good", "Strong"];
        const widths = ["5%", "25%", "50%", "75%", "100%"];
        $("strengthBar").style.width = value ? widths[strength] : "0%";
        $("strengthText").textContent = value ? labels[strength] : "Password strength";
    }

    function safeNextPath() {
        const candidate = new URLSearchParams(window.location.search).get("next");
        if (!candidate) return "dashboard.html";
        const target = new URL(candidate, window.location.href);
        if (target.origin !== window.location.origin ||
            !target.pathname.includes("/pages/") ||
            target.pathname.includes("/pages/admin/")) {
            return "dashboard.html";
        }
        return `${target.pathname}${target.search}${target.hash}`;
    }

    function loadLanguages() {
        api.get("/languages").then(result => {
            const items = Array.isArray(result.items) ? result.items : [];
            languageSelect.replaceChildren();
            items.forEach(item => {
                const option = document.createElement("option");
                option.value = item.code;
                option.textContent = item.native_name
                    ? `${item.native_name} — ${item.english_name}`
                    : item.english_name;
                languageSelect.appendChild(option);
            });
            languagesLoaded = items.length > 0;
            submitButton.disabled = mode === "register" && !languagesLoaded;
            if (!languagesLoaded) {
                showMessage("No active registration languages are available.");
            }
        }).catch(error => {
            languagesLoaded = false;
            submitButton.disabled = mode === "register";
            showMessage(`Could not load available languages: ${error.message}`);
        });
    }

    password.addEventListener("input", () => {
        if (mode === "register") {
            strengthPanel.hidden = !password.value;
            updatePasswordStrength();
        }
    });

    document.querySelectorAll(".password-toggle").forEach(button => {
        button.addEventListener("click", () => {
            const target = $(button.dataset.target);
            const isPassword = target.type === "password";
            target.type = isPassword ? "text" : "password";
            button.textContent = isPassword ? "Hide" : "Show";
        });
    });

    function validateForm() {
        clearErrors();
        const email = $("email").value.trim();
        const pass = password.value;
        let valid = true;

        if (mode === "register" && $("fullName").value.trim().length < 2) {
            setError("nameError", "Please enter your full name.");
            valid = false;
        }
        if (!email || !validateEmail(email)) {
            setError("emailError", "Please enter a valid email address.");
            valid = false;
        }
        if (!pass) {
            setError("passwordError", "Please enter your password.");
            valid = false;
        } else if (mode === "register" && pass.length < 12) {
            setError("passwordError", "Password must contain at least 12 characters.");
            valid = false;
        }
        if (mode === "register") {
            if ($("confirmPassword").value !== pass) {
                setError("confirmError", "Your passwords do not match.");
                valid = false;
            }
            if (!$("acceptTerms").checked) {
                setError("termsError", "Please accept the terms to continue.");
                valid = false;
            }
            if (!languagesLoaded || !languageSelect.value) {
                showMessage("Select an available registration language.");
                valid = false;
            }
        }
        return valid;
    }

    form.addEventListener("submit", async event => {
        event.preventDefault();
        clearMessage();
        if (!validateForm()) {
            if (!message.hidden) return;
            showMessage("Please review the highlighted fields and try again.");
            return;
        }

        submitButton.disabled = true;
        const email = $("email").value.trim();
        const pass = password.value;
        try {
            const result = mode === "login"
                ? await api.post("/auth/citizen/login", { email, password: pass })
                : await api.post("/auth/citizen/register", {
                    email,
                    password: pass,
                    display_name: $("fullName").value.trim(),
                    preferred_language_code: languageSelect.value
                });
            api.markAuthenticated("citizen");
            window.location.replace(safeNextPath());
        } catch (error) {
            showMessage(error.message || "Authentication could not be completed.");
        } finally {
            submitButton.disabled = mode === "register" && !languagesLoaded;
        }
    });

    loginTab.addEventListener("click", () => setMode("login"));
    registerTab.addEventListener("click", () => setMode("register"));
    switchMode.addEventListener("click", () =>
        setMode(mode === "login" ? "register" : "login")
    );

    forgotPassword.addEventListener("click", () => {
        clearMessage();
        const email = $("email").value.trim();
        if (email && !validateEmail(email)) {
            showMessage("Please correct your email address first.");
            return;
        }
        showMessage("Password recovery is not available in the account API.", "info");
    });

    $("termsLink").addEventListener("click", event => {
        event.preventDefault();
        showMessage("Terms of Service are not available on this page.", "info");
    });
    $("privacyLink").addEventListener("click", event => {
        event.preventDefault();
        showMessage("Privacy information is not available on this page.", "info");
    });

    let sessionCheckError = null;
    try {
        if (await api.isAuthenticated("citizen")) {
            window.location.replace(safeNextPath());
            return;
        }
    } catch (error) {
        sessionCheckError = error;
    }
    setMode("login");
    if (new URLSearchParams(window.location.search).has("expired")) {
        showMessage("Your session expired. Please sign in again.", "info");
    } else if (sessionCheckError) {
        showMessage(`Could not check your sign-in session: ${sessionCheckError.message}`, "info");
    }
    loadLanguages();
});
