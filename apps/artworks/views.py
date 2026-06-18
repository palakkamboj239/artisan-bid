from django.db import models
from django.views.generic import DetailView, ListView

from apps.artworks.models import Artwork, Artist


class ArtistDetailView(DetailView):
    """Public profile page for an artist."""

    model = Artist
    template_name = "artworks/artist_detail.html"
    context_object_name = "artist"
    slug_field = "slug"


class ArtworkListView(ListView):
    """Browse all published artworks."""

    model = Artwork
    template_name = "artworks/artwork_list.html"
    context_object_name = "artworks"
    paginate_by = 12

    def get_queryset(self):
        return Artwork.objects.filter(status__in=("published", "live_auction")).select_related(
            "artist", "category"
        )


class ArtworkDetailView(DetailView):
    """Full detail view for a single artwork."""

    model = Artwork
    template_name = "artworks/artwork_detail.html"
    context_object_name = "artwork"

    def get_queryset(self):
        return Artwork.objects.select_related("artist", "category").prefetch_related(
            "images", "tags"
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment view counter
        Artwork.objects.filter(pk=obj.pk).update(views_count=models.F("views_count") + 1)
        return obj
