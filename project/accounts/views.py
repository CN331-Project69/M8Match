from django.views.generic import CreateView, TemplateView, UpdateView, DetailView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import login
from django.urls import reverse_lazy
from .forms import RegisterForm
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Profile
from django.shortcuts import redirect
from django.contrib import messages
from .forms import ProfileForm


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    next_page = reverse_lazy("home")


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("home")


class HomeView(TemplateView):
    template_name = "accounts/home.html"


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("profile_detail")

    def get_object(self, queryset=None):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, "Your profile has been updated.")
        return super().form_valid(form)


class ProfileDetailView(LoginRequiredMixin, DetailView):
    model = Profile
    template_name = "accounts/profile_detail.html"
    context_object_name = "profile"

    def get_object(self, queryset=None):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile
