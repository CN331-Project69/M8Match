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


class CommentAuthorProfileTests(TestCase):
    """คอมเมนต์: ชื่อผู้คอมเมนต์กดดูโปรไฟล์ได้ และมีลิงก์แชท"""

    def setUp(self):
        from .models import Comment

        User = get_user_model()
        self.me = User.objects.create_user(username="me", password="x")
        self.commenter = User.objects.create_user(username="helper", password="x")
        post = Post.objects.create(author=self.me, title="Need help", content="Anyone?")
        Comment.objects.create(post=post, author=self.commenter, content="Me!")
        Comment.objects.create(post=post, author=self.me, content="Thanks")
        self.url = reverse("board:post_comments", args=[post.id])
        self.client.force_login(self.me)

    def test_comment_json_has_profile_and_chat_urls(self):
        comments = {c["author_name"]: c for c in self.client.get(self.url).json()["comments"]}

        self.assertEqual(comments["helper"]["author_profile_url"], reverse("user_profile", args=["helper"]))
        self.assertEqual(comments["helper"]["author_chat_url"], reverse("chat:start", args=[self.commenter.id]))
        # คอมเมนต์ของตัวเอง: มีลิงก์โปรไฟล์ แต่ไม่มีปุ่มแชท
        self.assertEqual(comments["me"]["author_profile_url"], reverse("user_profile", args=["me"]))
        self.assertIsNone(comments["me"]["author_chat_url"])


class LikeWithoutReloadTests(TestCase):
    """กด Like ผ่าน fetch ได้ JSON กลับมา ไม่ต้องโหลดหน้าใหม่"""

    def setUp(self):
        User = get_user_model()
        self.me = User.objects.create_user(username="me", password="x")
        writer = User.objects.create_user(username="writer", password="x")
        self.post = Post.objects.create(author=writer, title="Hello", content="World")
        self.url = reverse("board:toggle_like", args=[self.post.id])
        self.client.force_login(self.me)

    def test_json_like_and_unlike(self):
        first = self.client.post(self.url, HTTP_ACCEPT="application/json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json(), {"liked": True, "like_count": 1})

        second = self.client.post(self.url, HTTP_ACCEPT="application/json")
        self.assertEqual(second.json(), {"liked": False, "like_count": 0})

    def test_plain_form_still_redirects(self):
        response = self.client.post(self.url, {"next": "/board/"})
        self.assertRedirects(response, "/board/", fetch_redirect_response=False)

    def test_board_has_ajax_like_form(self):
        response = self.client.get(reverse("board:board"))
        self.assertContains(response, 'class="like-form"')
        self.assertContains(response, 'class="like-count"')


class CommentAvatarTests(TestCase):
    def test_comment_has_picture_and_display_name(self):
        from accounts.models import Profile

        from .models import Comment

        User = get_user_model()
        me = User.objects.create_user(username="me", password="x")
        helper = User.objects.create_user(username="helper", password="x")
        Profile.objects.create(user=helper, display_name="Helper Jane", profile_picture="profile_pics/jane.png")
        post = Post.objects.create(author=me, title="Q", content="?")
        Comment.objects.create(post=post, author=helper, content="Hi")

        self.client.force_login(me)
        comment = self.client.get(reverse("board:post_comments", args=[post.id])).json()["comments"][0]
        self.assertEqual(comment["author_name"], "Helper Jane")
        self.assertTrue(comment["author_picture"].endswith("profile_pics/jane.png"))
