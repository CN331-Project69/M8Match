from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from chat.models import Conversation, Message


class Command(BaseCommand):
    help = "สร้างห้องแชททดสอบ: ให้ user คุยกับ Bot และ/หรือเพิ่ม user เข้าห้องที่มีอยู่แล้ว"

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="username ที่ใช้ล็อกอินอยู่")
        parser.add_argument(
            "--rooms",
            nargs="*",
            type=int,
            default=[],
            help="id ของห้องที่มีอยู่แล้ว (เช่น 1 2) ที่ต้องการเพิ่ม user เข้าไปเป็นสมาชิก",
        )
        parser.add_argument(
            "--demo-friend",
            action="store_true",
            help="สร้าง user 'friend' (รหัสผ่าน friend1234) + ห้องคุยกับ user นี้ ไว้ทดสอบ 2 เบราว์เซอร์",
        )

    def handle(self, *args, **opts):
        User = get_user_model()

        try:
            me = User.objects.get(username=opts["user"])
        except User.DoesNotExist:
            raise CommandError(f"ไม่พบ user '{opts['user']}'")

        # 1) เพิ่ม user เข้าห้องที่มีอยู่แล้ว (เช่นห้อง 1, 2 ที่สร้างไว้ใน admin)
        for room_id in opts["rooms"]:
            try:
                conv = Conversation.objects.get(id=room_id)
            except Conversation.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"ไม่มีห้อง {room_id}"))
                continue
            conv.participants.add(me)
            self.stdout.write(self.style.SUCCESS(f"เพิ่ม {me.username} เข้าห้อง {room_id} แล้ว"))

        # 2) ห้องคุยกับ Bot
        bot, created = User.objects.get_or_create(username="Bot")
        if created:
            bot.set_unusable_password()   # Bot ล็อกอินไม่ได้ ใช้เป็นคู่สนทนาอย่างเดียว
            bot.save()
        conv = self._get_or_create_room(me, bot)
        if not conv.messages.exists():
            Message.objects.create(
                conversation=conv,
                sender=bot,
                content="สวัสดี! พิมพ์ !help เพื่อลองคุยกับบอทได้เลย",
            )
        self.stdout.write(self.style.SUCCESS(f"ห้องคุยกับ Bot: /chat/room/{conv.id}/"))

        # 3) (เลือก) เพื่อนทดสอบ
        if opts["demo_friend"]:
            friend, created = User.objects.get_or_create(username="friend")
            if created:
                friend.set_password("friend1234")
                friend.save()
            conv = self._get_or_create_room(me, friend)
            self.stdout.write(
                self.style.SUCCESS(
                    f"ห้องคุยกับ friend: /chat/room/{conv.id}/  (login: friend / friend1234)"
                )
            )

    @staticmethod
    def _get_or_create_room(a, b):
        conv = (
            Conversation.objects.filter(participants=a)
            .filter(participants=b)
            .first()
        )
        if conv is None:
            conv = Conversation.objects.create()
            conv.participants.add(a, b)
        return conv