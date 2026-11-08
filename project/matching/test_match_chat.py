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
