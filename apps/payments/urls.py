from django.urls import path

from apps.payments import views

app_name = "payments"

urlpatterns = [
    # Checkout
    path("<slug:slug>/checkout/", views.PaymentCheckoutView.as_view(), name="checkout"),
    # Initiate (AJAX)
    path("<slug:slug>/initiate/", views.InitiatePaymentView.as_view(), name="initiate"),
    # Verify (callback from Razorpay)
    path("<slug:slug>/verify/", views.VerifyPaymentView.as_view(), name="verify"),
    # Success / Failure
    path("<slug:slug>/success/", views.PaymentSuccessView.as_view(), name="success"),
    path("<slug:slug>/failed/", views.PaymentFailedView.as_view(), name="failed"),
    # History
    path("history/", views.PaymentHistoryView.as_view(), name="history"),
    # Invoice
    path("invoice/<str:invoice_number>/", views.InvoiceView.as_view(), name="invoice"),
    path("invoice/<str:invoice_number>/download/", views.DownloadInvoiceView.as_view(), name="download_invoice"),
]
