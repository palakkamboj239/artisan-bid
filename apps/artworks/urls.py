from django.urls import path

from apps.artworks import views

app_name = "artworks"

urlpatterns = [
    # Artists
    path("artists/<slug:slug>/", views.ArtistDetailView.as_view(), name="artist_detail"),
    # Artworks
    path("", views.ArtworkListView.as_view(), name="artwork_list"),
    path("<slug:slug>/", views.ArtworkDetailView.as_view(), name="artwork_detail"),
]
