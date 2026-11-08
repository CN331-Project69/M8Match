from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "chat"

urlpatterns = [
    # /chat/  ->  /chat/room/
    path("", RedirectView.as_view(pattern_name="chat:inbox", permanent=False), name="index"),

    # /chat/room/      : หน้าแชทแบบ Instagram (มีแต่รายการแชททางซ้าย ฝั่งขวาว่าง)
    path("room/", views.inbox_view, name="inbox"),

    # /chat/room/<id>/ : รายการแชททางซ้าย + ประวัติแชทของห้องนั้นทางขวา
    path("room/<int:room_id>/", views.room_view, name="room"),

    path("upload/<int:conversation_id>/", views.upload_image, name="upload_image"),
    path("message/<int:message_id>/image/", views.message_image, name="message_image"),
    path("start/<int:user_id>/", views.start_chat, name="start"),
]