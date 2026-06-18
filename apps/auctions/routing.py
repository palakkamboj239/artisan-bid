"""
WebSocket URL routing for the auctions app.
Maps WebSocket connections to the AuctionConsumer.
"""

from django.urls import re_path

from apps.auctions.consumers import AuctionConsumer

websocket_urlpatterns = [
    re_path(r"ws/auctions/(?P<slug>[\w-]+)/$", AuctionConsumer.as_asgi()),
]
