"""
URL configuration for project project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, include, re_path
from django.views.static import serve

# กำหนด URL หลักของแต่ละแอปในโปรเจกต์
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("board/", include("board.urls")),
    path("categories/", include("categories.urls")),
    path("create-project/", include("matching.urls")),
    path("chat/", include("chat.urls")),
]

urlpatterns += staticfiles_urlpatterns()

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif not settings.USE_CLOUDINARY:
    # production ที่ยังไม่ได้ต่อ Cloudinary: ให้ Django เสิร์ฟรูปที่อัปโหลดเอง
    # (ใช้ได้กับโปรเจกต์ขนาดเล็ก; รูปจะหายเมื่อ deploy ใหม่บน Render แบบฟรี)
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
