document.addEventListener("DOMContentLoaded", () => {
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

    let mode = "login";

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
            ? "Start your SchemeSathi journey."
            : "Sign in to continue your journey.";

        submitLabel.textContent = isRegister ? "Create account" : "Sign in";
        switchText.textContent = isRegister
            ? "Already have an account?"
            : "Don't have an account?";

        switchMode.textContent = isRegister ? "Sign in" : "Create one";
    }

    function setError(id, text) {
        $(id).textContent = text;
    }

    function validateEmail(value) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
    }

    function getPasswordStrength(value) {
        let score = 0;

        if (value.length >= 8) score++;
        if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score++;
        if (/\d/.test(value)) score++;
        if (/[^A-Za-z0-9]/.test(value)) score++;

        return score;
    }

    function updatePasswordStrength() {
        const value = password.value;
        const strength = getPasswordStrength(value);

        const labels = [
            "Very weak",
            "Weak",
            "Fair",
            "Good",
            "Strong"
        ];

        const widths = ["5%", "25%", "50%", "75%", "100%"];

        $("strengthBar").style.width = value ? widths[strength] : "0%";
        $("strengthText").textContent = value
            ? labels[strength]
            : "Password strength";
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

        if (mode === "register") {
            const name = $("fullName").value.trim();

            if (name.length < 2) {
                setError("nameError", "Please enter your full name.");
                valid = false;
            }
        }

        if (!email || !validateEmail(email)) {
            setError("emailError", "Please enter a valid email address.");
            valid = false;
        }

        if (!pass) {
            setError("passwordError", "Please enter your password.");
            valid = false;
        } else if (mode === "register" && pass.length < 8) {
            setError("passwordError", "Password must contain at least 8 characters.");
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
        }

        return valid;
    }

    form.addEventListener("submit", event => {
        event.preventDefault();
        clearMessage();

        if (!validateForm()) {
            showMessage("Please review the highlighted fields and try again.");
            return;
        }

        // Frontend-only stage: do not pretend that authentication succeeded.
        if (mode === "login") {
            showMessage(
                "Your details look valid. Account sign-in is not connected yet. We will enable it when the backend authentication API is ready.",
                "success"
            );
        } else {
            showMessage(
                "Your registration details look valid. Account creation is not connected yet. We will enable it when the backend registration API is ready.",
                "success"
            );
        }
    });

    loginTab.addEventListener("click", () => setMode("login"));
    registerTab.addEventListener("click", () => setMode("register"));

    switchMode.addEventListener("click", () => {
        setMode(mode === "login" ? "register" : "login");
    });

    forgotPassword.addEventListener("click", () => {
        clearMessage();

        const email = $("email").value.trim();

        if (email && !validateEmail(email)) {
            showMessage("Please correct your email address first.");
            return;
        }

        showMessage(
            "Password recovery will be available after the account authentication backend is connected.",
            "success"
        );
    });

    $("termsLink").addEventListener("click", event => {
        event.preventDefault();
        showMessage("The full Terms of Service will be published before account registration is enabled.", "success");
    });

    $("privacyLink").addEventListener("click", event => {
        event.preventDefault();
        showMessage("The full Privacy Policy will be published before account registration is enabled.", "success");
    });

    setMode("login");
});
