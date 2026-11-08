from django.urls import path
from .views import (
    RegisterView,
    CustomLoginView,
    CustomLogoutView,
    HomeView,
    ProfileUpdateView,
)
from . import views
from django.contrib.auth import views as auth_views

app_name = "accounts"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    path("match/", views.MatchView.as_view(), name="match"),
    path("profile/", views.ProfileDetailView.as_view(), name="profile_detail"),
    path("profile/edit/", views.ProfileUpdateView.as_view(), name="edit_profile"),
]
