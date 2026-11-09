import io
import json
import shutil
import tempfile

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from PIL import Image

from .consumers import ChatConsumer
from .models import Message
from .services import get_or_create_direct_conversation

TEMP_MEDIA = tempfile.mkdtemp()
IN_MEMORY_LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


def png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), "pink").save(buffer, format="PNG")
    return buffer.getvalue()


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class ChatConsumerTests(TransactionTestCase):
    """แชท real-time ผ่าน WebSocket"""

    def setUp(self):
        User = get_user_model()
        self.me = User.objects.create_user(username="me", password="x")
        self.mate = User.objects.create_user(username="mate", password="x")
        self.stranger = User.objects.create_user(username="stranger", password="x")
        self.room = get_or_create_direct_conversation(self.me, self.mate)

    def communicator(self, user):
        comm = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.room.id}/")
        comm.scope["user"] = user
        comm.scope["url_route"] = {"kwargs": {"room_id": self.room.id}}
        return comm

    def test_participant_sends_and_receives_message(self):
        async def scenario():
            comm = self.communicator(self.me)
            connected, _ = await comm.connect()
            self.assertTrue(connected)
            await comm.send_to(text_data=json.dumps({"message": "  Hello team  "}))
            reply = json.loads(await comm.receive_from())
            await comm.disconnect()
            return reply

        reply = async_to_sync(scenario)()
        self.assertEqual(reply, {"sender": "me", "sender_id": self.me.id, "message": "Hello team"})
        self.assertTrue(Message.objects.filter(conversation=self.room, content="Hello team").exists())

    def test_help_command_gets_bot_reply(self):
        async def scenario():
            comm = self.communicator(self.me)
            await comm.connect()
            await comm.send_to(text_data=json.dumps({"message": "!help"}))
            first = json.loads(await comm.receive_from())
            bot = json.loads(await comm.receive_from())
            await comm.disconnect()
            return first, bot

        first, bot = async_to_sync(scenario)()
        self.assertEqual(first["message"], "!help")
        self.assertEqual(bot["sender"], "Bot")
        self.assertEqual(Message.objects.filter(conversation=self.room, sender__username="Bot").count(), 1)

    def test_invalid_or_empty_messages_are_ignored(self):
        async def scenario():
            comm = self.communicator(self.me)
            await comm.connect()
            await comm.send_to(text_data="not json")
            await comm.send_to(text_data=json.dumps({"message": "   "}))
            nothing = await comm.receive_nothing(timeout=0.2)
            await comm.disconnect()
            return nothing

        self.assertTrue(async_to_sync(scenario)())
        self.assertFalse(Message.objects.exists())

    def test_image_event_is_forwarded(self):
        async def scenario():
            comm = self.communicator(self.mate)
            await comm.connect()
            await get_channel_layer().group_send(
                f"chat_{self.room.id}",
                {"type": "chat.message", "message": {
                    "content": "", "image_url": "/img/1", "sender": "me", "sender_id": self.me.id,
                }},
            )
            payload = json.loads(await comm.receive_from())
            await comm.disconnect()
            return payload

        payload = async_to_sync(scenario)()
        self.assertEqual(payload["image_url"], "/img/1")
        self.assertEqual(payload["sender"], "me")

    def test_non_participant_and_guest_are_rejected(self):
        async def connect(user):
            comm = self.communicator(user)
            connected, _ = await comm.connect()
            await comm.disconnect()
            return connected

        self.assertFalse(async_to_sync(connect)(self.stranger))
        self.assertFalse(async_to_sync(connect)(AnonymousUser()))


@override_settings(MEDIA_ROOT=TEMP_MEDIA, CHANNEL_LAYERS=IN_MEMORY_LAYER)
class ChatImageTests(TestCase):
    """ส่งรูปในแชท และเปิดดูรูปได้เฉพาะคนในห้อง"""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        User = get_user_model()
        self.me = User.objects.create_user(username="me", password="x")
        self.mate = User.objects.create_user(username="mate", password="x")
        self.stranger = User.objects.create_user(username="stranger", password="x")
        self.room = get_or_create_direct_conversation(self.me, self.mate)
        self.url = reverse("chat:upload_image", args=[self.room.id])
        self.client.force_login(self.me)

    def test_upload_and_view_image(self):
        image = SimpleUploadedFile("a.png", png_bytes(), content_type="image/png")
        response = self.client.post(self.url, {"image": image})
        self.assertEqual(response.json(), {"success": True})

        message = Message.objects.get(conversation=self.room)
        image_url = reverse("chat:message_image", args=[message.id])
        self.assertEqual(self.client.get(image_url).status_code, 200)

        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(image_url).status_code, 404)

    def test_upload_rejects_missing_or_invalid_file(self):
        self.assertEqual(self.client.post(self.url).status_code, 400)
        fake = SimpleUploadedFile("a.png", b"not an image", content_type="image/png")
        self.assertEqual(self.client.post(self.url, {"image": fake}).status_code, 400)

    def test_upload_rejects_too_large_file(self):
        big = SimpleUploadedFile("big.png", b"0" * (5 * 1024 * 1024 + 1), content_type="image/png")
        self.assertEqual(self.client.post(self.url, {"image": big}).status_code, 400)

    def test_text_message_has_no_image(self):
        message = Message.objects.create(conversation=self.room, sender=self.me, content="hi")
        self.assertEqual(self.client.get(reverse("chat:message_image", args=[message.id])).status_code, 404)

    def test_cannot_start_chat_with_yourself(self):
        response = self.client.post(reverse("chat:start", args=[self.me.id]))
        self.assertRedirects(response, reverse("chat:inbox"))
