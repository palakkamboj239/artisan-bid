/**
 * ArtisanBid – main.js
 * Luxury auction platform interactions.
 */

document.addEventListener("DOMContentLoaded", function () {

    // Auto-dismiss flash messages after 6 seconds
    var alerts = document.querySelectorAll(".messages-container .alert");
    alerts.forEach(function (alert) {
        setTimeout(function () {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 6000);
    });

    // Auction countdown timers
    document.querySelectorAll(".auction-countdown[data-end]").forEach(function (el) {
        var endTime = new Date(el.getAttribute("data-end").replace(" ", "T")).getTime();
        var timerEl = el.querySelector(".countdown-timer");

        function updateCountdown() {
            var now = new Date().getTime();
            var diff = endTime - now;
            if (diff <= 0) {
                timerEl.textContent = "Ended";
                return;
            }
            var days = Math.floor(diff / (1000 * 60 * 60 * 24));
            var hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            var minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            var seconds = Math.floor((diff % (1000 * 60)) / 1000);

            if (days > 0) {
                timerEl.textContent = days + "d " + hours + "h " + minutes + "m";
            } else if (hours > 0) {
                timerEl.textContent = hours + "h " + minutes + "m " + seconds + "s";
            } else {
                timerEl.textContent = minutes + "m " + seconds + "s";
            }
        }

        updateCountdown();
        setInterval(updateCountdown, 1000);
    });

});
