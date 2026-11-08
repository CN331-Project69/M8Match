
"""
URL configuration for project project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# กำหนด URL หลักของแต่ละแอปในโปรเจกต์
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("board/", include("board.urls")),
    path("categories/", include("categories.urls")),
]

# เปิดให้ Django จัดการไฟล์รูปภาพและ Media ในโหมด Development
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
