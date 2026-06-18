import json
import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

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

logger = logging.getLogger(__name__)


def portrait_home(request):
    categories = PortraitCategory.objects.filter(is_active=True)
    featured_products = PortraitProduct.objects.filter(is_active=True, is_featured=True)
    sizes = PortraitSize.objects.filter(is_active=True)
    canvases = CanvasOption.objects.filter(is_active=True)
    frames = FrameOption.objects.filter(is_active=True)

    context = {
        "categories": categories,
        "featured_products": featured_products,
        "sizes": sizes,
        "canvases": canvases,
        "frames": frames,
    }
    return render(request, "portraits/portrait_home.html", context)


def category_detail(request, slug):
    category = get_object_or_404(PortraitCategory, slug=slug, is_active=True)
    products = category.products.filter(is_active=True)

    context = {
        "category": category,
        "products": products,
    }
    return render(request, "portraits/category_detail.html", context)


def product_detail(request, category_slug, product_slug):
    category = get_object_or_404(PortraitCategory, slug=category_slug, is_active=True)
    product = get_object_or_404(PortraitProduct, slug=product_slug, category=category, is_active=True)
    sizes = PortraitSize.objects.filter(is_active=True)
    canvases = CanvasOption.objects.filter(is_active=True)
    frames = FrameOption.objects.filter(is_active=True)

    context = {
        "category": category,
        "product": product,
        "sizes": sizes,
        "canvases": canvases,
        "frames": frames,
    }
    return render(request, "portraits/product_detail.html", context)


def portrait_customize(request, product_slug):
    product = get_object_or_404(PortraitProduct, slug=product_slug, is_active=True)
    category = product.category
    sizes = PortraitSize.objects.filter(is_active=True)
    canvases = CanvasOption.objects.filter(is_active=True)
    frames = FrameOption.objects.filter(is_active=True)
    sketch_types = SketchType.objects.filter(is_active=True)

    # Ensure session exists for anonymous users (for upload tracking)
    if not request.user.is_authenticated and not request.session.session_key:
        request.session.create()

    session_key = request.session.session_key
    uploaded_images = UploadedReferenceImage.objects.filter(
        is_active=True,
    ).filter(
        user=request.user if request.user.is_authenticated else None,
    ).filter(
        session_key=session_key if not request.user.is_authenticated else None,
    )

    context = {
        "product": product,
        "category": category,
        "sizes": sizes,
        "canvases": canvases,
        "frames": frames,
        "sketch_types": sketch_types,
        "uploaded_images": uploaded_images,
        "max_uploads": UploadedReferenceImage.MAX_UPLOADS_PER_SESSION,
    }
    return render(request, "portraits/portrait_customize.html", context)


@login_required
@require_POST
def add_to_cart(request):
    try:
        data = json.loads(request.body)

        product = get_object_or_404(PortraitProduct, id=data.get("product_id"), is_active=True)
        size = get_object_or_404(PortraitSize, id=data.get("size_id"), is_active=True)
        canvas = None
        if data.get("canvas_id"):
            canvas = get_object_or_404(CanvasOption, id=data["canvas_id"], is_active=True)
        frame = None
        if data.get("frame_id"):
            frame = get_object_or_404(FrameOption, id=data["frame_id"], is_active=True)
        sketch_type = None
        if data.get("sketch_type_id"):
            sketch_type = get_object_or_404(SketchType, id=data["sketch_type_id"], is_active=True)

        quantity = max(1, int(data.get("quantity", 1)))

        reference_image_ids = data.get("reference_image_ids", [])

        size_applied = product.base_price * size.price_multiplier
        canvas_adjustment = canvas.price_adjustment if canvas else Decimal("0.00")
        frame_adjustment = frame.price_adjustment if frame else Decimal("0.00")
        sketch_adjustment = sketch_type.price_adjustment if sketch_type else Decimal("0.00")
        unit_price = size_applied + canvas_adjustment + frame_adjustment + sketch_adjustment
        total_price = unit_price * quantity

        cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)

        item = CartItem.objects.create(
            cart=cart,
            product=product,
            size=size,
            canvas=canvas,
            frame=frame,
            sketch_type=sketch_type,
            quantity=quantity,
            calculated_total_price=total_price,
        )

        if reference_image_ids:
            valid_images = UploadedReferenceImage.objects.filter(
                id__in=reference_image_ids,
                is_active=True,
                user=request.user,
            )
            item.reference_images.set(valid_images)

        return JsonResponse({
            "success": True,
            "cart_item_id": item.id,
            "calculated_price": str(total_price),
            "cart_count": cart.item_count,
            "message": "Added to cart.",
        })

    except Exception as e:
        logger.error(f"Add to cart error: {e}")
        return JsonResponse({"success": False, "error": "Failed to add to cart."}, status=400)


@login_required
def cart_detail(request):
    cart = Cart.objects.filter(user=request.user, is_active=True).first()
    context = {
        "cart": cart,
    }
    return render(request, "portraits/portrait_cart.html", context)


@login_required
@require_POST
def update_cart_item(request):
    try:
        data = json.loads(request.body)
        item = get_object_or_404(CartItem, id=data.get("item_id"), cart__user=request.user, cart__is_active=True)

        quantity = max(1, int(data.get("quantity", 1)))
        item.quantity = quantity

        size_applied = item.product.base_price * item.size.price_multiplier
        canvas_adjustment = item.canvas.price_adjustment if item.canvas else Decimal("0.00")
        frame_adjustment = item.frame.price_adjustment if item.frame else Decimal("0.00")
        sketch_adjustment = item.sketch_type.price_adjustment if item.sketch_type else Decimal("0.00")
        unit_price = size_applied + canvas_adjustment + frame_adjustment + sketch_adjustment
        item.calculated_total_price = unit_price * quantity
        item.save(update_fields=["quantity", "calculated_total_price"])

        cart = item.cart

        return JsonResponse({
            "success": True,
            "quantity": item.quantity,
            "item_total": str(item.calculated_total_price),
            "cart_subtotal": str(cart.subtotal),
            "cart_count": cart.item_count,
        })

    except Exception as e:
        logger.error(f"Update cart error: {e}")
        return JsonResponse({"success": False, "error": "Failed to update item."}, status=400)


@login_required
@require_POST
def remove_cart_item(request):
    try:
        data = json.loads(request.body)
        item = get_object_or_404(CartItem, id=data.get("item_id"), cart__user=request.user, cart__is_active=True)
        cart = item.cart
        item.delete()

        return JsonResponse({
            "success": True,
            "cart_subtotal": str(cart.subtotal),
            "cart_count": cart.item_count,
            "message": "Item removed.",
        })

    except Exception as e:
        logger.error(f"Remove cart error: {e}")
        return JsonResponse({"success": False, "error": "Failed to remove item."}, status=400)


@require_POST
def upload_reference_image(request):
    try:
        if request.FILES.get("image") is None:
            return JsonResponse({"success": False, "error": "No image provided."}, status=400)

        file = request.FILES["image"]

        if file.content_type not in UploadedReferenceImage.ALLOWED_TYPES:
            return JsonResponse(
                {"success": False, "error": "Only JPG, PNG, and WebP images are allowed."},
                status=400,
            )

        if file.size > UploadedReferenceImage.MAX_FILE_SIZE:
            return JsonResponse(
                {"success": False, "error": "Image must be under 5 MB."},
                status=400,
            )

        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        existing_count = UploadedReferenceImage.objects.filter(
            is_active=True,
        ).filter(
            user=request.user if request.user.is_authenticated else None
        ).filter(
            session_key=session_key if not request.user.is_authenticated else None
        ).count()

        if existing_count >= UploadedReferenceImage.MAX_UPLOADS_PER_SESSION:
            return JsonResponse(
                {"success": False, "error": f"Maximum {UploadedReferenceImage.MAX_UPLOADS_PER_SESSION} images allowed."},
                status=400,
            )

        ref = UploadedReferenceImage(
            image=file,
            user=request.user if request.user.is_authenticated else None,
            session_key=None if request.user.is_authenticated else session_key,
        )
        ref.save()

        return JsonResponse({
            "success": True,
            "id": ref.id,
            "url": ref.image.url,
            "message": "Image uploaded successfully.",
        })

    except Exception as e:
        logger.error(f"Upload error: {e}")
        return JsonResponse({"success": False, "error": "Upload failed. Please try again."}, status=500)


@require_POST
def delete_reference_image(request):
    try:
        data = json.loads(request.body)
        image_id = data.get("image_id")
        if not image_id:
            return JsonResponse({"success": False, "error": "No image ID provided."}, status=400)

        ref = get_object_or_404(UploadedReferenceImage, id=image_id)

        if ref.user and ref.user != request.user:
            return JsonResponse({"success": False, "error": "Unauthorized."}, status=403)
        if ref.session_key and ref.session_key != request.session.session_key:
            return JsonResponse({"success": False, "error": "Unauthorized."}, status=403)

        ref.is_active = False
        ref.save(update_fields=["is_active"])
        return JsonResponse({"success": True, "message": "Image removed."})

    except Exception as e:
        logger.error(f"Delete error: {e}")
        return JsonResponse({"success": False, "error": "Delete failed."}, status=500)
