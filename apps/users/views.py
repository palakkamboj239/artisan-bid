from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q, Sum, Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import CreateView, TemplateView, UpdateView, ListView

from apps.users.forms import ProfileForm, UserRegistrationForm
from apps.users.models import Profile, User
from apps.auctions.models import Auction, Bid, AuctionWatchlist, BidHistory
from apps.artworks.models import FavoriteArtwork, ArtworkView


# =========================================================================
# REGISTER
# =========================================================================
class RegisterView(SuccessMessageMixin, CreateView):
    form_class = UserRegistrationForm
    template_name = "users/register.html"
    success_url = reverse_lazy("users:dashboard")
    success_message = "Welcome to ArtisanBid — your account has been created."

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("users:dashboard")
        return super().get(request, *args, **kwargs)


# =========================================================================
# LOGIN
# =========================================================================
@method_decorator(never_cache, name="dispatch")
class CustomLoginView(SuccessMessageMixin, LoginView):
    template_name = "users/login.html"
    next_page = reverse_lazy("users:dashboard")
    success_message = "Welcome back to ArtisanBid."

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("users:dashboard")
        return super().get(request, *args, **kwargs)


# =========================================================================
# LOGOUT
# =========================================================================
class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("core:home")


# =========================================================================
# PROFILE
# =========================================================================
class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile_user"] = self.request.user
        return context


class EditProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = "users/edit_profile.html"
    success_message = "Your profile has been updated."

    def get_object(self, queryset=None):
        return get_object_or_404(Profile, user=self.request.user)

    def get_success_url(self):
        return reverse_lazy("users:profile")


# =========================================================================
# DASHBOARD — shared context
# =========================================================================
class DashboardMixin(LoginRequiredMixin):
    """Mixin providing dashboard-wide context data."""

    def get_dashboard_context(self):
        user = self.request.user
        now = timezone.now()

        total_bids = Bid.objects.filter(bidder=user).count()
        active_auctions = Bid.objects.filter(
            bidder=user, auction__status="live", auction__end_time__gt=now
        ).values("auction").distinct().count()
        won_auctions = Auction.objects.filter(winner=user, status__in=("sold", "ended")).count()
        watchlist_count = AuctionWatchlist.objects.filter(user=user).count()

        return {
            "total_bids": total_bids,
            "active_auctions": active_auctions,
            "won_auctions": won_auctions,
            "watchlist_count": watchlist_count,
            "unread_notifications": 0,
            "active_tab": "dashboard",
            "notifications": self._get_notifications(user),
        }

    def _get_notifications(self, user, limit=5):
        entries = BidHistory.objects.filter(
            Q(auction__seller=user) | Q(user=user)
        ).select_related("auction", "user").order_by("-timestamp")[:limit]

        notifs = []
        for e in entries:
            ntype = "bid" if e.action == "bid_placed" else "outbid" if e.action == "bid_cancelled" else "win" if e.action == "winner" else "ended" if e.action in ("ended",) else "info"
            notifs.append({
                "type": ntype,
                "message": e.description or f"{e.get_action_display()} on {e.auction.auction_title}",
                "time": e.timestamp,
                "read": False,
                "link": None,
            })
        return notifs


# =========================================================================
# DASHBOARD HOME
# =========================================================================
class DashboardHomeView(DashboardMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.now()
        context.update(self.get_dashboard_context())

        context["greeting"] = self._greeting()

        # Active bids
        context["active_bids"] = Bid.objects.filter(
            bidder=user, auction__status="live", auction__end_time__gt=now
        ).select_related("auction", "auction__artwork").order_by("-bid_time")[:8]

        # Watchlist items
        context["watchlist_items"] = AuctionWatchlist.objects.filter(
            user=user
        ).select_related("auction", "auction__artwork").order_by("-added_at")[:4]

        # Selling auctions
        context["selling_auctions"] = Auction.objects.filter(
            seller=user
        ).select_related("artwork").order_by("-start_time")[:4]

        # Recent activity
        context["recent_activity"] = self._recent_activity(user)

        return context

    def _greeting(self):
        h = timezone.now().hour
        if h < 12: return "Good morning. The art market awaits."
        if h < 17: return "Good afternoon. Discover exceptional pieces."
        return "Good evening. Explore tonight's auctions."

    def _recent_activity(self, user, limit=8):
        activity = []
        bids = Bid.objects.filter(bidder=user).select_related("auction").order_by("-bid_time")[:5]
        for b in bids:
            activity.append({
                "type": "bid",
                "message": f"You placed a bid of ${b.bid_amount:,.2f} on {b.auction.auction_title}",
                "time": b.bid_time,
            })
        watches = AuctionWatchlist.objects.filter(user=user).select_related("auction").order_by("-added_at")[:3]
        for w in watches:
            activity.append({
                "type": "watch",
                "message": f"You added {w.auction.auction_title} to your watchlist",
                "time": w.added_at,
            })
        activity.sort(key=lambda x: x["time"], reverse=True)
        return activity[:limit]


# =========================================================================
# DASHBOARD — MY BIDS
# =========================================================================
class DashboardBidsView(DashboardMixin, TemplateView):
    template_name = "dashboard/bids.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update(self.get_dashboard_context())
        context["active_tab"] = "bids"

        # Filter
        filter_type = self.request.GET.get("filter", "active")
        qs = Bid.objects.filter(bidder=user).select_related(
            "auction", "auction__artwork", "auction__artwork__artist"
        )

        if filter_type == "active":
            qs = qs.filter(auction__status="live")
        elif filter_type == "won":
            qs = qs.filter(is_winning_bid=True, auction__status__in=("sold", "ended"))
        elif filter_type == "lost":
            qs = qs.filter(
                Q(is_winning_bid=False) | Q(auction__status="ended"),
                auction__status__in=("ended", "sold"),
            )

        context["bids"] = qs.order_by("-bid_time")[:50]
        context["filter"] = filter_type
        return context


# =========================================================================
# DASHBOARD — WATCHLIST
# =========================================================================
class DashboardWatchlistView(DashboardMixin, TemplateView):
    template_name = "dashboard/watchlist.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_context())
        context["active_tab"] = "watchlist"
        context["watchlist_items"] = AuctionWatchlist.objects.filter(
            user=self.request.user
        ).select_related("auction", "auction__artwork").order_by("-added_at")
        return context


# =========================================================================
# DASHBOARD — SAVED ARTWORKS
# =========================================================================
class DashboardSavedView(DashboardMixin, TemplateView):
    template_name = "dashboard/saved.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_context())
        context["active_tab"] = "saved"
        context["saved_artworks"] = FavoriteArtwork.objects.filter(
            user=self.request.user
        ).select_related("artwork").order_by("-added_at")
        return context


# =========================================================================
# DASHBOARD — SELLER / MY SALES
# =========================================================================
class DashboardSellerView(DashboardMixin, TemplateView):
    template_name = "dashboard/seller.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update(self.get_dashboard_context())
        context["active_tab"] = "seller"

        auctions = Auction.objects.filter(seller=user)
        context["selling_auctions"] = auctions.select_related("artwork").order_by("-start_time")
        context["active_listings"] = auctions.filter(status__in=("live", "upcoming")).count()
        context["items_sold"] = auctions.filter(status="sold").count()

        revenue = auctions.filter(status="sold").aggregate(
            total=Sum("winning_bid")
        )["total"] or 0
        context["total_revenue"] = revenue

        views = ArtworkView.objects.filter(
            artwork__auction__seller=user
        ).count()
        context["total_views"] = views

        return context


# =========================================================================
# DASHBOARD — NOTIFICATIONS
# =========================================================================
class DashboardNotificationsView(DashboardMixin, TemplateView):
    template_name = "dashboard/notifications.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update(self.get_dashboard_context())
        context["active_tab"] = "notifications"
        context["notifications"] = self._get_notifications(user, limit=50)
        return context


# =========================================================================
# DASHBOARD — SETTINGS
# =========================================================================
class DashboardSettingsView(DashboardMixin, TemplateView):
    template_name = "dashboard/settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_context())
        context["active_tab"] = "settings"
        return context


# =========================================================================
# DASHBOARD — ANALYTICS
# =========================================================================
class DashboardAnalyticsView(DashboardMixin, TemplateView):
    template_name = "dashboard/analytics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update(self.get_dashboard_context())
        context["active_tab"] = "analytics"

        all_bids = Bid.objects.filter(bidder=user)
        total_bids = all_bids.count()
        won = Auction.objects.filter(winner=user, status__in=("sold", "ended")).count()
        lost = total_bids - won if total_bids > won else 0

        context["lost_auctions"] = max(0, lost)
        context["win_rate"] = round((won / total_bids * 100)) if total_bids > 0 else 0
        context["win_rate_offset"] = 283 - (283 * context["win_rate"] / 100)

        context["total_likes"] = sum(
            a.likes_count for a in user.won_auctions.all()
        ) if hasattr(user, "won_auctions") else 0

        context["total_favorites"] = FavoriteArtwork.objects.filter(
            artwork__auction__seller=user
        ).count() if hasattr(user, "artist_profile") else 0

        avg = all_bids.aggregate(v=Avg("bid_amount"))["v"]
        context["avg_bid"] = f"${avg:,.2f}" if avg else "$0"

        return context
