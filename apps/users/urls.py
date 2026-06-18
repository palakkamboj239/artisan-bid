from django.urls import path

from apps.users import views

app_name = "users"

urlpatterns = [
    # Authentication
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    # Profile
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/edit/", views.EditProfileView.as_view(), name="edit_profile"),
    # Dashboard (old path — redirect to new)
    path("dashboard/", views.DashboardHomeView.as_view(), name="dashboard"),
    # Dashboard pages
    path("dashboard/bids/", views.DashboardBidsView.as_view(), name="dashboard_bids"),
    path("dashboard/watchlist/", views.DashboardWatchlistView.as_view(), name="dashboard_watchlist"),
    path("dashboard/saved/", views.DashboardSavedView.as_view(), name="dashboard_saved"),
    path("dashboard/seller/", views.DashboardSellerView.as_view(), name="dashboard_seller"),
    path("dashboard/notifications/", views.DashboardNotificationsView.as_view(), name="dashboard_notifications"),
    path("dashboard/settings/", views.DashboardSettingsView.as_view(), name="dashboard_settings"),
    path("dashboard/analytics/", views.DashboardAnalyticsView.as_view(), name="dashboard_analytics"),
]
