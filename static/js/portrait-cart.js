(function () {
    'use strict';

    var PortraitCart = {

        init: function () {
            this.attachHandlers();
        },

        attachHandlers: function () {
            var self = this;

            // Quantity minus
            document.querySelectorAll('.qty-minus').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    var itemId = this.getAttribute('data-item-id');
                    var qtyEl = document.getElementById('qty-' + itemId);
                    var val = parseInt(qtyEl.textContent);
                    if (val > 1) self.updateQuantity(itemId, val - 1);
                });
            });

            // Quantity plus
            document.querySelectorAll('.qty-plus').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    var itemId = this.getAttribute('data-item-id');
                    var qtyEl = document.getElementById('qty-' + itemId);
                    var val = parseInt(qtyEl.textContent);
                    self.updateQuantity(itemId, val + 1);
                });
            });

            // Remove
            document.querySelectorAll('.btn-remove-item').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    var itemId = this.getAttribute('data-item-id');
                    self.removeItem(itemId);
                });
            });
        },

        getCSRF: function () {
            var csrf = document.querySelector('[name=csrfmiddlewaretoken]');
            return csrf ? csrf.value : '';
        },

        updateQuantity: function (itemId, quantity) {
            var qtyEl = document.getElementById('qty-' + itemId);
            if (!qtyEl) return;

            fetch('/portraits/api/update-cart-item/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRF(),
                },
                body: JSON.stringify({ item_id: parseInt(itemId), quantity: quantity }),
            })
                .then(function (r) { return r.json(); })
                .then(function (res) {
                    if (res.success) {
                        qtyEl.textContent = res.quantity;
                        self.updateSummary(res.cart_subtotal, res.cart_count);
                        self.updateItemTotal(itemId, res.item_total);
                    }
                })
                .catch(function () {});
        },

        removeItem: function (itemId) {
            var card = document.querySelector('.cart-item-card[data-item-id="' + itemId + '"]');
            if (!card) return;

            fetch('/portraits/api/remove-cart-item/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRF(),
                },
                body: JSON.stringify({ item_id: parseInt(itemId) }),
            })
                .then(function (r) { return r.json(); })
                .then(function (res) {
                    if (res.success) {
                        card.classList.add('cart-item-removing');
                        setTimeout(function () {
                            card.remove();
                            self.updateSummary(res.cart_subtotal, res.cart_count);
                            self.checkEmpty();
                        }, 300);
                    }
                })
                .catch(function () {});
        },

        updateSummary: function (subtotal, count) {
            var subEl = document.getElementById('cartSubtotal');
            var totalEl = document.getElementById('cartTotal');
            if (subEl) subEl.textContent = '₹' + parseInt(subtotal).toLocaleString('en-IN');
            if (totalEl) totalEl.textContent = '₹' + parseInt(subtotal).toLocaleString('en-IN');

            var badge = document.getElementById('cartBadge');
            if (badge) badge.textContent = count;
        },

        updateItemTotal: function (itemId, total) {
            var card = document.querySelector('.cart-item-card[data-item-id="' + itemId + '"]');
            if (!card) return;
            var totalEl = card.querySelector('.cart-item-total');
            if (totalEl) totalEl.textContent = '₹' + parseInt(total).toLocaleString('en-IN');
        },

        checkEmpty: function () {
            var remaining = document.querySelectorAll('.cart-item-card').length;
            if (remaining === 0) {
                window.location.reload();
            }
        },
    };

    window.PortraitCart = PortraitCart;
})();
