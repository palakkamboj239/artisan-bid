"""
WebSocket consumer for live auction room.
Handles real-time bidding, countdown sync, user presence, and bid feed.
"""

import json
from decimal import Decimal
from collections import defaultdict

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db import transaction
from django.utils import timezone

from apps.auctions.models import Auction, Bid, BidHistory


class AuctionConsumer(AsyncWebsocketConsumer):
    """
    Consumer that manages a single auction room.

    - On connect: joins the auction group, sends current state.
    - On disconnect: leaves group.
    - On bid message: validates, persists, and broadcasts to all room members.
    """

    # Class-level viewer/bidder tracking per auction slug
    _viewers = defaultdict(int)
    _bidders = defaultdict(int)

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------
    def _get_auction_data(self, auction):
        return {
            "type": "auction_state",
            "auction_id": auction.id,
            "status": auction.status,
            "current_bid": str(auction.current_bid or auction.starting_bid),
            "total_bids": auction.total_bids,
            "total_watchers": auction.total_watchers,
            "winner": auction.winner.username if auction.winner else None,
            "winning_bid": str(auction.winning_bid) if auction.winning_bid else None,
            "start_time": auction.start_time.isoformat(),
            "end_time": auction.end_time.isoformat(),
            "auto_extend_minutes": auction.auto_extend_time,
            "bid_increment": str(auction.bid_increment),
            "reserve_price": str(auction.reserve_price) if auction.reserve_price else None,
            "minimum_next_bid": str(auction.minimum_next_bid()),
        }

    def _get_bid_data(self, bid):
        return {
            "type": "new_bid",
            "bid_id": bid.id,
            "bidder": bid.bidder.username,
            "amount": str(bid.bid_amount),
            "time": bid.bid_time.isoformat(),
            "is_winning": bid.is_winning_bid,
        }

    # ------------------------------------------------------------------
    #  Database helpers (sync → async wrappers)
    # ------------------------------------------------------------------
    @database_sync_to_async
    def _get_auction(self, slug):
        try:
            return Auction.objects.select_related("winner").get(slug=slug)
        except Auction.DoesNotExist:
            return None

    @database_sync_to_async
    def _get_recent_bids(self, auction, limit=15):
        return list(
            auction.bids.select_related("bidder").order_by("-bid_amount")[:limit]
        )

    @database_sync_to_async
    def _get_recent_history(self, auction, limit=10):
        return list(
            auction.history.select_related("user").order_by("-timestamp")[:limit]
        )

    @database_sync_to_async
    def _place_bid(self, auction, user, amount, ip_address):
        from apps.auctions.forms import BidForm

        form = BidForm({"bid_amount": amount}, auction=auction, user=user)
        if not form.is_valid():
            return False, "; ".join(
                err for errors in form.errors.values() for err in errors
            )

        try:
            with transaction.atomic():
                bid = Bid.objects.create(
                    auction=auction,
                    bidder=user,
                    bid_amount=form.cleaned_data["bid_amount"],
                    ip_address=ip_address,
                )
            auction.refresh_from_db()
            return True, bid
        except Exception as e:
            return False, str(e)

    @database_sync_to_async
    def _get_user(self):
        return self.scope.get("user")

    # ------------------------------------------------------------------
    #  Connection lifecycle
    # ------------------------------------------------------------------
    async def connect(self):
        self.slug = self.scope["url_route"]["kwargs"]["slug"]
        self.room_group_name = f"auction_{self.slug}"

        self.auction = await self._get_auction(self.slug)
        if self.auction is None:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        AuctionConsumer._viewers[self.slug] += 1

        # Send initial auction state
        await self.send(text_data=json.dumps(self._get_auction_data(self.auction)))

        # Send recent bids
        recent_bids = await self._get_recent_bids(self.auction)
        for bid in recent_bids:
            await self.send(text_data=json.dumps(self._get_bid_data(bid)))

        # Send recent history entries
        recent_history = await self._get_recent_history(self.auction)
        for h in recent_history:
            await self.send(
                text_data=json.dumps({
                    "type": "history_entry",
                    "action": h.action,
                    "user": h.user.username if h.user else None,
                    "amount": str(h.amount) if h.amount else None,
                    "time": h.timestamp.isoformat(),
                    "description": h.description,
                })
            )

        # Broadcast viewer counts to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "viewer_update",
                "viewers": AuctionConsumer._viewers.get(self.slug, 0),
                "online_bidders": AuctionConsumer._bidders.get(self.slug, 0),
            },
        )

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            AuctionConsumer._viewers[self.slug] = max(
                0, AuctionConsumer._viewers.get(self.slug, 0) - 1
            )
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "viewer_update",
                    "viewers": AuctionConsumer._viewers.get(self.slug, 0),
                    "online_bidders": AuctionConsumer._bidders.get(self.slug, 0),
                },
            )

    # ------------------------------------------------------------------
    #  Message handling
    # ------------------------------------------------------------------
    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")

        if msg_type == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))

        elif msg_type == "place_bid":
            await self.handle_place_bid(data)

        elif msg_type == "request_state":
            auction = await self._get_auction(self.slug)
            if auction:
                await self.send(text_data=json.dumps(self._get_auction_data(auction)))

    async def handle_place_bid(self, data):
        user = await self._get_user()
        if not user or not user.is_authenticated:
            await self.send(
                text_data=json.dumps({
                    "type": "bid_error",
                    "message": "You must be logged in to place a bid.",
                })
            )
            return

        try:
            amount = Decimal(str(data.get("amount", "0")))
        except Exception:
            await self.send(
                text_data=json.dumps({
                    "type": "bid_error",
                    "message": "Invalid bid amount.",
                })
            )
            return

        auction = await self._get_auction(self.slug)
        if auction is None:
            await self.send(
                text_data=json.dumps({
                    "type": "bid_error",
                    "message": "Auction not found.",
                })
            )
            return

        ip_address = self.scope.get("client", [None])[0]
        success, result = await self._place_bid(auction, user, amount, ip_address)

        if not success:
            await self.send(
                text_data=json.dumps({
                    "type": "bid_error",
                    "message": result,
                })
            )
            return

        bid = result
        auction = await self._get_auction(self.slug)

        AuctionConsumer._bidders[self.slug] += 1

        # Broadcast bid + updated auction state to ALL room members
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "broadcast_bid",
                "bid": self._get_bid_data(bid),
                "auction": self._get_auction_data(auction),
            },
        )

        # Handle auto-extend (anti-sniping)
        if (
            auction.auto_extend_time > 0
            and auction.status == Auction.Status.LIVE
        ):
            time_left = (auction.end_time - timezone.now()).total_seconds() / 60
            if 0 < time_left <= auction.auto_extend_time:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "auction_extended",
                        "new_end_time": auction.end_time.isoformat(),
                        "extended_by": auction.auto_extend_time,
                    },
                )

    # ------------------------------------------------------------------
    #  Broadcast handlers (called by channel_layer.group_send)
    # ------------------------------------------------------------------
    async def broadcast_bid(self, event):
        await self.send(text_data=json.dumps(event["bid"]))
        await self.send(text_data=json.dumps(event["auction"]))

    async def viewer_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "viewer_update",
            "viewers": event["viewers"],
            "online_bidders": event["online_bidders"],
        }))

    async def auction_extended(self, event):
        await self.send(text_data=json.dumps({
            "type": "auction_extended",
            "new_end_time": event["new_end_time"],
            "extended_by": event["extended_by"],
        }))

    async def auction_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    async def bid_error(self, event):
        await self.send(text_data=json.dumps(event))
