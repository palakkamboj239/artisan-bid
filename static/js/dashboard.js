/**
 * ArtisanBid – Dashboard JavaScript
 * Sidebar toggle, countdown timers, animated counters, settings tabs.
 */
(function () {
    "use strict";

    // ─── Sidebar Toggle ──────────────────────────────────────────────
    var toggleBtn = document.getElementById("sidebarToggle");
    var sidebar = document.getElementById("dashboardSidebar");

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener("click", function () {
            sidebar.classList.toggle("open");
        });

        // Close sidebar on outside click (mobile)
        document.addEventListener("click", function (e) {
            if (window.innerWidth <= 992 &&
                !sidebar.contains(e.target) &&
                !toggleBtn.contains(e.target)) {
                sidebar.classList.remove("open");
            }
        });
    }

    // ─── Countdown Timers ────────────────────────────────────────────
    document.querySelectorAll("[data-end]").forEach(function (el) {
        var endTime = new Date(el.getAttribute("data-end").replace(" ", "T")).getTime();
        var timerEl = el.querySelector(".timer-text") || el.querySelector(".countdown-value");

        if (!timerEl) return;

        function tick() {
            var diff = endTime - Date.now();
            if (diff <= 0) {
                timerEl.textContent = "Ended";
                return;
            }
            var d = Math.floor(diff / 86400000);
            var h = Math.floor((diff % 86400000) / 3600000);
            var m = Math.floor((diff % 3600000) / 60000);
            var s = Math.floor((diff % 60000) / 1000);

            if (d > 0) {
                timerEl.textContent = d + "d " + h + "h " + m + "m";
            } else if (h > 0) {
                timerEl.textContent = h + "h " + m + "m " + s + "s";
            } else {
                timerEl.textContent = m + "m " + s + "s";
                // Urgent pulse
                el.classList.add("text-danger");
            }
        }

        tick();
        setInterval(tick, 1000);
    });

    // ─── Animated Counters ───────────────────────────────────────────
    var counterEls = document.querySelectorAll(".stat-value[data-count]");
    counterEls.forEach(function (el) {
        var target = parseInt(el.getAttribute("data-count"), 10);
        if (isNaN(target) || target === 0) return;

        var current = 0;
        var step = Math.max(1, Math.floor(target / 40));
        var dur = Math.min(1500, Math.max(500, target * 3));

        var interval = setInterval(function () {
            current += step;
            if (current >= target) {
                current = target;
                clearInterval(interval);
            }
            el.textContent = current.toLocaleString();
        }, dur / (target / step));
    });

    // ─── Settings Tabs ───────────────────────────────────────────────
    var navLinks = document.querySelectorAll(".settings-nav-link");
    navLinks.forEach(function (link) {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            var target = this.getAttribute("data-target");
            if (!target) return;

            navLinks.forEach(function (l) { l.classList.remove("active"); });
            this.classList.add("active");

            document.querySelectorAll(".settings-panel").forEach(function (p) {
                p.classList.remove("active");
            });

            var panel = document.getElementById("panel-" + target);
            if (panel) panel.classList.add("active");
        });
    });

    // ─── Profile Image Preview ───────────────────────────────────────
    var profileUpload = document.getElementById("profileUpload");
    var profilePreview = document.getElementById("profilePreview");

    if (profileUpload && profilePreview) {
        profileUpload.addEventListener("change", function () {
            var file = this.files[0];
            if (file) {
                var reader = new FileReader();
                reader.onload = function (e) {
                    profilePreview.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // ─── Watchlist Remove (via AJAX) ─────────────────────────────────
    document.querySelectorAll(".watch-remove").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var url = this.getAttribute("data-url");
            var csrf = this.getAttribute("data-csrf");
            if (!url) return;

            var card = this.closest(".watchlist-card");
            if (card) card.style.opacity = "0.3";

            fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrf,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: "csrfmiddlewaretoken=" + encodeURIComponent(csrf),
            }).then(function () {
                if (card) {
                    card.style.transition = "opacity 0.3s, transform 0.3s";
                    card.style.opacity = "0";
                    card.style.transform = "scale(0.95)";
                    setTimeout(function () { card.remove(); }, 300);
                }
            }).catch(function () {
                if (card) card.style.opacity = "1";
            });
        });
    });

    // ─── Favorite Remove (via AJAX) ──────────────────────────────────
    document.querySelectorAll(".fav-remove").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var artworkId = this.getAttribute("data-artwork-id");
            if (!artworkId) return;

            var card = this.closest(".artwork-card-dash");
            if (card) card.style.opacity = "0.3";

            // Toggle favorite via API (placeholder)
            var url = "/artworks/" + artworkId + "/favorite/";

            fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            }).then(function () {
                if (card) {
                    card.style.transition = "opacity 0.3s, transform 0.3s";
                    card.style.opacity = "0";
                    card.style.transform = "scale(0.95)";
                    setTimeout(function () { card.remove(); }, 300);
                }
            }).catch(function () {
                if (card) card.style.opacity = "1";
            });
        });
    });

    // ─── CSRF Cookie Helper ──────────────────────────────────────────
    function getCookie(name) {
        var parts = "; " + document.cookie;
        var c = parts.split("; " + name + "=");
        if (c.length === 2) return c.pop().split(";").shift();
    }

})();
