import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .models import Conversation, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"

        user = self.scope["user"]

        # ต้อง login และเป็นสมาชิกของห้องนี้เท่านั้น
        if not user.is_authenticated or not await self.is_participant(
            user.id, self.room_id
        ):
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        message = (data.get("message") or "").strip()
        if not message:
            return

        user = self.scope["user"]
        sender_id, sender_name = await self.save_message(self.room_id, user, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "sender": sender_name,
                "sender_id": sender_id,
            },
        )

        # บอท
        if message == "!help":
            bot_reply = "สวัสดี มีอะไรให้บอทช่วยไหม?"
            await self.save_bot_message(self.room_id, bot_reply)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": bot_reply,
                    "sender": "Bot",
                    "sender_id": 0,
                },
            )

    async def chat_message(self, event):
        message = event["message"]
        payload = {
            "sender": event.get("sender", "Unknown"),
            "sender_id": event.get("sender_id", 0),
        }

        if isinstance(message, dict):
            # มาจาก upload_image (ส่งรูป)
            payload.update(
                {
                    "message": message.get("content", ""),
                    "image_url": message.get("image_url"),
                    "sender": message.get("sender", payload["sender"]),
                    "sender_id": message.get("sender_id", payload["sender_id"]),
                }
            )
        else:
            payload["message"] = message

        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def is_participant(self, user_id, room_id):
        return Conversation.objects.filter(
            id=room_id, participants__id=user_id
        ).exists()

    @database_sync_to_async
    def save_message(self, room_id, user, content):
        conversation = Conversation.objects.get(id=room_id)
        Message.objects.create(conversation=conversation, sender=user, content=content)
        return user.id, user.username

    @database_sync_to_async
    def save_bot_message(self, room_id, content):
        User = get_user_model()
        conversation = Conversation.objects.get(id=room_id)
        bot_user, _ = User.objects.get_or_create(username="Bot")
        Message.objects.create(conversation=conversation, sender=bot_user, content=content)