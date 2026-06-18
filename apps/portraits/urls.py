from django.urls import path

from . import views

app_name = "portraits"

urlpatterns = [
    path("", views.portrait_home, name="portrait_home"),
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    path(
        "category/<slug:category_slug>/<slug:product_slug>/",
        views.product_detail,
        name="product_detail",
    ),
    path(
        "customize/<slug:product_slug>/",
        views.portrait_customize,
        name="portrait_customize",
    ),
    path(
        "api/upload-reference/",
        views.upload_reference_image,
        name="upload_reference",
    ),
    path(
        "api/delete-reference/",
        views.delete_reference_image,
        name="delete_reference",
    ),
    path(
        "api/add-to-cart/",
        views.add_to_cart,
        name="add_to_cart",
    ),
    path(
        "api/update-cart-item/",
        views.update_cart_item,
        name="update_cart_item",
    ),
    path(
        "api/remove-cart-item/",
        views.remove_cart_item,
        name="remove_cart_item",
    ),
    path(
        "cart/",
        views.cart_detail,
        name="cart_detail",
    ),
]
