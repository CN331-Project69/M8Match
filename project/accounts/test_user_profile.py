from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from chat.models import Conversation
from chat.services import get_or_create_direct_conversation


class ChatPartnerProfileTests(TestCase):
    """กดดูโปรไฟล์ของคนที่แชทด้วยได้ (แบบ IG)"""

    def setUp(self):
        User = get_user_model()
        self.me = User.objects.create_user(username="me", email="me@example.com", password="x")
        self.mate = User.objects.create_user(username="mate", email="mate@example.com", password="x")
        Profile.objects.create(user=self.mate, display_name="Mate Jr.", about_me="Hello", skills="Go, Rust")
        self.room = get_or_create_direct_conversation(self.me, self.mate)
        self.client.force_login(self.me)

    def test_chat_header_links_to_partner_profile(self):
        response = self.client.get(reverse("chat:room", args=[self.room.id]))
        profile_url = reverse("user_profile", args=["mate"])
        self.assertContains(response, 'class="chat-header"')
        self.assertContains(response, f'href="{profile_url}"', count=2)  # รูป/ชื่อ + ปุ่ม info
        self.assertContains(response, "Mate Jr.")

    def test_sidebar_uses_display_name(self):
        response = self.client.get(reverse("chat:inbox"))
        self.assertContains(response, '<div class="name">Mate Jr.</div>', html=True)

    def test_partner_profile_is_read_only_with_message_button(self):
        response = self.client.get(reverse("user_profile", args=["mate"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mate Jr.")
        self.assertContains(response, '<li class="skill-tag">Rust</li>', html=True)
        self.assertContains(response, f'action="{reverse("chat:start", args=[self.mate.id])}"')
        self.assertNotContains(response, "Edit Profile")
        self.assertNotContains(response, reverse("edit_profile"))
        self.assertNotContains(response, "mate@example.com")  # อีเมลไม่แสดงให้คนอื่นเห็น

    def test_message_button_returns_to_same_room(self):
        response = self.client.post(reverse("chat:start", args=[self.mate.id]))
        self.assertRedirects(response, reverse("chat:room", args=[self.room.id]))
        self.assertEqual(Conversation.objects.count(), 1)

    def test_own_username_redirects_to_editable_profile(self):
        response = self.client.get(reverse("user_profile", args=["me"]))
        self.assertRedirects(response, reverse("profile_detail"))

    def test_unknown_user_is_404_and_login_required(self):
        self.assertEqual(self.client.get(reverse("user_profile", args=["nobody"])).status_code, 404)
        self.client.logout()
        response = self.client.get(reverse("user_profile", args=["mate"]))
        self.assertEqual(response.status_code, 302)

    def test_user_named_edit_is_reachable(self):
        get_user_model().objects.create_user(username="edit", password="x")
        response = self.client.get(reverse("user_profile", args=["edit"]))
        self.assertContains(response, "@edit")
