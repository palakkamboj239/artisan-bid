from django import forms
from django.utils import timezone

from apps.auctions.models import Auction, Bid


class BidForm(forms.Form):
    """Secure bid form with all validation logic."""

    bid_amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Enter your bid amount",
            "step": "0.01",
        }),
        label="Your Bid",
    )

    def __init__(self, *args, auction=None, user=None, **kwargs):
        self.auction = auction
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_bid_amount(self):
        amount = self.cleaned_data["bid_amount"]
        auction = self.auction

        # Guard: auction must exist
        if not auction:
            raise forms.ValidationError("Auction not found.")

        # Guard: auction must be live
        if auction.status != Auction.Status.LIVE:
            raise forms.ValidationError("This auction is not currently accepting bids.")

        # Guard: auction must not have ended
        if auction.end_time < timezone.now():
            raise forms.ValidationError("This auction has already ended.")

        # Guard: user must be logged in
        if not self.user or not self.user.is_authenticated:
            raise forms.ValidationError("You must be logged in to place a bid.")

        # Guard: seller cannot bid on own auction
        if auction.seller and self.user == auction.seller:
            raise forms.ValidationError("You cannot bid on your own auction.")

        # Guard: bid must exceed current bid
        min_bid = auction.minimum_next_bid()
        if amount < min_bid:
            raise forms.ValidationError(
                f"Your bid must be at least ${min_bid:,.2f} "
                f"(current bid ${auction.current_bid or auction.starting_bid:,.2f} "
                f"+ increment ${auction.bid_increment:,.2f})."
            )

        return amount
