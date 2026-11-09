from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from chat.models import Conversation

from .models import Swipe


class MatchPopupChatTests(TestCase):
    """เมื่อ Match กันแล้ว popup ต้องให้เลือกแชทหรือปัดต่อ และปุ่มแชทพาไปหน้าแชท"""

    def setUp(self):
        User = get_user_model()
        self.me = User.objects.create_user(username="me", password="pass12345")
        self.mate = User.objects.create_user(username="mate", password="pass12345")
        # อีกฝ่ายปัดขวาเรามาก่อนแล้ว
        Swipe.objects.create(swiper=self.mate, swiped_user=self.me, direction=Swipe.RIGHT)
        self.client.force_login(self.me)

    def swipe_right_on_mate(self):
        return self.client.post(
            reverse("find_match"),
            {"target_user_id": self.mate.id, "direction": "right"},
            follow=True,
        )

    def test_popup_offers_chat_and_continue(self):
        response = self.swipe_right_on_mate()

        self.assertContains(response, "IT'S A MATCH!")
        self.assertContains(response, "Continue Swiping")
        self.assertContains(response, f'action="{reverse("chat:start", args=[self.mate.id])}"')
        self.assertNotContains(response, "Chat Coming Soon")

    def test_popup_only_shows_once(self):
        self.swipe_right_on_mate()
        response = self.client.get(reverse("find_match"))
        self.assertNotContains(response, "IT'S A MATCH!")

    def test_chat_button_opens_chat_room_with_match(self):
        self.swipe_right_on_mate()

        response = self.client.post(reverse("chat:start", args=[self.mate.id]))

        conversation = Conversation.objects.get(participants=self.me)
        self.assertRedirects(response, reverse("chat:room", args=[conversation.id]))
        self.assertEqual(
            set(conversation.participants.values_list("username", flat=True)),
            {"me", "mate"},
        )

    def test_chat_button_reuses_existing_room(self):
        self.swipe_right_on_mate()
        url = reverse("chat:start", args=[self.mate.id])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(Conversation.objects.filter(participants=self.me).count(), 1)


class MatchCreatesConversationTests(TestCase):
    """Match สำเร็จแล้วต้องมีห้องแชททันที ไม่ต้องรอกดปุ่ม Chat"""

    def setUp(self):
        User = get_user_model()
        self.me = User.objects.create_user(username="me", password="pass12345")
        self.mate = User.objects.create_user(username="mate", password="pass12345")

    def conversations_between(self, a, b):
        return Conversation.objects.filter(participants=a).filter(participants=b)

    def test_mutual_like_creates_conversation_for_both(self):
        from .services import swipe_user

        swipe_user(self.mate, self.me.id, Swipe.RIGHT)
        result = swipe_user(self.me, self.mate.id, Swipe.RIGHT)

        self.assertTrue(result["matched"])
        self.assertEqual(self.conversations_between(self.me, self.mate).count(), 1)

        # อีกฝ่ายเห็นห้องในหน้าแชทของตัวเองด้วย
        self.client.force_login(self.mate)
        response = self.client.get(reverse("chat:inbox"))
        self.assertContains(response, "me")
        conversation = self.conversations_between(self.me, self.mate).get()
        self.assertContains(response, reverse("chat:room", args=[conversation.id]))

    def test_one_sided_like_or_pass_creates_no_conversation(self):
        from .services import swipe_user

        swipe_user(self.me, self.mate.id, Swipe.RIGHT)
        swipe_user(self.mate, self.me.id, Swipe.LEFT)
        self.assertFalse(self.conversations_between(self.me, self.mate).exists())

    def test_match_reuses_existing_conversation(self):
        from chat.services import get_or_create_direct_conversation

        from .services import swipe_user

        existing = get_or_create_direct_conversation(self.me, self.mate)
        swipe_user(self.mate, self.me.id, Swipe.RIGHT)
        swipe_user(self.me, self.mate.id, Swipe.RIGHT)
        self.assertEqual(list(self.conversations_between(self.me, self.mate)), [existing])

    def test_backfill_migration_adds_rooms_for_old_matches(self):
        import importlib

        from django.apps import apps

        from .models import Match

        backfill = importlib.import_module(
            "matching.migrations.0004_backfill_match_conversations"
        ).backfill_match_conversations

        # Match เก่าที่เกิดก่อนมีระบบสร้างห้องอัตโนมัติ
        Match.objects.create(user1=self.me, user2=self.mate)
        self.assertFalse(self.conversations_between(self.me, self.mate).exists())

        backfill(apps, None)
        backfill(apps, None)  # รันซ้ำต้องไม่สร้างห้องซ้ำ

        self.assertEqual(self.conversations_between(self.me, self.mate).count(), 1)
