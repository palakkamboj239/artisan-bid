from django.contrib import admin
from django.utils.html import format_html

from apps.artworks.models import (
    Artist,
    Artwork,
    ArtworkImage,
    ArtworkTag,
    ArtworkView,
    Category,
    FavoriteArtwork,
)


# =========================================================================
# INLINES
# =========================================================================
class ArtworkImageInline(admin.TabularInline):
    """Inline gallery images for the Artwork admin."""

    model = ArtworkImage
    extra = 2
    fields = ("image", "caption", "is_primary", "order")
    ordering = ("order",)


class ArtworkInline(admin.TabularInline):
    """Inline artworks for Artist admin."""

    model = Artwork
    extra = 1
    fields = ("title", "status", "is_featured", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    show_change_link = True


# =========================================================================
# ARTIST ADMIN
# =========================================================================
@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("artist_name",)}
    list_display = (
        "artist_name",
        "country",
        "verified_artist",
        "birth_year",
        "artwork_count",
        "created_at",
    )
    list_filter = ("verified_artist", "country")
    search_fields = ("artist_name", "biography")
    inlines = [ArtworkInline]
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Profile", {"fields": ("artist_name", "slug", "user", "biography")}),
        ("Media", {"fields": ("profile_image",)}),
        ("Details", {"fields": ("country", "birth_year", "website", "instagram", "verified_artist")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def artwork_count(self, obj):
        return obj.artworks.count()
    artwork_count.short_description = "Artworks"


# =========================================================================
# CATEGORY ADMIN
# =========================================================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "artwork_count", "created_at")
    search_fields = ("name",)

    def artwork_count(self, obj):
        return obj.artworks.count()
    artwork_count.short_description = "Artworks"


# =========================================================================
# ARTWORK TAG ADMIN
# =========================================================================
@admin.register(ArtworkTag)
class ArtworkTagAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "artwork_count")
    search_fields = ("name",)

    def artwork_count(self, obj):
        return obj.artworks.count()
    artwork_count.short_description = "Artworks"


# =========================================================================
# ARTWORK ADMIN  —  Main admin configuration
# =========================================================================
@admin.register(Artwork)
class ArtworkAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ArtworkImageInline]

    list_display = (
        "thumbnail_preview",
        "title",
        "artist_name",
        "status",
        "category",
        "current_price",
        "is_featured",
        "views_count",
        "likes_count",
        "created_at",
    )
    list_display_links = ("thumbnail_preview", "title")
    list_filter = (
        "status",
        "is_featured",
        "is_active",
        "category",
        "created_at",
    )
    search_fields = ("title", "short_description", "full_description")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    readonly_fields = ("views_count", "likes_count", "created_at", "updated_at", "slug")

    fieldsets = (
        ("Identity", {"fields": ("title", "slug", "artist", "category", "tags")}),
        ("Description", {"fields": ("short_description", "full_description")}),
        ("Provenance", {"fields": ("creation_year", "medium", "dimensions")}),
        ("Pricing", {"fields": ("starting_price", "estimated_price", "reserve_price", "current_price")}),
        ("Status", {"fields": ("status", "is_featured", "is_active")}),
        ("Media", {"fields": ("primary_image",)}),
        ("Analytics", {"fields": ("views_count", "likes_count"), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def thumbnail_preview(self, obj):
        if obj.primary_image:
            return format_html(
                '<img src="{}" style="width:48px;height:48px;object-fit:cover;" />',
                obj.primary_image.url,
            )
        return "—"
    thumbnail_preview.short_description = "Image"

    def artist_name(self, obj):
        return obj.artist_name
    artist_name.short_description = "Artist"


# =========================================================================
# ARTWORK VIEW ADMIN (read-only analytics)
# =========================================================================
@admin.register(ArtworkView)
class ArtworkViewAdmin(admin.ModelAdmin):
    list_display = ("artwork", "user", "ip_address", "viewed_at")
    list_filter = ("viewed_at",)
    search_fields = ("artwork__title", "ip_address")
    readonly_fields = ("artwork", "user", "ip_address", "viewed_at")
    date_hierarchy = "viewed_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# =========================================================================
# FAVORITE ARTWORK ADMIN
# =========================================================================
@admin.register(FavoriteArtwork)
class FavoriteArtworkAdmin(admin.ModelAdmin):
    list_display = ("user", "artwork", "added_at")
    list_filter = ("added_at",)
    search_fields = ("user__username", "artwork__title")
    date_hierarchy = "added_at"
