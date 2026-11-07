from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.shortcuts import redirect

from .models import Project
from accounts.models import Profile

from django.contrib import messages
from django.core.exceptions import ValidationError

from .models import Project, Swipe
from .services import find_matching_projects, swipe_user


class CreateProjectView(LoginRequiredMixin, TemplateView):
    template_name = "matching/create_project.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        project = (
            Project.objects.filter(
                user=self.request.user,
                is_active=True,
            )
            .order_by("-id")
            .first()
        )

        context["project"] = project

        profile = Profile.objects.filter(user=self.request.user).first()

        context["profile"] = profile

        return context

    def post(self, request, *args, **kwargs):
        team_details = request.POST.get("team_details", "")
        requirements_details = request.POST.get("requirements_details", "")

        project = (
            Project.objects.filter(
                user=request.user,
                is_active=True,
            )
            .order_by("-id")
            .first()
        )

        if project:
            project.team_details = team_details
            project.requirements_details = requirements_details
            project.save()
        else:
            Project.objects.create(
                user=request.user,
                team_details=team_details,
                requirements_details=requirements_details,
            )

        return redirect("find_match")


class FindMatchView(LoginRequiredMixin, TemplateView):
    template_name = "matching/find_match.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Find matching projects
        matches = find_matching_projects(self.request.user)

        # Get users who have already been swiped
        swiped_user_ids = Swipe.objects.filter(swiper=self.request.user).values_list(
            "swiped_user_id", flat=True
        )

        # Exclude already-swiped users
        matches = [
            item for item in matches if item["project"].user_id not in swiped_user_ids
        ]

        context["matches"] = matches
        context["has_matches"] = bool(matches)

        return context

    def post(self, request, *args, **kwargs):

        target_user_id = request.POST.get("target_user_id")
        direction = request.POST.get("direction")

        try:
            result = swipe_user(
                user=request.user,
                target_user_id=target_user_id,
                direction=direction,
            )

            if result["matched"]:
                messages.success(request, "It's a Match! You both like each other!")

            elif direction == Swipe.LEFT:
                messages.info(request, "You passed this user.")

            else:
                messages.success(request, "Like sent! Waiting for their response.")

        except (ValidationError, ValueError) as error:
            messages.error(request, str(error))

        return redirect("find_match")
