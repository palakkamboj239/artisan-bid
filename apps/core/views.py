from django.shortcuts import render

from apps.artworks.models import Artwork, Artist
from apps.auctions.models import Auction


def home(request):
    """Landing page with full luxury sections."""
    featured_artworks = Artwork.objects.filter(
        is_featured=True, status__in=("published", "live_auction")
    ).select_related("artist", "category")[:6]

    live_auctions = Auction.objects.filter(status="active").select_related(
        "artwork", "artwork__artist"
    )[:6]

    top_artists = Artist.objects.filter(verified_artist=True)[:8]

    context = {
        "featured_artworks": featured_artworks,
        "live_auctions": live_auctions,
        "top_artists": top_artists,
    }
    return render(request, "core/index.html", context)
