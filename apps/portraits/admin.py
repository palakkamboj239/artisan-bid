from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CanvasOption,
    Cart,
    CartItem,
    FrameOption,
    PortraitCategory,
    PortraitProduct,
    PortraitSize,
    SketchType,
    UploadedReferenceImage,
)


@admin.register(PortraitCategory)
class PortraitCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active", "product_count", "created_at")
    list_editable = ("order", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    readonly_fields = ("created_at",)

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "Products"


@admin.register(PortraitSize)
class PortraitSizeAdmin(admin.ModelAdmin):
    list_display = ("name", "width_display", "height_display", "price_multiplier", "is_active", "order")
    list_editable = ("price_multiplier", "is_active", "order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

    def width_display(self, obj):
        return f"{obj.width_cm} cm" if obj.width_cm else "—"
    width_display.short_description = "Width"

    def height_display(self, obj):
        return f"{obj.height_cm} cm" if obj.height_cm else "—"
    height_display.short_description = "Height"


@admin.register(CanvasOption)
class CanvasOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "price_adjustment", "is_active", "order")
    list_editable = ("price_adjustment", "is_active", "order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="200" />', obj.image.url)
        return "No image uploaded"
    image_preview.short_description = "Image Preview"


@admin.register(FrameOption)
class FrameOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "price_adjustment", "is_active", "order")
    list_editable = ("price_adjustment", "is_active", "order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="200" />', obj.image.url)
        return "No image uploaded"
    image_preview.short_description = "Image Preview"


@admin.register(PortraitProduct)
class PortraitProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "base_price", "is_featured", "is_active", "order")
    list_editable = ("base_price", "is_featured", "is_active", "order")
    list_filter = ("category", "is_active", "is_featured")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at", "sample_preview")

    def sample_preview(self, obj):
        if obj.sample_image:
            return format_html('<img src="{}" width="200" />', obj.sample_image.url)
        return "No sample image"
    sample_preview.short_description = "Sample Preview"

    fieldsets = (
        ("Details", {
            "fields": ("category", "name", "slug", "description", "base_price")
        }),
        ("Media", {
            "fields": ("sample_image", "sample_preview", "sample_gallery")
        }),
        ("Settings", {
            "fields": ("is_active", "is_featured", "order")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )


@admin.register(UploadedReferenceImage)
class UploadedReferenceImageAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "product", "image_thumbnail", "is_active", "uploaded_at")
    list_filter = ("is_active", "uploaded_at")
    search_fields = ("user__username", "session_key")
    readonly_fields = ("image_preview", "uploaded_at")
    list_editable = ("is_active",)

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:2px;" />',
                obj.image.url,
            )
        return "—"
    image_thumbnail.short_description = "Thumb"

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="300" style="border:1px solid rgba(255,255,255,0.1);" />',
                obj.image.url,
            )
        return "No image uploaded"
    image_preview.short_description = "Preview"


@admin.register(SketchType)
class SketchTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "price_adjustment", "is_active", "order")
    list_editable = ("price_adjustment", "is_active", "order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("calculated_total_price", "created_at")
    fields = ("product", "size", "canvas", "frame", "sketch_type", "quantity", "calculated_total_price")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "item_count", "subtotal_display", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at", "subtotal_display")
    inlines = [CartItemInline]

    def subtotal_display(self, obj):
        return f"₹{obj.subtotal}"
    subtotal_display.short_description = "Subtotal"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product", "quantity", "calculated_total_price", "created_at")
    list_filter = ("created_at",)
    search_fields = ("cart__user__username", "product__name")
    readonly_fields = ("created_at",)
