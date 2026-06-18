from django.db import models
from django.urls import path

from apps.auctions import views

app_name = "auctions"

urlpatterns = [
    # List / Browse
    path("", views.AuctionListView.as_view(), name="auction_list"),
    # User's auctions dashboard
    path("my-auctions/", views.MyAuctionsView.as_view(), name="my_auctions"),
    # Watchlist toggle
    path("<slug:slug>/watch/", views.ToggleWatchlistView.as_view(), name="toggle_watch"),
    # Bid submission
    path("<slug:slug>/bid/", views.PlaceBidView.as_view(), name="place_bid"),
    # Live auction room (WebSocket real-time bidding)
    path("<slug:slug>/live/", views.AuctionRoomView.as_view(), name="auction_room"),
    # Detail
    path("<slug:slug>/", views.AuctionDetailView.as_view(), name="auction_detail"),
]
