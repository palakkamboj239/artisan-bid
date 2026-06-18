from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone

from apps.artworks.models import Artwork


# =========================================================================
# AUCTION  —  Core auction listing
# =========================================================================
class Auction(models.Model):
    """A timed auction sale for a single artwork."""

    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        LIVE = "live", "Live"
        ENDED = "ended", "Ended"
        SOLD = "sold", "Sold"
        CANCELLED = "cancelled", "Cancelled"

    artwork = models.OneToOneField(
        Artwork, on_delete=models.CASCADE, related_name="auction"
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="selling_auctions",
        blank=True,
        null=True,
    )
    auction_title = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=280, unique=True, blank=True)

    # Timing
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()
    auto_extend_time = models.PositiveIntegerField(
        default=0,
        help_text="Minutes to auto-extend when a bid is placed near the end (0 = disabled)",
    )

    # Pricing
    starting_bid = models.DecimalField(max_digits=14, decimal_places=2)
    current_bid = models.DecimalField(
        max_digits=14, decimal_places=2, blank=True, null=True
    )
    reserve_price = models.DecimalField(
        max_digits=14, decimal_places=2, blank=True, null=True
    )
    bid_increment = models.DecimalField(
        max_digits=10, decimal_places=2, default=100.00
    )

    # Status & state
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.UPCOMING
    )
    is_featured = models.BooleanField(default=False)

    # Denormalised counters
    total_bids = models.PositiveIntegerField(default=0)
    total_watchers = models.PositiveIntegerField(default=0)

    # Winner
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_auctions",
    )
    winning_bid = models.DecimalField(
        max_digits=14, decimal_places=2, blank=True, null=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-start_time",)
        verbose_name = "Auction"
        verbose_name_plural = "Auctions"

    # ------------------------------------------------------------------ #
    #  Slug generation
    # ------------------------------------------------------------------ #
    def save(self, *args, **kwargs):
        if not self.auction_title:
            self.auction_title = self.artwork.title
        if not self.slug:
            base = slugify(self.auction_title)
            slug = base
            counter = 1
            while Auction.objects.filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------ #
    #  URL
    # ------------------------------------------------------------------ #
    def get_absolute_url(self):
        return reverse("auctions:auction_detail", kwargs={"slug": self.slug})

    # ------------------------------------------------------------------ #
    #  State helpers
    # ------------------------------------------------------------------ #
    @property
    def is_live(self):
        return self.status == self.Status.LIVE

    @property
    def is_upcoming(self):
        return self.status == self.Status.UPCOMING

    @property
    def has_ended(self):
        return self.status in (self.Status.ENDED, self.Status.SOLD)

    @property
    def time_remaining(self):
        if self.has_ended:
            return None
        now = timezone.now()
        if self.start_time > now:
            return self.start_time - now
        if self.end_time > now:
            return self.end_time - now
        return None

    @property
    def bid_count(self):
        """Alias for template compatibility."""
        return self.total_bids

    # ------------------------------------------------------------------ #
    #  Bid validation helpers
    # ------------------------------------------------------------------ #
    def minimum_next_bid(self):
        """Return the minimum amount the next bid must be."""
        current = self.current_bid or self.starting_bid
        return current + self.bid_increment

    def can_bid(self, user=None):
        """Check whether bidding is currently allowed."""
        if self.status != self.Status.LIVE:
            return False
        if self.end_time < timezone.now():
            return False
        if user and self.seller and user == self.seller:
            return False
        return True

    # ------------------------------------------------------------------ #
    #  str
    # ------------------------------------------------------------------ #
    def __str__(self):
        return f"{self.auction_title} – {self.get_status_display()}"


# =========================================================================
# BID  —  Individual bid placed on an auction
# =========================================================================
class Bid(models.Model):
    """A single bid placed by a user on an auction."""

    auction = models.ForeignKey(
        Auction, on_delete=models.CASCADE, related_name="bids"
    )
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bids",
    )
    bid_amount = models.DecimalField(max_digits=14, decimal_places=2)
    bid_time = models.DateTimeField(default=timezone.now)
    is_winning_bid = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        ordering = ("-bid_amount", "-bid_time")
        verbose_name = "Bid"
        verbose_name_plural = "Bids"

    def __str__(self):
        return f"{self.bidder.username} → ${self.bid_amount} on {self.auction.auction_title}"


# =========================================================================
# BID HISTORY  —  Audit log for all auction events
# =========================================================================
class BidHistory(models.Model):
    """Immutable audit trail of every action on an auction."""

    class Action(models.TextChoices):
        AUCTION_CREATED = "created", "Auction Created"
        BID_PLACED = "bid_placed", "Bid Placed"
        BID_CANCELLED = "bid_cancelled", "Bid Cancelled"
        AUCTION_STARTED = "started", "Auction Started"
        AUCTION_ENDED = "ended", "Auction Ended"
        AUCTION_SOLD = "sold", "Auction Sold"
        RESERVE_MET = "reserve_met", "Reserve Met"
        AUCTION_EXTENDED = "extended", "Auction Extended"
        WINNER_DETERMINED = "winner", "Winner Determined"

    auction = models.ForeignKey(
        Auction, on_delete=models.CASCADE, related_name="history"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("-timestamp",)
        verbose_name_plural = "Bid Histories"

    def __str__(self):
        return f"{self.get_action_display()} — {self.auction.auction_title}"


# =========================================================================
# AUCTION WATCHLIST
# =========================================================================
class AuctionWatchlist(models.Model):
    """User follow/watching an auction (for notifications)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auction_watchlist",
    )
    auction = models.ForeignKey(
        Auction, on_delete=models.CASCADE, related_name="watchers"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-added_at",)
        verbose_name = "Auction Watchlist"
        verbose_name_plural = "Auction Watchlists"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "auction"],
                name="unique_user_auction_watch",
            )
        ]

    def __str__(self):
        return f"{self.user.username} watching {self.auction.auction_title}"


# =========================================================================
# AUCTION RESULT
# =========================================================================
class AuctionResult(models.Model):
    """Finalized result for a completed auction (payment tracking)."""

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    auction = models.OneToOneField(
        Auction, on_delete=models.CASCADE, related_name="result"
    )
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="auction_results",
    )
    final_price = models.DecimalField(max_digits=14, decimal_places=2)
    total_bids = models.PositiveIntegerField(default=0)
    sold_at = models.DateTimeField(default=timezone.now)
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    payment_date = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-sold_at",)
        verbose_name = "Auction Result"
        verbose_name_plural = "Auction Results"

    def __str__(self):
        return f"Result: {self.auction.auction_title} — ${self.final_price}"
