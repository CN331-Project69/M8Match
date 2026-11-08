from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from chat.models import Conversation


class SharedNavbarTests(TestCase):
    """ทุกหน้าต้องมี navbar กลาง และไฮไลต์เมนูของหน้าที่เปิดอยู่"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="mate", password="pass12345")
        other = get_user_model().objects.create_user(username="other", password="pass12345")
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user, other)

    def assert_navbar(self, url, active=None):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        self.assertContains(response, '<header class="m8-navbar', count=1, msg_prefix=url)
        if active:
            self.assertContains(response, f'aria-current="page">{active}<', count=1, msg_prefix=url)
        else:
            self.assertNotContains(response, 'aria-current="page"', msg_prefix=url)
        return response

    def test_logged_in_pages(self):
        self.client.force_login(self.user)
        pages = [
            (reverse("home"), None),
            (reverse("profile_detail"), "Profile"),
            (reverse("edit_profile"), "Profile"),
            (reverse("board:board"), "Board"),
            (reverse("board:my_posts"), "Board"),
            (reverse("board:create_post"), "Board"),
            (reverse("chat:inbox"), "Chat"),
            (reverse("chat:room", args=[self.conversation.id]), "Chat"),
            (reverse("find_match"), "Match"),
            (reverse("create_project"), "Match"),
            (reverse("categories:category-list"), None),
        ]
        for url, active in pages:
            with self.subTest(url=url):
                response = self.assert_navbar(url, active)
                self.assertContains(response, "Log Out")

    def test_guest_pages(self):
        pages = [
            (reverse("home"), None),
            (reverse("login"), "Log In"),
            (reverse("register"), "Register"),
            (reverse("board:board"), "Board"),
            (reverse("categories:category-list"), None),
        ]
        for url, active in pages:
            with self.subTest(url=url):
                response = self.assert_navbar(url, active)
                self.assertNotContains(response, "Log Out")
                self.assertNotContains(response, reverse("chat:inbox"))
