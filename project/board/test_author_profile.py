from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from chat.models import Conversation

from .models import Post
from .views import get_post_cards


class PostAuthorProfileTests(TestCase):
    """กดดูโปรไฟล์ของคนโพสต์ และกดแชทไปหาได้จากบอร์ด"""

    def setUp(self):
        User = get_user_model()
        self.me = User.objects.create_user(username="me", password="x")
        self.author = User.objects.create_user(username="writer", password="x")
        self.post = Post.objects.create(author=self.author, title="Need a designer", content="Join us")
        self.my_post = Post.objects.create(author=self.me, title="My own post", content="Hi")

        self.profile_url = reverse("user_profile", args=["writer"])
        self.chat_url = reverse("chat:start", args=[self.author.id])

    def test_logged_in_sees_profile_link_and_message_button(self):
        self.client.force_login(self.me)
        response = self.client.get(reverse("board:board"))

        self.assertContains(response, f'class="author-name" href="{self.profile_url}"')
        self.assertContains(response, f'class="avatar" href="{self.profile_url}"')
        self.assertContains(response, f'action="{self.chat_url}"')

    def test_no_message_button_on_own_post(self):
        self.client.force_login(self.me)
        response = self.client.get(reverse("board:board"))
        self.assertNotContains(response, reverse("chat:start", args=[self.me.id]))

    def test_guest_sees_name_only(self):
        response = self.client.get(reverse("board:board"))
        self.assertContains(response, '<span class="author-name">writer</span>', html=True)
        self.assertNotContains(response, self.profile_url)
        self.assertNotContains(response, self.chat_url)

    def test_profile_link_opens_author_profile(self):
        self.client.force_login(self.me)
        response = self.client.get(self.profile_url)
        self.assertContains(response, "@writer")

    def test_message_button_opens_chat_with_author(self):
        self.client.force_login(self.me)
        response = self.client.post(self.chat_url)

        room = Conversation.objects.filter(participants=self.me).get(participants=self.author)
        self.assertRedirects(response, reverse("chat:room", args=[room.id]))

    def test_adapter_profile_url_takes_priority(self):
        class FakeAdapter:
            def get_post_interaction_data(self, posts, user):
                return {}

            def get_public_profile_url(self, user):
                return f"/custom-profile/{user.username}/"

        cards = get_post_cards([self.post], self.me, adapter=FakeAdapter())
        self.assertEqual(cards[0]["author_profile_url"], "/custom-profile/writer/")
        self.assertEqual(cards[0]["author_chat_url"], self.chat_url)
