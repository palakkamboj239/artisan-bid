from django import forms
from django.utils import timezone

from apps.payments.models import Payment


class PaymentForm(forms.Form):
    """Secure payment form with validation."""

    razorpay_payment_id = forms.CharField(max_length=100, required=True)
    razorpay_order_id = forms.CharField(max_length=100, required=True)
    razorpay_signature = forms.CharField(max_length=255, required=True)

    def clean_razorpay_order_id(self):
        order_id = self.cleaned_data["razorpay_order_id"]
        try:
            payment = Payment.objects.get(razorpay_order_id=order_id)
        except Payment.DoesNotExist:
            raise forms.ValidationError("Invalid payment order.")

        # Prevent duplicate success
        if payment.status == Payment.Status.SUCCESS:
            raise forms.ValidationError("Payment already completed.")

        # Prevent expired orders (older than 1 hour)
        age = timezone.now() - payment.created_at
        if age.total_seconds() > 3600:
            raise forms.ValidationError("Payment order has expired.")

        self.cleaned_data["_payment"] = payment
        return order_id
