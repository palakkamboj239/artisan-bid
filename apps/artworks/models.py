from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


# =========================================================================
# ARTIST
# =========================================================================
class Artist(models.Model):
    """Professional artist profile linked to a User account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="artist_profile",
        blank=True,
        null=True,
    )
    artist_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    biography = models.TextField(blank=True)
    profile_image = models.ImageField(
        upload_to="artists/",
        blank=True,
        default="artists/default.svg",
    )
    country = models.CharField(max_length=100, blank=True)
    birth_year = models.PositiveIntegerField(blank=True, null=True)
    website = models.URLField(max_length=500, blank=True)
    instagram = models.CharField(max_length=100, blank=True)
    verified_artist = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("artist_name",)
        verbose_name = "Artist"
        verbose_name_plural = "Artists"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.artist_name)
            slug = base
            counter = 1
            while Artist.objects.filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("artworks:artist_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.artist_name


# =========================================================================
# CATEGORY
# =========================================================================
class Category(models.Model):
    """Artistic category / medium (e.g. Painting, Sculpture, Photography)."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    featured_image = models.ImageField(upload_to="categories/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ("name",)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =========================================================================
# ARTWORK TAG
# =========================================================================
class ArtworkTag(models.Model):
    """Tag for categorizing artworks (e.g. Luxury, Rare, Contemporary)."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =========================================================================
# ARTWORK  —  Main model
# =========================================================================
class Artwork(models.Model):
    """A piece of art consigned for auction or display."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        LIVE_AUCTION = "live_auction", "Live Auction"
        SOLD = "sold", "Sold"
        ARCHIVED = "archived", "Archived"

    artist = models.ForeignKey(
        Artist,
        on_delete=models.SET_NULL,
        null=True,
        related_name="artworks",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="artworks",
    )
    tags = models.ManyToManyField(
        ArtworkTag,
        blank=True,
        related_name="artworks",
    )

    # Core
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    short_description = models.CharField(max_length=300, blank=True)
    full_description = models.TextField(blank=True)

    # Provenance
    creation_year = models.PositiveIntegerField(blank=True, null=True)
    medium = models.CharField(max_length=200, blank=True)
    dimensions = models.CharField(max_length=200, blank=True)

    # Pricing
    starting_price = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    estimated_price = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    reserve_price = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    current_price = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)

    # Status & flags
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Analytics counters (denormalized for performance)
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)

    # Primary image thumbnail
    primary_image = models.ImageField(upload_to="artworks/", blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Artwork"
        verbose_name_plural = "Artworks"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            counter = 1
            while Artwork.objects.filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("artworks:artwork_detail", kwargs={"slug": self.slug})

    @property
    def artist_name(self):
        """Return the artist display name (compatible with templates expecting a string)."""
        return self.artist.artist_name if self.artist else "Unknown Artist"

    def __str__(self):
        return f"{self.title} — {self.artist_name}"


# =========================================================================
# ARTWORK IMAGE GALLERY
# =========================================================================
class ArtworkImage(models.Model):
    """Multiple images for a single artwork (gallery support)."""

    artwork = models.ForeignKey(
        Artwork,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="artworks/gallery/")
    caption = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "uploaded_at")
        verbose_name = "Artwork Image"
        verbose_name_plural = "Artwork Images"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per artwork
        if self.is_primary:
            ArtworkImage.objects.filter(artwork=self.artwork, is_primary=True).exclude(
                pk=self.pk
            ).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.artwork.title}"


# =========================================================================
# ARTWORK VIEW  (analytics)
# =========================================================================
class ArtworkView(models.Model):
    """Tracks each view of an artwork for analytics / recommendations."""

    artwork = models.ForeignKey(
        Artwork,
        on_delete=models.CASCADE,
        related_name="views",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="artwork_views",
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-viewed_at",)
        verbose_name = "Artwork View"
        verbose_name_plural = "Artwork Views"

    def __str__(self):
        return f"{self.artwork.title} viewed at {self.viewed_at}"


# =========================================================================
# FAVORITE / WATCHLIST
# =========================================================================
class FavoriteArtwork(models.Model):
    """User's saved / favourite artworks (watchlist entries)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_artworks",
    )
    artwork = models.ForeignKey(
        Artwork,
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-added_at",)
        verbose_name = "Favorite Artwork"
        verbose_name_plural = "Favorite Artworks"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "artwork"],
                name="unique_user_artwork_favorite",
            )
        ]

    def __str__(self):
        return f"{self.user.username} ♥ {self.artwork.title}"
