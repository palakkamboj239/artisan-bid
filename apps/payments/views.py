"""
Payment views for ArtisanBid.
Handles checkout, verification, success/failure, history, and invoice display.
"""

import logging
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction as db_transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView, View

from apps.auctions.models import Auction, AuctionResult
from apps.payments.forms import PaymentForm
from apps.payments.models import Invoice, Payment, Transaction
from apps.payments.services import (
    create_razorpay_order,
    complete_payment,
)

logger = logging.getLogger(__name__)


# =========================================================================
# CHECKOUT  — Create order + show checkout page
# =========================================================================
class PaymentCheckoutView(LoginRequiredMixin, DetailView):
    """Display payment checkout for a won auction."""

    template_name = "payments/checkout.html"
    context_object_name = "auction"

    def get_object(self):
        return get_object_or_404(
            Auction.objects.select_related("artwork", "artwork__artist", "winner"),
            slug=self.kwargs["slug"],
            winner=self.request.user,
            status__in=("ended", "sold"),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        auction = self.object
        user = self.request.user

        # Check for existing payment
        existing = Payment.objects.filter(
            auction=auction, user=user
        ).order_by("-created_at").first()

        amount = auction.winning_bid or auction.current_bid or auction.starting_bid
        tax = amount * Decimal("0.00")  # Configure tax rate as needed
        total = amount + tax

        context["razorpay_key_id"] = settings.RAZORPAY_KEY_ID
        context["amount"] = amount
        context["tax_amount"] = tax
        context["total_amount"] = total
        context["existing_payment"] = existing
        context["callback_url"] = reverse("payments:verify", kwargs={"slug": auction.slug})

        return context


# =========================================================================
# INITIATE PAYMENT  — Create Razorpay order (AJAX endpoint)
# =========================================================================
class InitiatePaymentView(LoginRequiredMixin, View):
    """Create a Razorpay order and return order details as JSON."""

    def post(self, request, slug):
        auction = get_object_or_404(
            Auction, slug=slug, winner=request.user, status__in=("ended", "sold")
        )

        amount = auction.winning_bid or auction.current_bid or auction.starting_bid
        tax = amount * Decimal("0.00")
        total = amount + tax

        # Prevent duplicate payments
        if Payment.objects.filter(
            auction=auction, user=request.user, status=Payment.Status.SUCCESS
        ).exists():
            return JsonResponse({"error": "Payment already completed."}, status=400)

        with db_transaction.atomic():
            payment = Payment.objects.create(
                user=request.user,
                auction=auction,
                artwork=auction.artwork,
                amount=amount,
                tax_amount=tax,
                total_amount=total,
                currency="INR",
                buyer_email=request.user.email,
                status=Payment.Status.PENDING,
            )

            try:
                razorpay_order = create_razorpay_order(payment)
                order_id = razorpay_order["id"]
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

            Transaction.objects.create(
                payment=payment,
                user=request.user,
                action=Transaction.Action.ORDER_CREATED,
                description=f"Razorpay order {order_id} created",
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

        return JsonResponse({
            "order_id": order_id,
            "amount": int(total * 100),
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,
            "name": "ArtisanBid",
            "description": f"Payment for {auction.auction_title}",
            "prefill": {
                "name": request.user.get_full_name() or request.user.username,
                "email": request.user.email,
            },
        })


# =========================================================================
# VERIFY PAYMENT  — Server-side signature verification
# =========================================================================
class VerifyPaymentView(LoginRequiredMixin, View):
    """Verify Razorpay signature and mark payment complete."""

    def post(self, request, slug):
        form = PaymentForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Invalid payment verification data.")
            return redirect("payments:failed", slug=slug)

        payment = form.cleaned_data["_payment"]

        # Verify and complete
        success, message = complete_payment(
            payment,
            form.cleaned_data["razorpay_payment_id"],
            form.cleaned_data["razorpay_signature"],
            request=request,
        )

        if not success:
            messages.error(request, message)
            return redirect("payments:failed", slug=slug)

        messages.success(request, "Payment successful! Your invoice is ready.")
        return redirect("payments:success", slug=slug)


# =========================================================================
# PAYMENT SUCCESS
# =========================================================================
class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    template_name = "payments/success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        auction = get_object_or_404(
            Auction, slug=self.kwargs["slug"], winner=self.request.user
        )
        payment = get_object_or_404(
            Payment, auction=auction, user=self.request.user, status=Payment.Status.SUCCESS
        )
        context["auction"] = auction
        context["payment"] = payment
        context["invoice"] = getattr(payment, "invoice", None)
        return context


# =========================================================================
# PAYMENT FAILED
# =========================================================================
class PaymentFailedView(LoginRequiredMixin, TemplateView):
    template_name = "payments/failed.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        auction = get_object_or_404(
            Auction, slug=self.kwargs["slug"], winner=self.request.user
        )
        context["auction"] = auction
        context["retry_url"] = reverse("payments:checkout", kwargs={"slug": auction.slug})
        return context


# =========================================================================
# INVOICE VIEW
# =========================================================================
class InvoiceView(LoginRequiredMixin, DetailView):
    """Display a luxury invoice for a completed payment."""

    template_name = "payments/invoice.html"
    context_object_name = "invoice"

    def get_object(self):
        return get_object_or_404(
            Invoice.objects.select_related(
                "payment", "payment__user", "auction", "auction__artwork",
                "auction__artwork__artist",
            ),
            invoice_number=self.kwargs["invoice_number"],
            user=self.request.user,
        )


# =========================================================================
# PAYMENT HISTORY  — User's transaction history
# =========================================================================
class PaymentHistoryView(LoginRequiredMixin, ListView):
    """List all payments made by the current user."""

    template_name = "payments/history.html"
    context_object_name = "payments"
    paginate_by = 20

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).select_related(
            "auction", "auction__artwork", "auction__artwork__artist"
        ).order_by("-created_at")


# =========================================================================
# DOWNLOAD INVOICE  — Plain text invoice download
# =========================================================================
class DownloadInvoiceView(LoginRequiredMixin, View):
    """Return invoice as text for printing/download."""

    def get(self, request, invoice_number):
        invoice = get_object_or_404(
            Invoice.objects.select_related("payment", "auction", "auction__artwork"),
            invoice_number=invoice_number,
            user=request.user,
        )

        lines = [
            "=" * 60,
            "                    ARTISANBID",
            "              Premium Art Auction House",
            f"                Invoice #{invoice.invoice_number}",
            "=" * 60,
            "",
            f"Date: {invoice.issued_at.strftime('%B %d, %Y')}",
            f"Due:  {invoice.due_at.strftime('%B %d, %Y')}",
            "",
            "-" * 60,
            "  BILLED TO",
            f"  {invoice.user.get_full_name() or invoice.user.username}",
            f"  {invoice.user.email}",
            "",
            "-" * 60,
            "  ITEM",
            f"  Auction: {invoice.auction.auction_title}" if invoice.auction else "",
            f"  Amount: ${invoice.subtotal:,.2f}",
            f"  Tax:    ${invoice.tax_amount:,.2f}",
            f"  Total:  ${invoice.total:,.2f}",
            "",
            f"  Status: {'PAID' if invoice.is_paid else 'PENDING'}",
            f"  Payment: {invoice.payment.get_status_display() if invoice.payment else 'N/A'}",
            "",
            "=" * 60,
            "  Thank you for your purchase.",
            "  ArtisanBid — Where Art Meets Legacy",
            "=" * 60,
        ]

        response = HttpResponse("\n".join(lines), content_type="text/plain")
        response["Content-Disposition"] = f'attachment; filename="invoice_{invoice.invoice_number}.txt"'
        return response
