from django.urls import path
from .views import (
    RegisterView,
    CustomLoginView,
    CustomLogoutView,
    HomeView,
    ProfileUpdateView,
)
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    
    path('profile/', ProfileUpdateView.as_view(), name='profile_update'),
]
