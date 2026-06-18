from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView, View

from apps.auctions.forms import BidForm
from apps.auctions.models import Auction, AuctionWatchlist, Bid, BidHistory
from apps.auctions.signals import finalize_auction


# =========================================================================
# AUCTION LIST
# =========================================================================
class AuctionListView(ListView):
    """List all auctions, filterable by status."""

    model = Auction
    template_name = "auctions/auction_list.html"
    context_object_name = "auctions"
    paginate_by = 12

    def get_queryset(self):
        qs = Auction.objects.select_related("artwork", "artwork__artist", "seller")
        status = self.request.GET.get("status")
        if status and status in ("upcoming", "live", "ended", "sold", "cancelled"):
            qs = qs.filter(status=status)
        else:
            qs = qs.exclude(status="cancelled")
        return qs


# =========================================================================
# AUCTION DETAIL  (with bid form + history)
# =========================================================================
class AuctionDetailView(DetailView):
    """Full auction detail with bid form, history, and watchlist."""

    model = Auction
    template_name = "auctions/auction_detail.html"
    context_object_name = "auction"
    slug_field = "slug"

    def get_queryset(self):
        return Auction.objects.select_related(
            "artwork", "artwork__artist", "seller", "seller__profile"
        ).prefetch_related("bids", "history", "watchers")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        auction = self.object

        # Bid form
        context["bid_form"] = BidForm(auction=auction, user=self.request.user)

        # Top bids
        context["top_bids"] = auction.bids.select_related("bidder").order_by("-bid_amount")[:10]

        # Bid history (recent events)
        context["recent_history"] = auction.history.select_related("user").order_by("-timestamp")[:10]

        # Watchlist state
        if self.request.user.is_authenticated:
            context["is_watching"] = AuctionWatchlist.objects.filter(
                user=self.request.user, auction=auction
            ).exists()
        else:
            context["is_watching"] = False

        # Can the current user bid?
        context["can_bid"] = auction.can_bid(user=self.request.user) and self.request.user.is_authenticated

        return context


# =========================================================================
# PLACE BID
# =========================================================================
class PlaceBidView(LoginRequiredMixin, View):
    """Handle bid submission with full validation."""

    def post(self, request, slug):
        auction = get_object_or_404(Auction, slug=slug)
        form = BidForm(request.POST, auction=auction, user=request.user)

        if form.is_valid():
            amount = form.cleaned_data["bid_amount"]
            try:
                with transaction.atomic():
                    bid = Bid.objects.create(
                        auction=auction,
                        bidder=request.user,
                        bid_amount=amount,
                        ip_address=request.META.get("REMOTE_ADDR"),
                    )
                messages.success(
                    request,
                    f"Your bid of ${amount:,.2f} has been placed successfully!"
                )
            except Exception as e:
                messages.error(request, f"An error occurred while placing your bid: {e}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)

        return redirect("auctions:auction_detail", slug=slug)


# =========================================================================
# TOGGLE WATCHLIST
# =========================================================================
class ToggleWatchlistView(LoginRequiredMixin, View):
    """Add or remove an auction from the user's watchlist."""

    def post(self, request, slug):
        auction = get_object_or_404(Auction, slug=slug)
        watch, created = AuctionWatchlist.objects.get_or_create(
            user=request.user, auction=auction
        )
        if created:
            # Increment watcher count
            Auction.objects.filter(pk=auction.pk).update(
                total_watchers=models.F("total_watchers") + 1
            )
            messages.success(request, "Added to your watchlist.")
        else:
            watch.delete()
            Auction.objects.filter(pk=auction.pk).update(
                total_watchers=models.F("total_watchers") - 1
            )
            messages.info(request, "Removed from your watchlist.")

        return redirect("auctions:auction_detail", slug=slug)


# =========================================================================
# USER AUCTION DASHBOARD
# =========================================================================
class MyAuctionsView(LoginRequiredMixin, ListView):
    """Display the current user's auctions (bidding & selling)."""

    template_name = "auctions/my_auctions.html"
    context_object_name = "my_bids"
    paginate_by = 20

    def get_queryset(self):
        return Bid.objects.filter(bidder=self.request.user).select_related(
            "auction", "auction__artwork"
        ).order_by("-bid_time")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["my_sales"] = Auction.objects.filter(seller=self.request.user)
        context["my_watchlist"] = AuctionWatchlist.objects.filter(
            user=self.request.user
        ).select_related("auction", "auction__artwork")
        return context


# =========================================================================
# LIVE AUCTION ROOM  (WebSocket-powered real-time bidding)
# =========================================================================
class AuctionRoomView(DetailView):
    """Cinematic live auction room with WebSocket bidding."""

    model = Auction
    template_name = "auctions/auction_room.html"
    context_object_name = "auction"
    slug_field = "slug"

    def get_queryset(self):
        return Auction.objects.select_related(
            "artwork", "artwork__artist", "seller", "seller__profile"
        ).prefetch_related("bids", "history")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        auction = self.object
        context["top_bids"] = auction.bids.select_related("bidder").order_by("-bid_amount")[:15]
        context["can_bid"] = auction.can_bid(user=self.request.user) and self.request.user.is_authenticated
        if self.request.user.is_authenticated:
            context["is_watching"] = AuctionWatchlist.objects.filter(
                user=self.request.user, auction=auction
            ).exists()
        else:
            context["is_watching"] = False
        return context
