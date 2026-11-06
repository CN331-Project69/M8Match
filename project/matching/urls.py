from django.urls import path

from .views import CreateProjectView


urlpatterns = [
    path(
        "",
        CreateProjectView.as_view(),
        name="create_project",
    ),
]
