from django.contrib import admin
from django.utils.html import format_html

from apps.payments.models import Payment, Transaction, Invoice


# =========================================================================
# INLINE
# =========================================================================
class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    fields = ("action", "gateway", "ip_address", "is_suspicious", "created_at")
    readonly_fields = ("action", "gateway", "ip_address", "is_suspicious", "created_at")
    ordering = ("-created_at",)

    def has_add_permission(self, request, obj=None):
        return False


# =========================================================================
# PAYMENT ADMIN
# =========================================================================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    inlines = [TransactionInline]
    list_display = (
        "payment_id_display",
        "user",
        "amount_display",
        "status_colored",
        "payment_method",
        "razorpay_order_id",
        "paid_at",
        "created_at",
    )
    list_display_links = ("payment_id_display",)
    list_filter = ("status", "payment_method", "currency", "created_at")
    search_fields = ("user__username", "razorpay_order_id", "razorpay_payment_id", "auction__auction_title")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    readonly_fields = (
        "razorpay_order_id",
        "razorpay_payment_id",
        "razorpay_signature",
        "status",
        "paid_at",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Buyer", {"fields": ("user", "buyer_email", "buyer_phone")}),
        ("Auction Item", {"fields": ("auction", "artwork")}),
        ("Amounts", {"fields": ("amount", "tax_amount", "total_amount", "currency")}),
        ("Payment Gateway", {"fields": ("payment_method", "razorpay_order_id", "razorpay_payment_id", "razorpay_signature")}),
        ("Status", {"fields": ("status", "paid_at")}),
        ("Details", {"fields": ("billing_address", "notes"), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def payment_id_display(self, obj):
        return f"#{obj.id}"
    payment_id_display.short_description = "Payment ID"

    def amount_display(self, obj):
        return f"{obj.currency} {obj.total_amount:,.2f}"
    amount_display.short_description = "Amount"

    def status_colored(self, obj):
        colors = {
            "pending": "#c9a84c",
            "success": "#28a745",
            "failed": "#dc3545",
            "refunded": "#6c757d",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color:{};font-weight:600;">●</span> {}',
            color,
            obj.get_status_display(),
        )
    status_colored.short_description = "Status"

    actions = ["mark_as_refunded"]

    def mark_as_refunded(self, request, queryset):
        updated = queryset.update(status="refunded")
        self.message_user(request, f"{updated} payment(s) marked as refunded.")
    mark_as_refunded.short_description = "Mark selected as Refunded"


# =========================================================================
# TRANSACTION ADMIN
# =========================================================================
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("payment", "action_colored", "gateway", "ip_address", "is_suspicious", "created_at")
    list_filter = ("action", "gateway", "is_suspicious", "created_at")
    search_fields = ("payment__razorpay_order_id", "description", "ip_address")
    date_hierarchy = "created_at"
    readonly_fields = ("payment", "user", "action", "gateway", "gateway_response", "ip_address", "created_at")

    def action_colored(self, obj):
        colors = {
            "payment_success": "#28a745",
            "payment_failed": "#dc3545",
            "verification_failed": "#dc3545",
        }
        color = colors.get(obj.action, "#6c757d")
        return format_html('<span style="color:{};">●</span> {}', color, obj.get_action_display())
    action_colored.short_description = "Action"

    def has_add_permission(self, request):
        return False


# =========================================================================
# INVOICE ADMIN
# =========================================================================
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "user", "total_display", "is_paid", "issued_at", "due_at")
    list_filter = ("is_paid", "issued_at")
    search_fields = ("invoice_number", "user__username", "auction__auction_title")
    date_hierarchy = "issued_at"
    readonly_fields = ("invoice_number", "payment", "user", "subtotal", "total", "issued_at", "paid_at")

    def total_display(self, obj):
        return f"${obj.total:,.2f}"
    total_display.short_description = "Total"
