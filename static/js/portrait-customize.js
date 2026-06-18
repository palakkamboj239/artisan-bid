/**
 * ArtisanBid Studio – Portrait Customization + Reference Upload System
 * Handles live pricing engine, image upload/preview, add-to-cart.
 */
(function () {
    'use strict';

    var PortraitCustomizer = {

        config: {
            basePrice: 0,
            currency: 'INR',
            maxUploads: 5,
            productId: null,
        },

        elements: {},

        /**
         * Initialize with configuration from Django template.
         */
        init: function (cfg) {
            this.config = Object.assign(this.config, cfg || {});
            this.cacheElements();
            this.attachListeners();
            this.attachUploadHandlers();
            this.attachCartHandler();
            this.update();
            this.updateUploadCount();
        },

        /**
         * Cache DOM elements.
         */
        cacheElements: function () {
            this.elements = {
                sizeRadios: document.querySelectorAll('input[name="size"]'),
                sizeLabels: document.querySelectorAll('.size-selector'),
                canvasRadios: document.querySelectorAll('input[name="canvas"]'),
                canvasLabels: document.querySelectorAll('.canvas-selector'),
                frameRadios: document.querySelectorAll('input[name="frame"]'),
                frameLabels: document.querySelectorAll('.frame-selector'),
                sketchRadios: document.querySelectorAll('input[name="sketch_type"]'),
                sketchLabels: document.querySelectorAll('.sketch-selector'),
                summarySize: document.getElementById('summarySize'),
                summaryCanvas: document.getElementById('summaryCanvas'),
                summaryFrame: document.getElementById('summaryFrame'),
                summarySketch: document.getElementById('summarySketch'),
                summaryBasePrice: document.getElementById('summaryBasePrice'),
                summaryMultiplier: document.getElementById('summaryMultiplier'),
                summaryCanvasPrice: document.getElementById('summaryCanvasPrice'),
                summaryFramePrice: document.getElementById('summaryFramePrice'),
                summarySketchPrice: document.getElementById('summarySketchPrice'),
                summaryTotal: document.getElementById('summaryTotal'),
                summaryRefCount: document.getElementById('summaryRefCount'),
                addToCartBtn: document.getElementById('addToCartBtn'),
                addToCartPrice: document.getElementById('addToCartPrice'),
                uploadZone: document.getElementById('uploadZone'),
                uploadInput: document.getElementById('referenceImageInput'),
                uploadBrowseBtn: document.getElementById('uploadBrowseBtn'),
                uploadPreviews: document.getElementById('uploadPreviews'),
                uploadProgress: document.getElementById('uploadProgress'),
                uploadCount: document.getElementById('uploadCount'),
                uploadHint: document.getElementById('uploadHint'),
            };
        },

        /**
         * Attach change listeners to selector radio groups.
         */
        attachListeners: function () {
            var self = this;

            function handleChange(groupRadios, groupLabels) {
                groupRadios.forEach(function (radio) {
                    radio.addEventListener('change', function () {
                        groupLabels.forEach(function (l) { l.classList.remove('selected'); });
                        var parent = self.findParentLabel(this);
                        if (parent) parent.classList.add('selected');
                        self.update();
                    });
                });
            }

            handleChange(this.elements.sizeRadios, this.elements.sizeLabels);
            handleChange(this.elements.canvasRadios, this.elements.canvasLabels);
            handleChange(this.elements.frameRadios, this.elements.frameLabels);
            handleChange(this.elements.sketchRadios, this.elements.sketchLabels);
        },

        // -----------------------------------------------------------------------
        // UPLOAD HANDLERS
        // -----------------------------------------------------------------------

        attachUploadHandlers: function () {
            var self = this;
            var zone = this.elements.uploadZone;
            var input = this.elements.uploadInput;
            var browseBtn = this.elements.uploadBrowseBtn;

            if (!zone || !input) return;

            // Browse button click
            if (browseBtn) {
                browseBtn.addEventListener('click', function (e) {
                    e.stopPropagation();
                    input.click();
                });
            }

            // Zone click (delegates to input)
            zone.addEventListener('click', function (e) {
                if (e.target === browseBtn || e.target.closest('.upload-preview-remove')) return;
                input.click();
            });

            // File input change
            input.addEventListener('change', function () {
                self.handleFiles(this.files);
                this.value = '';
            });

            // Drag-and-drop
            zone.addEventListener('dragover', function (e) {
                e.preventDefault();
                zone.classList.add('dragover');
            });

            zone.addEventListener('dragleave', function () {
                zone.classList.remove('dragover');
            });

            zone.addEventListener('drop', function (e) {
                e.preventDefault();
                zone.classList.remove('dragover');
                if (e.dataTransfer.files.length) {
                    self.handleFiles(e.dataTransfer.files);
                }
            });

            // Remove buttons (existing + future)
            this.elements.uploadPreviews.addEventListener('click', function (e) {
                var removeBtn = e.target.closest('.upload-preview-remove');
                if (removeBtn) {
                    var imageId = removeBtn.getAttribute('data-image-id');
                    if (imageId) self.deleteImage(imageId);
                }
            });
        },

        /**
         * Handle selected/dropped files.
         */
        handleFiles: function (files) {
            var self = this;
            var currentCount = document.querySelectorAll('.upload-preview-card').length;

            for (var i = 0; i < files.length; i++) {
                if (currentCount >= this.config.maxUploads) {
                    this.showError('Maximum ' + this.config.maxUploads + ' images allowed.');
                    break;
                }

                var file = files[i];

                // Client-side validation
                var allowed = ['image/jpeg', 'image/png', 'image/webp'];
                if (allowed.indexOf(file.type) === -1) {
                    this.showError('Only JPG, PNG, and WebP images are allowed.');
                    continue;
                }
                if (file.size > 5 * 1024 * 1024) {
                    this.showError('Each image must be under 5 MB.');
                    continue;
                }

                this.uploadFile(file);
                currentCount++;
            }
        },

        /**
         * Upload a single file via AJAX.
         */
        uploadFile: function (file) {
            var self = this;
            var formData = new FormData();
            formData.append('image', file);

            this.showProgress(true);

            fetch('/portraits/api/upload-reference/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRF(),
                },
                body: formData,
            })
                .then(function (r) { return r.json(); })
                .then(function (res) {
                    self.showProgress(false);
                    if (res.success) {
                        self.addPreviewCard(res.id, res.url);
                        self.updateUploadCount();
                        self.showSuccess('Image uploaded successfully.');
                    } else {
                        self.showError(res.error || 'Upload failed.');
                    }
                })
                .catch(function () {
                    self.showProgress(false);
                    self.showError('Upload failed. Please try again.');
                });
        },

        /**
         * Delete an uploaded image.
         */
        deleteImage: function (imageId) {
            var self = this;

            fetch('/portraits/api/delete-reference/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRF(),
                },
                body: JSON.stringify({ image_id: parseInt(imageId) }),
            })
                .then(function (r) { return r.json(); })
                .then(function (res) {
                    if (res.success) {
                        var card = document.querySelector('.upload-preview-card[data-image-id="' + imageId + '"]');
                        if (card) {
                            card.style.opacity = '0';
                            card.style.transform = 'scale(0.8)';
                            setTimeout(function () { card.remove(); self.updateUploadCount(); }, 300);
                        }
                    } else {
                        self.showError(res.error || 'Delete failed.');
                    }
                })
                .catch(function () {
                    self.showError('Delete failed. Please try again.');
                });
        },

        /**
         * Add a preview card to the upload previews container.
         */
        addPreviewCard: function (id, url) {
            var card = document.createElement('div');
            card.className = 'upload-preview-card fade-in';
            card.setAttribute('data-image-id', id);
            card.innerHTML =
                '<img src="' + url + '" alt="Reference" />' +
                '<button type="button" class="upload-preview-remove" data-image-id="' + id + '" title="Remove">×</button>' +
                '<div class="upload-preview-check">✓</div>';

            this.elements.uploadPreviews.appendChild(card);

            // Re-bind remove for new card
            var removeBtn = card.querySelector('.upload-preview-remove');
            if (removeBtn) {
                removeBtn.addEventListener('click', function (e) {
                    e.stopPropagation();
                    self.deleteImage(id);
                });
            }
        },

        // -----------------------------------------------------------------------
        // UI HELPERS
        // -----------------------------------------------------------------------

        updateUploadCount: function () {
            var count = document.querySelectorAll('.upload-preview-card').length;
            if (this.elements.uploadCount) {
                this.elements.uploadCount.textContent = count;
            }
            if (this.elements.summaryRefCount) {
                this.elements.summaryRefCount.textContent = count;
            }
        },

        showProgress: function (visible) {
            if (!this.elements.uploadProgress) return;
            if (visible) {
                this.elements.uploadProgress.classList.remove('d-none');
            } else {
                this.elements.uploadProgress.classList.add('d-none');
            }
        },

        showError: function (msg) {
            var hint = this.elements.uploadHint;
            if (hint) {
                hint.innerHTML = '<span class="upload-error">' + msg + '</span>';
                setTimeout(function () { self.updateUploadCount(); }, 3000);
            }
        },

        showSuccess: function (msg) {
            var hint = this.elements.uploadHint;
            if (hint) {
                var count = document.querySelectorAll('.upload-preview-card').length;
                hint.innerHTML = '<span class="upload-success">' + msg + '</span>';
                setTimeout(function () { self.updateUploadCount(); }, 2000);
            }
        },

        getCSRF: function () {
            var csrf = document.querySelector('[name=csrfmiddlewaretoken]');
            return csrf ? csrf.value : '';
        },

        // -----------------------------------------------------------------------
        // ADD TO CART
        // -----------------------------------------------------------------------

        attachCartHandler: function () {
            var self = this;
            var btn = this.elements.addToCartBtn;
            if (!btn) return;

            btn.addEventListener('click', function () {
                self.addToCart();
            });
        },

        getSelectedValue: function (radios) {
            for (var i = 0; i < radios.length; i++) {
                if (radios[i].checked) return radios[i].value;
            }
            return null;
        },

        addToCart: function () {
            var self = this;
            var btn = this.elements.addToCartBtn;
            if (!btn) return;

            btn.classList.add('loading');
            btn.textContent = 'Adding...';

            var referenceIds = [];
            document.querySelectorAll('.upload-preview-card').forEach(function (card) {
                var id = card.getAttribute('data-image-id');
                if (id) referenceIds.push(parseInt(id));
            });

            var payload = {
                product_id: this.config.productId,
                size_id: this.getSelectedValue(this.elements.sizeRadios),
                canvas_id: this.getSelectedValue(this.elements.canvasRadios),
                frame_id: this.getSelectedValue(this.elements.frameRadios),
                sketch_type_id: this.getSelectedValue(this.elements.sketchRadios),
                quantity: 1,
                reference_image_ids: referenceIds,
            };

            fetch('/portraits/api/add-to-cart/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRF(),
                },
                body: JSON.stringify(payload),
            })
                .then(function (r) { return r.json(); })
                .then(function (res) {
                    btn.classList.remove('loading');
                    if (res.success) {
                        btn.classList.add('added');
                        btn.textContent = 'Added to Cart ✓';
                        self.showCartToast(res.cart_count);
                        self.updateCartBadge(res.cart_count);
                    } else {
                        btn.textContent = 'Add to Cart — ' + self.getTotalText();
                        self.showError(res.error || 'Failed to add to cart.');
                    }
                })
                .catch(function () {
                    btn.classList.remove('loading');
                    btn.textContent = 'Add to Cart — ' + self.getTotalText();
                    self.showError('Failed to add to cart.');
                });
        },

        showCartToast: function (count) {
            var existing = document.querySelector('.cart-toast');
            if (existing) existing.remove();

            var toast = document.createElement('div');
            toast.className = 'cart-toast';
            toast.innerHTML =
                '<span class="cart-toast-icon">✓</span>' +
                '<span class="cart-toast-text">Added to cart. <strong>' + count + '</strong> item(s) in cart</span>';

            document.body.appendChild(toast);
            setTimeout(function () { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; }, 3000);
            setTimeout(function () { if (toast.parentNode) toast.remove(); }, 3500);
        },

        updateCartBadge: function (count) {
            var badge = document.getElementById('cartBadge');
            if (badge) {
                badge.textContent = count;
            } else {
                var cartLink = document.querySelector('a[href*="cart"]');
                if (cartLink && count > 0) {
                    var newBadge = document.createElement('span');
                    newBadge.className = 'cart-badge';
                    newBadge.id = 'cartBadge';
                    newBadge.textContent = count;
                    cartLink.appendChild(newBadge);
                }
            }
        },

        getTotalText: function () {
            var el = this.elements.summaryTotal;
            return el ? el.textContent : '';
        },

        // -----------------------------------------------------------------------
        // PRICING ENGINE
        // -----------------------------------------------------------------------

        findParentLabel: function (input) {
            return input.closest('.size-selector') ||
                   input.closest('.canvas-selector') ||
                   input.closest('.frame-selector') ||
                   input.closest('.sketch-selector');
        },

        getLabelText: function (label, selector) {
            var el = label ? label.querySelector(selector) : null;
            return el ? el.textContent.trim() : '—';
        },

        getCheckedData: function (radios, attr) {
            for (var i = 0; i < radios.length; i++) {
                if (radios[i].checked) return radios[i].getAttribute(attr);
            }
            return null;
        },

        getCheckedLabel: function (radios, labels) {
            for (var i = 0; i < radios.length; i++) {
                if (radios[i].checked) {
                    for (var j = 0; j < labels.length; j++) {
                        if (labels[j].contains(radios[i])) return labels[j];
                    }
                }
            }
            return null;
        },

        update: function () {
            var self = this;

            var sizeMultiplier = parseFloat(
                self.getCheckedData(self.elements.sizeRadios, 'data-price-multiplier') || '1.00'
            );
            var canvasAdjustment = parseFloat(
                self.getCheckedData(self.elements.canvasRadios, 'data-price-adjustment') || '0'
            );
            var frameAdjustment = parseFloat(
                self.getCheckedData(self.elements.frameRadios, 'data-price-adjustment') || '0'
            );
            var sketchAdjustment = parseFloat(
                self.getCheckedData(self.elements.sketchRadios, 'data-price-adjustment') || '0'
            );

            var basePrice = self.config.basePrice;
            var sizeAppliedPrice = basePrice * sizeMultiplier;
            var total = sizeAppliedPrice + canvasAdjustment + frameAdjustment + sketchAdjustment;

            var sizeLabel = self.getCheckedLabel(self.elements.sizeRadios, self.elements.sizeLabels);
            var canvasLabel = self.getCheckedLabel(self.elements.canvasRadios, self.elements.canvasLabels);
            var frameLabel = self.getCheckedLabel(self.elements.frameRadios, self.elements.frameLabels);
            var sketchLabel = self.getCheckedLabel(self.elements.sketchRadios, self.elements.sketchLabels);

            if (self.elements.summarySize) {
                self.elements.summarySize.textContent = self.getLabelText(sizeLabel, '.size-name');
            }
            if (self.elements.summaryCanvas) {
                self.elements.summaryCanvas.textContent = self.getLabelText(canvasLabel, '.canvas-name');
            }
            if (self.elements.summaryFrame) {
                self.elements.summaryFrame.textContent = frameLabel && frameLabel.dataset.frameId !== ''
                    ? self.getLabelText(frameLabel, '.frame-name') : 'No Frame';
            }
            if (self.elements.summarySketch) {
                self.elements.summarySketch.textContent = self.getLabelText(sketchLabel, '.sketch-name');
            }

            if (self.elements.summaryBasePrice) {
                self.elements.summaryBasePrice.textContent = self.formatPrice(basePrice);
            }
            if (self.elements.summaryMultiplier) {
                self.elements.summaryMultiplier.textContent = sizeMultiplier.toFixed(2) + '×';
            }
            if (self.elements.summaryCanvasPrice) {
                self.elements.summaryCanvasPrice.textContent = canvasAdjustment > 0
                    ? '+' + self.formatPrice(canvasAdjustment) : '—';
            }
            if (self.elements.summaryFramePrice) {
                self.elements.summaryFramePrice.textContent = frameAdjustment > 0
                    ? '+' + self.formatPrice(frameAdjustment) : '—';
            }
            if (self.elements.summarySketchPrice) {
                self.elements.summarySketchPrice.textContent = sketchAdjustment > 0
                    ? '+' + self.formatPrice(sketchAdjustment) : '—';
            }
            if (self.elements.summaryTotal) {
                self.elements.summaryTotal.textContent = self.formatPrice(total);
            }
            if (self.elements.addToCartPrice) {
                self.elements.addToCartPrice.textContent = self.formatPrice(total);
            }
        },

        formatPrice: function (amount) {
            return '₹' + Math.round(amount).toLocaleString('en-IN');
        },
    };

    window.PortraitCustomizer = PortraitCustomizer;
})();
