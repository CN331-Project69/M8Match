import mimetypes

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.db.models import F, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from PIL import Image, UnidentifiedImageError
    
from .models import Conversation, Message


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def build_sidebar(user, active_id=None):
    """
    รายการห้องแชทของ user เรียงตามข้อความล่าสุด (ใหม่สุดอยู่บน) เหมือน Instagram
    ห้องที่ยังไม่มีข้อความจะเรียงตามเวลาที่สร้างห้อง
    """
    last_msg = Message.objects.filter(conversation=OuterRef("pk")).order_by(
        "-created_at", "-id"
    )

    conversations = (
        Conversation.objects.filter(participants=user)
        .annotate(
            last_activity=Coalesce(
                Subquery(last_msg.values("created_at")[:1]), F("created_at")
            ),
            last_content=Subquery(last_msg.values("content")[:1]),
            last_image=Subquery(last_msg.values("image")[:1]),
        )
        .order_by("-last_activity", "-id")
        .prefetch_related("participants")
    )

    items = []
    for conv in conversations:
        others = [p for p in conv.participants.all() if p.id != user.id]
        other = others[0] if others else None
        name = other.get_username() if other else "Unknown"

        if conv.last_content:
            preview = conv.last_content
        elif conv.last_image:
            preview = "📷 รูปภาพ"
        else:
            preview = "ยังไม่มีข้อความ..."

        items.append(
            {
                "id": conv.id,
                "other_user": name,
                "initial": name[:1],
                "last_message": preview,
                "is_active": active_id is not None and conv.id == active_id,
            }
        )
    return items


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
@login_required
def inbox_view(request):
    """/chat/room/  ->  มีแต่รายการแชททางซ้าย ฝั่งขวาว่าง"""
    context = {
        "room_id": None,
        "messages": [],
        "sidebar_conversations": build_sidebar(request.user),
    }
    return render(request, "chat/room.html", context)


@login_required
def room_view(request, room_id):
    """/chat/room/<id>/  ->  รายการแชททางซ้าย + ประวัติแชทห้องนั้น"""
    # เข้าได้เฉพาะห้องที่ตัวเองเป็นสมาชิก (ไม่ใช่ห้องของคนอื่น)
    conversation = get_object_or_404(
        Conversation, id=room_id, participants=request.user
    )
    messages = conversation.messages.select_related("sender")

    context = {
        "room_id": conversation.id,
        "messages": messages,
        "sidebar_conversations": build_sidebar(request.user, active_id=conversation.id),
    }
    return render(request, "chat/room.html", context)


# --------------------------------------------------------------------------
# Images (ของเดิม ไม่ได้แก้)
# --------------------------------------------------------------------------
@login_required
@require_POST
def upload_image(request, conversation_id):
    conversation = get_object_or_404(
        Conversation, id=conversation_id, participants=request.user
    )

    image = request.FILES.get("image")

    if not image:
        return JsonResponse({"error": "Please select an image"}, status=400)

    if image.size > 5 * 1024 * 1024:
        return JsonResponse({"error": "Image must be 5 MB or smaller"}, status=400)

    try:
        with Image.open(image) as img:
            img.verify()
        image.seek(0)
    except (UnidentifiedImageError, OSError):
        return JsonResponse({"error": "Invalid image file"}, status=400)

    message = Message.objects.create(
        conversation=conversation, sender=request.user, image=image
    )

    image_url = reverse("chat:message_image", args=[message.id])

    payload = {
        "id": message.id,
        "sender_id": request.user.id,
        "sender": request.user.get_username(),
        "content": "",
        "image_url": image_url,
        "created_at": message.created_at.isoformat(),
    }

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"chat_{conversation.id}", {"type": "chat.message", "message": payload}
    )

    return JsonResponse({"success": True})


@login_required
def message_image(request, message_id):
    message = get_object_or_404(
        Message.objects.select_related("conversation"), id=message_id
    )

    if not message.conversation.participants.filter(id=request.user.id).exists():
        raise Http404

    if not message.image:
        raise Http404

    content_type = (
        mimetypes.guess_type(message.image.name)[0] or "application/octet-stream"
    )

    return FileResponse(message.image.open("rb"), content_type=content_type)

@login_required
@require_POST
def start_chat(request, user_id):
    User = get_user_model()
    if user_id == request.user.id:
        return redirect("chat:inbox")
    target = get_object_or_404(User, id=user_id, is_active=True)

    # หาห้องที่มีเราและเขาอยู่แล้ว ถ้าไม่มีค่อยสร้างใหม่
    conv = (Conversation.objects.filter(participants=request.user)
            .filter(participants=target).first())
    if conv is None:
        conv = Conversation.objects.create()
        conv.participants.add(request.user, target)
    return redirect("chat:room", room_id=conv.id)