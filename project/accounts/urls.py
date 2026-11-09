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
from django.views.generic import RedirectView

app_name = "accounts"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    # ลิงก์เก่า /match/ -> ไปหน้า Find Match ของแอป matching
    path("match/", RedirectView.as_view(pattern_name="find_match"), name="match"),
    path("profile/", views.ProfileDetailView.as_view(), name="profile_detail"),
    path("profile/edit/", views.ProfileUpdateView.as_view(), name="edit_profile"),
    # โปรไฟล์ของคนอื่น (เช่น กดจากหน้าแชท) แยก prefix ไม่ให้ชนกับ profile/edit/
    path("users/<str:username>/", views.UserProfileView.as_view(), name="user_profile"),
]
