"""
Premium payment models for ArtisanBid auction platform.
Supports Razorpay with Stripe-compatible architecture.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.auctions.models import Auction
from apps.artworks.models import Artwork


# =========================================================================
# PAYMENT  — Core payment record for auction wins
# =========================================================================
class Payment(models.Model):
    """Secure payment record tied to an auction result."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SUCCESS = "success", _("Success")
        FAILED = "failed", _("Failed")
        REFUNDED = "refunded", _("Refunded")

    class PaymentMethod(models.TextChoices):
        RAZORPAY = "razorpay", _("Razorpay")
        STRIPE = "stripe", _("Stripe")
        BANK_TRANSFER = "bank_transfer", _("Bank Transfer")
        CRYPTO = "crypto", _("Cryptocurrency")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    auction = models.ForeignKey(
        Auction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    artwork = models.ForeignKey(
        Artwork,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )

    # Razorpay fields
    razorpay_order_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    # Amount
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")

    # Status
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.RAZORPAY,
    )

    # Metadata
    paid_at = models.DateTimeField(null=True, blank=True)
    buyer_email = models.EmailField(blank=True)
    buyer_phone = models.CharField(max_length=20, blank=True)
    billing_address = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"Payment {self.id} — {self.user.username} — {self.get_status_display()}"

    def mark_success(self, payment_id, signature):
        """Mark payment as successful after signature verification."""
        self.status = self.Status.SUCCESS
        self.razorpay_payment_id = payment_id
        self.razorpay_signature = signature
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "razorpay_payment_id", "razorpay_signature", "paid_at", "updated_at"])

    def mark_failed(self):
        self.status = self.Status.FAILED
        self.save(update_fields=["status", "updated_at"])


# =========================================================================
# TRANSACTION  — Gateway-level audit log
# =========================================================================
class Transaction(models.Model):
    """Immutable audit log for every gateway interaction."""

    class Action(models.TextChoices):
        ORDER_CREATED = "order_created", _("Order Created")
        PAYMENT_INITIATED = "payment_initiated", _("Payment Initiated")
        PAYMENT_SUCCESS = "payment_success", _("Payment Success")
        PAYMENT_FAILED = "payment_failed", _("Payment Failed")
        PAYMENT_REFUNDED = "payment_refunded", _("Payment Refunded")
        VERIFICATION_SUCCESS = "verification_success", _("Verification Success")
        VERIFICATION_FAILED = "verification_failed", _("Verification Failed")
        WEBHOOK_RECEIVED = "webhook_received", _("Webhook Received")

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=25, choices=Action.choices)
    gateway = models.CharField(max_length=20, default="razorpay")

    # Raw gateway response
    gateway_response = models.JSONField(blank=True, default=dict)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)

    # Fraud / security
    fraud_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    is_suspicious = models.BooleanField(default=False)

    # Metadata
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self):
        return f"[{self.get_action_display()}] Payment {self.payment_id}"


# =========================================================================
# INVOICE  — Luxury invoice record
# =========================================================================
class Invoice(models.Model):
    """Professional luxury invoice for won auctions."""

    invoice_number = models.CharField(max_length=50, unique=True)
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name="invoice",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    auction = models.ForeignKey(
        Auction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # Financial details
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    buyer_premium = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    shipping = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=14, decimal_places=2)

    # Dates
    issued_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField()

    # Status
    is_paid = models.BooleanField(default=False)

    class Meta:
        ordering = ("-issued_at",)
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"

    def __str__(self):
        return f"Invoice #{self.invoice_number}"

    def generate_number(self):
        """Generate a unique invoice number: INV-2026-00001"""
        prefix = f"INV-{timezone.now().year}-"
        last = Invoice.objects.filter(invoice_number__startswith=prefix).count()
        return f"{prefix}{last + 1:05d}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_number()
        super().save(*args, **kwargs)
