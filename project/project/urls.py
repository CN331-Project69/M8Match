"""
URL configuration for project project.
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path(
        "create-project/",
        include("matching.urls"),
    ),
]


urlpatterns += staticfiles_urlpatterns()