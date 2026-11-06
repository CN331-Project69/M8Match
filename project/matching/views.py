from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .models import Project


class CreateProjectView(LoginRequiredMixin, TemplateView):
    template_name = "matching/create_project.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        project = Project.objects.filter(
            user=self.request.user,
            is_active=True,
        ).order_by("-id").first()

        context["project"] = project

        return context

    def post(self, request, *args, **kwargs):
        team_details = request.POST.get("team_details", "")
        requirements_details = request.POST.get("requirements_details", "")

        project = Project.objects.filter(
            user=request.user,
            is_active=True,
        ).order_by("-id").first()

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

        return self.render_to_response(
            self.get_context_data()
        )