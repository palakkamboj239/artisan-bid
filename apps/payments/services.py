"""
Razorpay payment service for ArtisanBid.
Handles order creation, signature verification, and gateway interaction.
"""

import json
import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.payments.models import Payment

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Razorpay client factory
# ---------------------------------------------------------------------------
def get_razorpay_client():
    """Return a configured Razorpay client using environment keys."""
    try:
        import razorpay
        return razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    except ImportError:
        logger.warning("razorpay SDK not installed — using mock client")
        return MockRazorpayClient()


# ---------------------------------------------------------------------------
#  Mock client for development without Razorpay keys
# ---------------------------------------------------------------------------
class MockRazorpayClient:
    """Local mock that simulates Razorpay without hitting the API."""

    def __init__(self):
        self._orders = {}

    def order(self, data=None):
        class OrderResponse(dict):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                self.__dict__ = self

        if data is None:
            return self._orders

        order_id = f"order_MOCK_{len(self._orders) + 1:06d}"
        order = OrderResponse({
            "id": order_id,
            "entity": "order",
            "amount": data.get("amount", 0),
            "currency": data.get("currency", "INR"),
            "receipt": data.get("receipt", ""),
            "status": "created",
            "attempts": 0,
            "notes": data.get("notes", {}),
        })
        self._orders[order_id] = order
        return order

    def utility(self):
        return self.Utility(self)

    class Utility:
        def __init__(self, client):
            self.client = client

        def verify_payment_signature(self, data):
            """Accept all signatures in mock mode."""
            return True


# ---------------------------------------------------------------------------
#  Order creation
# ---------------------------------------------------------------------------
def create_razorpay_order(payment, receipt=None):
    """
    Create a Razorpay order for a Payment record.
    Returns the order dict with 'id', 'amount', 'currency'.
    """
    client = get_razorpay_client()
    amount_paise = int(payment.total_amount * 100)  # Razorpay uses paise

    order_data = {
        "amount": amount_paise,
        "currency": payment.currency,
        "receipt": receipt or f"pay_{payment.id}",
        "notes": {
            "payment_id": str(payment.id),
            "user": payment.user.username,
            "auction": str(payment.auction_id or ""),
        },
    }

    try:
        razorpay_order = client.order.create(data=order_data)
        payment.razorpay_order_id = razorpay_order["id"]
        payment.save(update_fields=["razorpay_order_id", "updated_at"])
        logger.info(f"Razorpay order created: {razorpay_order['id']}")
        return razorpay_order
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        raise


# ---------------------------------------------------------------------------
#  Signature verification
# ---------------------------------------------------------------------------
def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    """
    Verify Razorpay payment signature to confirm payment authenticity.
    Never trust frontend data — always verify server-side.
    """
    client = get_razorpay_client()
    params = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature,
    }

    try:
        is_valid = client.utility.verify_payment_signature(params)
        if not is_valid:
            logger.warning(f"Signature verification FAILED for order {razorpay_order_id}")
        return is_valid
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


# ---------------------------------------------------------------------------
#  Complete payment flow (transaction-safe)
# ---------------------------------------------------------------------------
def complete_payment(payment, razorpay_payment_id, razorpay_signature, request=None):
    """
    Verify signature and mark payment as complete within a transaction.
    Returns (success: bool, message: str).
    """
    with db_transaction.atomic():
        # Reload payment within transaction
        payment = Payment.objects.select_for_update().get(pk=payment.pk)

        # Guard: prevent duplicate processing
        if payment.status == Payment.Status.SUCCESS:
            return False, "Payment already completed."

        # Verify signature
        is_valid = verify_payment_signature(
            payment.razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature,
        )
        if not is_valid:
            payment.mark_failed()
            _log_transaction(payment, "verification_failed", request,
                             "Signature verification failed")
            return False, "Payment verification failed."

        # Mark success
        payment.mark_success(razorpay_payment_id, razorpay_signature)

        # Update auction result
        _update_auction_result(payment)

        # Create invoice
        from apps.payments.models import Invoice
        invoice = Invoice.objects.create(
            payment=payment,
            user=payment.user,
            auction=payment.auction,
            subtotal=payment.amount,
            total=payment.total_amount,
            tax_amount=payment.tax_amount,
            due_at=timezone.now() + timezone.timedelta(days=7),
            is_paid=True,
            paid_at=timezone.now(),
        )

        _log_transaction(payment, "payment_success", request,
                         f"Payment completed: {razorpay_payment_id}")

    return True, "Payment successful."


def _update_auction_result(payment):
    """Update AuctionResult payment status when payment completes."""
    try:
        result = payment.auction.result
        result.payment_status = "paid"
        result.payment_date = timezone.now()
        result.save(update_fields=["payment_status", "payment_date"])
    except Exception:
        pass


def _log_transaction(payment, action, request, description=""):
    """Create an immutable Transaction audit record."""
    from apps.payments.models import Transaction
    Transaction.objects.create(
        payment=payment,
        user=payment.user,
        action=action,
        description=description,
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
    )
