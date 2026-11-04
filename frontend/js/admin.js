(() => {
    const sidebar = document.getElementById("adminSidebar");
    const menuButton = document.getElementById("mobileMenu");

    if (sidebar && menuButton) {
        menuButton.addEventListener("click", () => {
            sidebar.classList.toggle("open");
        });

        document.addEventListener("click", (event) => {
            if (
                window.innerWidth <= 800 &&
                sidebar.classList.contains("open") &&
                !sidebar.contains(event.target) &&
                !menuButton.contains(event.target)
            ) {
                sidebar.classList.remove("open");
            }
        });
    }

    const dateElement = document.getElementById("currentDate");

    if (dateElement) {
        dateElement.textContent = new Intl.DateTimeFormat("en-IN", {
            weekday: "short",
            day: "numeric",
            month: "long",
            year: "numeric"
        }).format(new Date());
    }
})();
