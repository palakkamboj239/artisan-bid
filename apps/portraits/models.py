from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class PortraitCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    hero_image = models.ImageField(upload_to="portraits/categories/", blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Portrait Category"
        verbose_name_plural = "Portrait Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PortraitSize(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    width_cm = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    price_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.00"))
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Portrait Size"
        verbose_name_plural = "Portrait Sizes"

    def __str__(self):
        label = self.name
        if self.width_cm and self.height_cm:
            label += f" ({self.width_cm}×{self.height_cm} cm)"
        return label

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class CanvasOption(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="portraits/canvases/", blank=True)
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Canvas Option"
        verbose_name_plural = "Canvas Options"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class FrameOption(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="portraits/frames/", blank=True)
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Frame Option"
        verbose_name_plural = "Frame Options"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PortraitProduct(models.Model):
    category = models.ForeignKey(
        PortraitCategory,
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    sample_image = models.ImageField(upload_to="portraits/samples/", blank=True)
    sample_gallery = models.ImageField(upload_to="portraits/gallery/", blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Portrait Product"
        verbose_name_plural = "Portrait Products"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class UploadedReferenceImage(models.Model):
    ALLOWED_TYPES = ("image/jpeg", "image/png", "image/webp")
    MAX_FILE_SIZE = 5 * 1024 * 1024
    MAX_UPLOADS_PER_SESSION = 5

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="portrait_uploads",
    )
    session_key = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    product = models.ForeignKey(
        PortraitProduct,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reference_images",
    )
    image = models.ImageField(upload_to="portraits/references/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-uploaded_at",)
        verbose_name = "Uploaded Reference Image"
        verbose_name_plural = "Uploaded Reference Images"

    def __str__(self):
        owner = self.user.username if self.user else f"session:{self.session_key}"
        return f"Ref #{self.id} — {owner} — {self.uploaded_at.date()}"


class SketchType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(blank=True)
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Sketch Type"
        verbose_name_plural = "Sketch Types"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portrait_cart",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

    def __str__(self):
        return f"Cart [{self.user.username}] — {self.item_count} item(s)"

    @property
    def item_count(self):
        return self.items.count()

    @property
    def subtotal(self):
        return sum(item.calculated_total_price for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        PortraitProduct,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cart_items",
    )
    size = models.ForeignKey(
        PortraitSize,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cart_items",
    )
    canvas = models.ForeignKey(
        CanvasOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cart_items",
    )
    frame = models.ForeignKey(
        FrameOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cart_items",
    )
    sketch_type = models.ForeignKey(
        SketchType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cart_items",
    )
    reference_images = models.ManyToManyField(
        UploadedReferenceImage,
        blank=True,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    calculated_total_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"

    def __str__(self):
        product_name = self.product.name if self.product else "Deleted Product"
        return f"{product_name} × {self.quantity} — ₹{self.calculated_total_price}"
