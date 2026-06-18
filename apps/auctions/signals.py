"""
Signals for auctions app — bid processing, winner selection, result creation.
"""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.auctions.models import Auction, Bid, BidHistory, AuctionResult


# =========================================================================
# BID PROCESSING SIGNAL
# =========================================================================
@receiver(post_save, sender=Bid)
def process_bid(sender, instance, created, **kwargs):
    """
    After a bid is placed:
    1. Update the auction's current_bid and total_bids
    2. Demote any previous winning bid
    3. Mark this bid as winning
    4. Record the event in BidHistory
    5. Check reserve price
    6. Handle auto-extension if enabled
    """
    if not created:
        return

    auction = instance.auction

    with transaction.atomic():
        # 1. Update auction counters
        auction.current_bid = instance.bid_amount
        auction.total_bids = auction.bids.count()
        auction.winning_bid = instance.bid_amount
        auction.winner = instance.bidder

        # 2. Demote any previous winning bid for this auction
        Bid.objects.filter(auction=auction, is_winning_bid=True).exclude(
            pk=instance.pk
        ).update(is_winning_bid=False)

        # 3. Mark current bid as winning
        Bid.objects.filter(pk=instance.pk).update(is_winning_bid=True)

        # 4. Auto-extend if a bid arrives within the extension window
        if auction.auto_extend_time > 0:
            time_left = (auction.end_time - timezone.now()).total_seconds() / 60
            if time_left <= auction.auto_extend_time:
                auction.end_time += timezone.timedelta(minutes=auction.auto_extend_time)
                BidHistory.objects.create(
                    auction=auction,
                    user=instance.bidder,
                    action=BidHistory.Action.AUCTION_EXTENDED,
                    amount=instance.bid_amount,
                    description=f"Auction extended by {auction.auto_extend_time} minutes",
                )

        # 5. Check if reserve met
        if (
            auction.reserve_price
            and instance.bid_amount >= auction.reserve_price
        ):
            BidHistory.objects.create(
                auction=auction,
                user=instance.bidder,
                action=BidHistory.Action.RESERVE_MET,
                amount=instance.bid_amount,
                description="Reserve price has been met",
            )

        auction.save()

    # 6. Record the bid event
    BidHistory.objects.create(
        auction=auction,
        user=instance.bidder,
        action=BidHistory.Action.BID_PLACED,
        amount=instance.bid_amount,
        description=f"Bid of ${instance.bid_amount} placed by {instance.bidder.username}",
    )


# =========================================================================
# AUCTION STATE TRANSITIONS
# =========================================================================
@receiver(post_save, sender=Auction)
def handle_auction_state(sender, instance, created, **kwargs):
    """Record history when an auction is created or status changes."""
    if created:
        BidHistory.objects.create(
            auction=instance,
            user=instance.seller,
            action=BidHistory.Action.AUCTION_CREATED,
            description=f"Auction created for {instance.auction_title}",
        )

        # Update the artwork status
        if instance.artwork.status not in ("live_auction", "sold"):
            instance.artwork.status = "published"
            instance.artwork.save(update_fields=["status"])


# =========================================================================
# AUCTION RESULT CREATION
# =========================================================================
def finalize_auction(auction):
    """
    Called when an auction ends (from management command or signal).
    Creates an AuctionResult and records the outcome.
    """
    if hasattr(auction, "result"):
        return auction.result  # already finalized

    winner = auction.winner
    final_price = auction.winning_bid or auction.current_bid or auction.starting_bid
    total_bids = auction.total_bids

    # If reserve not met and no winner, mark as ended (not sold)
    if (
        not winner
        or (
            auction.reserve_price
            and final_price < auction.reserve_price
        )
    ):
        auction.status = Auction.Status.ENDED
        auction.save(update_fields=["status"])

        BidHistory.objects.create(
            auction=auction,
            action=BidHistory.Action.AUCTION_ENDED,
            description="Auction ended — reserve price was not met",
        )
        return None

    # Reserve met — mark as sold
    auction.status = Auction.Status.SOLD
    auction.save(update_fields=["status"])

    result = AuctionResult.objects.create(
        auction=auction,
        winner=winner,
        final_price=final_price,
        total_bids=total_bids,
    )

    # Update artwork status
    artwork = auction.artwork
    artwork.status = "sold"
    artwork.current_price = final_price
    artwork.save(update_fields=["status", "current_price"])

    BidHistory.objects.create(
        auction=auction,
        user=winner,
        action=BidHistory.Action.AUCTION_SOLD,
        amount=final_price,
        description=f"Auction sold to {winner.username} for ${final_price}",
    )

    return result
