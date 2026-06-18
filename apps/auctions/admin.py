from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from apps.auctions.models import Auction, Bid, BidHistory, AuctionWatchlist, AuctionResult


# =========================================================================
# BID INLINE
# =========================================================================
class BidInline(admin.TabularInline):
    model = Bid
    extra = 0
    fields = ("bidder", "bid_amount", "bid_time", "is_winning_bid", "ip_address")
    readonly_fields = ("bidder", "bid_amount", "bid_time", "is_winning_bid", "ip_address")
    ordering = ("-bid_amount",)
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


# =========================================================================
# AUCTION ADMIN
# =========================================================================
@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    inlines = [BidInline]
    prepopulated_fields = {"slug": ("auction_title",)}

    list_display = (
        "status_indicator",
        "auction_title",
        "status",
        "current_bid_display",
        "total_bids",
        "total_watchers",
        "start_time",
        "end_time",
        "is_featured",
    )
    list_display_links = ("status_indicator", "auction_title")
    list_filter = ("status", "is_featured", "start_time")
    search_fields = ("auction_title", "artwork__title", "seller__username")
    date_hierarchy = "start_time"
    ordering = ("-start_time",)

    readonly_fields = (
        "slug",
        "total_bids",
        "total_watchers",
        "current_bid",
        "winning_bid",
        "winner",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Artwork & Seller", {"fields": ("artwork", "seller", "auction_title", "slug")}),
        ("Timing", {"fields": ("start_time", "end_time", "auto_extend_time")}),
        ("Pricing", {"fields": ("starting_bid", "current_bid", "reserve_price", "bid_increment")}),
        ("Status", {"fields": ("status", "is_featured")}),
        ("Results", {"fields": ("winner", "winning_bid", "total_bids", "total_watchers"), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def status_indicator(self, obj):
        colors = {
            "upcoming": "#c9a84c",
            "live": "#28a745",
            "ended": "#6c757d",
            "sold": "#0d6efd",
            "cancelled": "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        label = obj.get_status_display()
        if obj.status == "live" and obj.end_time < timezone.now():
            color = "#dc3545"
            label = "Overdue"
        return format_html(
            '<span style="display:inline-block;width:10px;height:10px;'
            'border-radius:50%;background:{};margin-right:6px;"></span>{}',
            color,
            label,
        )
    status_indicator.short_description = "Status"

    def current_bid_display(self, obj):
        if obj.current_bid:
            return f"${obj.current_bid:,.2f}"
        return f"${obj.starting_bid:,.2f}"
    current_bid_display.short_description = "Current Bid"

    actions = ["mark_as_live", "mark_as_ended", "finalize_results"]

    def mark_as_live(self, request, queryset):
        updated = queryset.update(status="live")
        self.message_user(request, f"{updated} auction(s) marked as Live.")
    mark_as_live.short_description = "Mark selected auctions as Live"

    def mark_as_ended(self, request, queryset):
        updated = queryset.update(status="ended")
        self.message_user(request, f"{updated} auction(s) marked as Ended.")
    mark_as_ended.short_description = "Mark selected auctions as Ended"

    def finalize_results(self, request, queryset):
        from apps.auctions.signals import finalize_auction
        count = 0
        for auction in queryset:
            if auction.status in ("live", "ended"):
                finalize_auction(auction)
                count += 1
        self.message_user(request, f"Results finalized for {count} auction(s).")
    finalize_results.short_description = "Finalize results for selected auctions"


# =========================================================================
# BID ADMIN
# =========================================================================
@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("bidder", "auction", "bid_amount", "bid_time", "is_winning_bid")
    list_filter = ("is_winning_bid", "bid_time")
    search_fields = ("bidder__username", "auction__auction_title")
    date_hierarchy = "bid_time"
    readonly_fields = ("bidder", "auction", "bid_amount", "bid_time", "ip_address")

    def has_add_permission(self, request):
        return False


# =========================================================================
# BID HISTORY ADMIN
# =========================================================================
@admin.register(BidHistory)
class BidHistoryAdmin(admin.ModelAdmin):
    list_display = ("auction", "action", "user", "amount", "timestamp")
    list_filter = ("action", "timestamp")
    search_fields = ("auction__auction_title", "user__username", "description")
    date_hierarchy = "timestamp"
    readonly_fields = ("auction", "user", "action", "amount", "timestamp", "description")

    def has_add_permission(self, request):
        return False


# =========================================================================
# WATCHLIST ADMIN
# =========================================================================
@admin.register(AuctionWatchlist)
class AuctionWatchlistAdmin(admin.ModelAdmin):
    list_display = ("user", "auction", "added_at")
    search_fields = ("user__username", "auction__auction_title")


# =========================================================================
# AUCTION RESULT ADMIN
# =========================================================================
@admin.register(AuctionResult)
class AuctionResultAdmin(admin.ModelAdmin):
    list_display = ("auction", "winner", "final_price", "payment_status", "sold_at")
    list_filter = ("payment_status", "sold_at")
    search_fields = ("auction__auction_title", "winner__username")
    date_hierarchy = "sold_at"
