from django.urls import path

from .views import CreateProjectView, FindMatchView


urlpatterns = [
    path("", CreateProjectView.as_view(), name="create_project"),
    path("find-match/", FindMatchView.as_view(), name="find_match"),
]
