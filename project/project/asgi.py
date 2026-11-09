"""
ASGI config: HTTP + WebSocket (แชท real-time)

ลำดับสำคัญ: ต้องตั้ง DJANGO_SETTINGS_MODULE และเรียก get_asgi_application()
ก่อน import โค้ดที่ใช้ model (เช่น chat.routing -> consumers)
ไม่งั้นรันด้วย daphne บน production จะ error "settings are not configured"
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

import chat.routing  # noqa: E402  ดึง routing ของแอป chat มาใช้งาน

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # รับ WebSocket เฉพาะจากหน้าเว็บของเราเอง (ตาม ALLOWED_HOSTS) กัน Cross-Site WebSocket Hijacking
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(chat.routing.websocket_urlpatterns))
        ),
    }
)
