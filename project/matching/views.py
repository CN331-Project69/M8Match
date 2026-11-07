from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import ValidationError

from accounts.models import Profile
from categories.models import Category

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

        profile = Profile.objects.filter(user=self.request.user).first()

        context["project"] = project
        context["profile"] = profile
        context["categories"] = Category.objects.filter(is_active=True)

        if project:
            context["selected_team_categories"] = project.team_categories.values_list(
                "id", flat=True
            )

            context["selected_required_categories"] = (
                project.required_categories.values_list("id", flat=True)
            )
        else:
            context["selected_team_categories"] = []
            context["selected_required_categories"] = []

        return context

    def post(self, request, *args, **kwargs):
        team_details = request.POST.get("team_details", "")
        requirements_details = request.POST.get("requirements_details", "")

        team_category_ids = request.POST.getlist("team_categories")
        required_category_ids = request.POST.getlist("required_categories")

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
            project = Project.objects.create(
                user=request.user,
                team_details=team_details,
                requirements_details=requirements_details,
            )

        active_categories = Category.objects.filter(is_active=True)

        project.team_categories.set(active_categories.filter(id__in=team_category_ids))

        project.required_categories.set(
            active_categories.filter(id__in=required_category_ids)
        )

        return redirect("find_match")


class FindMatchView(LoginRequiredMixin, TemplateView):
    template_name = "matching/find_match.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        matches = find_matching_projects(self.request.user)

        swiped_user_ids = Swipe.objects.filter(swiper=self.request.user).values_list(
            "swiped_user_id", flat=True
        )

        matches = [
            item for item in matches if item["project"].user_id not in swiped_user_ids
        ]

        context["matches"] = matches
        context["has_matches"] = bool(matches)

        # แสดง Popup เพียงครั้งเดียวหลังจากเกิด Match
        context["new_match"] = self.request.session.pop("new_match", None)

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
                match = result["match"]

                other_user = (
                    match.user2 if match.user1_id == request.user.id else match.user1
                )

                profile = getattr(other_user, "profile", None)

                request.session["new_match"] = {
                    "match_id": match.id,
                    "display_name": (
                        profile.display_name
                        if profile and profile.display_name
                        else other_user.username
                    ),
                    "profile_picture": (
                        profile.profile_picture.url
                        if profile and profile.profile_picture
                        else ""
                    ),
                }

            else:
                messages.info(request, "Your swipe has been saved.")

        except ValidationError as error:
            messages.error(request, error.message)

        return redirect("find_match")
