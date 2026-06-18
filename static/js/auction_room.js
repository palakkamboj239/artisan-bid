/**
 * ArtisanBid – Live Auction Room
 * WebSocket client for real-time bidding, countdown, and activity feed.
 */
(function () {
    "use strict";

    const dataEl = document.getElementById("auctionData");
    if (!dataEl) return;

    const DATA = JSON.parse(dataEl.textContent);
    const WS_URL = DATA.wsUrl;

    // ─── DOM refs ──────────────────────────────────────────────────────
    const $ = (id) => document.getElementById(id);
    const currentBidEl = $("currentBid");
    const totalBidsEl = $("totalBids");
    const minBidEl = $("minBid");
    const bidAmountInput = $("bidAmount");
    const placeBidBtn = $("placeBidBtn");
    const bidErrorEl = $("bidError");
    const bidFeed = $("bidFeed");
    const feedEmpty = $("feedEmpty");
    const historyFeed = $("historyFeed");
    const statusBadge = $("statusBadge");
    const countdownDisplay = $("countdownDisplay");
    const cdHours = $("cdHours");
    const cdMinutes = $("cdMinutes");
    const cdSeconds = $("cdSeconds");
    const countdownSection = $("countdownSection");
    const winnerSection = $("winnerSection");
    const winnerName = $("winnerName");
    const winnerPrice = $("winnerPrice");
    const viewersNum = $("viewersNum");
    const biddersNum = $("biddersNum");
    const toast = $("connectionToast");
    const toastDot = $("toastDot");
    const toastText = $("toastText");
    const reserveStatus = $("reserveStatus");

    let socket = null;
    let reconnectTimer = null;
    let countdownInterval = null;
    let auctionEndTime = null;
    let isConnected = false;

    // ─── Utility ───────────────────────────────────────────────────────
    function formatPrice(val) {
        const n = parseFloat(val);
        if (isNaN(n)) return "$0.00";
        return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function updateBidForm(auction) {
        if (minBidEl) minBidEl.textContent = parseFloat(auction.minimum_next_bid).toFixed(2);
        if (bidAmountInput) {
            bidAmountInput.placeholder = parseFloat(auction.minimum_next_bid).toFixed(2);
            bidAmountInput.min = auction.minimum_next_bid;
        }
        if (placeBidBtn) placeBidBtn.disabled = true;
    }

    function updateAuctionState(auction) {
        if (currentBidEl) currentBidEl.textContent = formatPrice(auction.current_bid);
        if (totalBidsEl) totalBidsEl.textContent = auction.total_bids;
        if (statusBadge) {
            statusBadge.textContent = auction.status.charAt(0).toUpperCase() + auction.status.slice(1);
            statusBadge.className = "status-badge status-" + auction.status;
        }
        updateBidForm(auction);
        updateReserve(auction);

        // Handle ended state
        if (auction.status === "ended" || auction.status === "sold") {
            if (countdownDisplay) countdownDisplay.textContent = "Ended";
            if (countdownSection) countdownSection.classList.add("ended");
            if (bidAmountInput) bidAmountInput.disabled = true;
            if (placeBidBtn) placeBidBtn.disabled = true;
        }

        // Handle sold with winner
        if (auction.winner && winnerSection) {
            winnerSection.style.display = "flex";
            if (winnerName) winnerName.textContent = auction.winner;
            if (winnerPrice) winnerPrice.textContent = formatPrice(auction.winning_bid || auction.current_bid);
            winnerSection.classList.add("visible");
        }
    }

    function updateReserve(auction) {
        if (!reserveStatus) return;
        const reserve = parseFloat(auction.reserve_price);
        const current = parseFloat(auction.current_bid);
        if (!auction.reserve_price) { reserveStatus.style.display = "none"; return; }
        reserveStatus.style.display = "inline";
        if (current >= reserve) {
            reserveStatus.textContent = "Reserve Met";
            reserveStatus.className = "reserve-met";
        } else {
            reserveStatus.textContent = "Reserve: " + formatPrice(auction.reserve_price);
            reserveStatus.className = "reserve-pending";
        }
    }

    // ─── Countdown ─────────────────────────────────────────────────────
    function startCountdown(endIso) {
        auctionEndTime = new Date(endIso).getTime();
        if (countdownInterval) clearInterval(countdownInterval);

        function tick() {
            const now = Date.now();
            const diff = auctionEndTime - now;

            if (diff <= 0) {
                if (cdHours) cdHours.textContent = "00";
                if (cdMinutes) cdMinutes.textContent = "00";
                if (cdSeconds) cdSeconds.textContent = "00";
                if (countdownSection) countdownSection.classList.add("ended");
                clearInterval(countdownInterval);
                return;
            }

            const hours = Math.floor(diff / 3600000);
            const minutes = Math.floor((diff % 3600000) / 60000);
            const seconds = Math.floor((diff % 60000) / 1000);

            if (cdHours) cdHours.textContent = String(hours).padStart(2, "0");
            if (cdMinutes) cdMinutes.textContent = String(minutes).padStart(2, "0");
            if (cdSeconds) cdSeconds.textContent = String(seconds).padStart(2, "0");

            // Pulse effect when under 5 minutes
            if (diff < 300000 && countdownSection) {
                countdownSection.classList.add("urgent");
            }
        }

        tick();
        countdownInterval = setInterval(tick, 1000);
    }

    // ─── Bid Feed ──────────────────────────────────────────────────────
    function addBidToFeed(bid) {
        if (feedEmpty) feedEmpty.remove();

        const existing = bidFeed.querySelector('[data-bid-id="' + bid.bid_id + '"]');
        if (existing) return;

        const el = document.createElement("div");
        el.className = "feed-item new-bid";
        el.setAttribute("data-bid-id", bid.bid_id);
        el.innerHTML =
            '<div class="feed-bidder">' +
                '<span class="feed-avatar">' + bid.bidder.charAt(0).toUpperCase() + '</span>' +
                '<div><strong class="feed-name">' + escapeHtml(bid.bidder) + '</strong></div>' +
            '</div>' +
            '<div class="feed-amount">' +
                '<span class="feed-price">' + formatPrice(bid.amount) + '</span>' +
                '<span class="feed-time">Just now</span>' +
            '</div>';

        bidFeed.insertBefore(el, bidFeed.firstChild);

        // Remove "Leading" from all others, set on new top
        bidFeed.querySelectorAll(".feed-item").forEach(function (item, idx) {
            item.classList.toggle("leading", idx === 0);
            const badge = item.querySelector(".feed-leading");
            if (idx === 0 && !badge) {
                const div = item.querySelector(".feed-bidder div");
                if (div) {
                    const lb = document.createElement("span");
                    lb.className = "feed-leading";
                    lb.textContent = "Leading";
                    div.appendChild(lb);
                }
            } else if (badge) {
                badge.remove();
            }
        });

        // Animate in
        requestAnimationFrame(function () {
            el.classList.add("visible");
        });

        // Limit feed to 50 items
        while (bidFeed.children.length > 50) {
            bidFeed.removeChild(bidFeed.lastChild);
        }
    }

    function escapeHtml(str) {
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    function addHistoryEntry(h) {
        if (!historyFeed) return;
        const el = document.createElement("div");
        el.className = "history-item";
        el.innerHTML =
            '<span class="history-action action-' + h.action + '">' + h.action.replace(/_/g, " ") + '</span>' +
            '<span class="history-desc">' + escapeHtml(h.description || "") + '</span>' +
            '<span class="history-time">Just now</span>';
        historyFeed.insertBefore(el, historyFeed.firstChild);
        const empty = historyFeed.querySelector(".history-empty");
        if (empty) empty.remove();
        while (historyFeed.children.length > 50) {
            historyFeed.removeChild(historyFeed.lastChild);
        }
    }

    // ─── Connection Toast ──────────────────────────────────────────────
    function showConnection(state, msg) {
        if (!toast) return;
        toast.className = "connection-toast " + state;
        if (toastDot) toastDot.className = "toast-dot " + state;
        if (toastText) toastText.textContent = msg || state;
        toast.classList.add("visible");
        if (state === "connected") {
            setTimeout(function () { toast.classList.remove("visible"); }, 3000);
        }
    }

    // ─── Bid Input Validation ──────────────────────────────────────────
    if (bidAmountInput && placeBidBtn) {
        bidAmountInput.addEventListener("input", function () {
            const val = parseFloat(this.value);
            const min = parseFloat(this.min || 0);
            placeBidBtn.disabled = !(val > 0 && val >= min);
        });
    }

    // ─── WebSocket ─────────────────────────────────────────────────────
    function connect() {
        if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;

        socket = new WebSocket(WS_URL);
        showConnection("connecting", "Connecting...");

        socket.onopen = function () {
            isConnected = true;
            showConnection("connected", "Connected");
            if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
        };

        socket.onclose = function () {
            isConnected = false;
            showConnection("disconnected", "Disconnected");
            scheduleReconnect();
        };

        socket.onerror = function () {
            showConnection("error", "Connection error");
        };

        socket.onmessage = function (e) {
            try {
                var msg = JSON.parse(e.data);
            } catch (err) { return; }

            switch (msg.type) {
                case "auction_state":
                    if (msg.end_time) startCountdown(msg.end_time);
                    updateAuctionState(msg);
                    break;

                case "new_bid":
                    addBidToFeed(msg);
                    break;

                case "viewer_update":
                    if (viewersNum) viewersNum.textContent = msg.viewers || 0;
                    if (biddersNum) biddersNum.textContent = msg.online_bidders || 0;
                    break;

                case "auction_extended":
                    if (msg.new_end_time) startCountdown(msg.new_end_time);
                    showConnection("extended", "Extended +" + msg.extended_by + "min");
                    break;

                case "history_entry":
                    addHistoryEntry(msg);
                    break;

                case "bid_error":
                    if (bidErrorEl) {
                        bidErrorEl.textContent = msg.message;
                        bidErrorEl.style.display = "block";
                        setTimeout(function () { bidErrorEl.style.display = "none"; }, 5000);
                    }
                    break;

                case "pong":
                    break;
            }
        };
    }

    function scheduleReconnect() {
        if (reconnectTimer) return;
        showConnection("reconnecting", "Reconnecting...");
        reconnectTimer = setTimeout(function () {
            reconnectTimer = null;
            connect();
        }, 3000);
    }

    // ─── Place Bid ─────────────────────────────────────────────────────
    if (placeBidBtn) {
        placeBidBtn.addEventListener("click", function () {
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                if (bidErrorEl) {
                    bidErrorEl.textContent = "Not connected. Reconnecting...";
                    bidErrorEl.style.display = "block";
                }
                connect();
                return;
            }

            const amount = bidAmountInput ? bidAmountInput.value : "";
            if (!amount || parseFloat(amount) <= 0) return;

            placeBidBtn.disabled = true;
            placeBidBtn.classList.add("sending");
            placeBidBtn.querySelector(".btn-text").textContent = "Sending...";

            socket.send(JSON.stringify({
                type: "place_bid",
                amount: amount,
            }));
        });

        // Re-enable after sending
        var origSend = socket ? socket.send : null;
        // We'll re-enable on the next message or timeout
        document.addEventListener("click", function handler(e) {
            if (e.target === placeBidBtn) {
                setTimeout(function () {
                    if (placeBidBtn) {
                        placeBidBtn.disabled = false;
                        placeBidBtn.classList.remove("sending");
                        var txt = placeBidBtn.querySelector(".btn-text");
                        if (txt) txt.textContent = "Place Bid";
                    }
                }, 2000);
            }
        }, true);
    }

    // ─── Ping Keepalive ────────────────────────────────────────────────
    setInterval(function () {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ping" }));
        }
    }, 30000);

    // ─── Init ──────────────────────────────────────────────────────────
    connect();
})();
