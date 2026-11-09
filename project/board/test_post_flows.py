import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.datastructures import MultiValueDict
from PIL import Image

from .forms import PostForm
from .models import Comment, CommentReport, Post, PostReport

TEMP_MEDIA = tempfile.mkdtemp()


def image_file(name="a.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), "pink").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class PostFlowTests(TestCase):
    """สร้าง / แก้ไข / ลบโพสต์"""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        User = get_user_model()
        self.me = User.objects.create_user(username="me", password="x")
        self.other = User.objects.create_user(username="other", password="x")
        self.client.force_login(self.me)

    def test_create_post_with_image(self):
        response = self.client.post(reverse("board:create_post"), {
            "title": "Need a designer", "content": "Join our hackathon team", "images": [image_file()],
        })
        self.assertRedirects(response, reverse("board:board"), fetch_redirect_response=False)
        post = Post.objects.get(title="Need a designer")
        self.assertEqual(post.author, self.me)
        self.assertEqual(post.images.count(), 1)

    def test_create_post_rejected_by_moderation(self):
        response = self.client.post(reverse("board:create_post"), {
            "title": "Spam", "content": "aaaaaaaaaaaaaaaa",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Potential spam detected.")
        self.assertFalse(Post.objects.exists())

    def test_create_post_suspicious_link_warns_but_saves(self):
        self.client.post(reverse("board:create_post"), {
            "title": "Link", "content": "see http://1.2.3.4/page",
        })
        self.assertTrue(Post.objects.filter(title="Link").exists())

    def test_edit_post(self):
        post = Post.objects.create(author=self.me, title="Old", content="Old content")
        self.assertEqual(self.client.get(reverse("board:edit_post", args=[post.id])).status_code, 200)

        response = self.client.post(reverse("board:edit_post", args=[post.id]), {
            "title": "New", "content": "New content",
        })
        self.assertRedirects(response, reverse("board:board"), fetch_redirect_response=False)
        post.refresh_from_db()
        self.assertEqual((post.title, post.is_edited), ("New", True))

    def test_edit_post_rejected_by_moderation(self):
        post = Post.objects.create(author=self.me, title="Old", content="Old content")
        response = self.client.post(reverse("board:edit_post", args=[post.id]), {
            "title": "Old", "content": "zzzzzzzzzzzzzzzz",
        })
        self.assertContains(response, "Potential spam detected.")
        post.refresh_from_db()
        self.assertEqual(post.content, "Old content")

    def test_cannot_edit_or_delete_others_post(self):
        post = Post.objects.create(author=self.other, title="Theirs", content="x")
        self.assertEqual(self.client.get(reverse("board:edit_post", args=[post.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse("board:delete_post", args=[post.id])).status_code, 404)

    def test_delete_post(self):
        post = Post.objects.create(author=self.me, title="Bye", content="x")
        self.assertEqual(self.client.get(reverse("board:delete_post", args=[post.id])).status_code, 200)
        self.client.post(reverse("board:delete_post", args=[post.id]))
        self.assertFalse(Post.objects.filter(id=post.id).exists())

    def test_my_posts_page(self):
        Post.objects.create(author=self.me, title="Mine", content="x")
        self.assertContains(self.client.get(reverse("board:my_posts")), "Mine")


class PostFormTests(TestCase):
    def test_blank_title_and_content_are_rejected(self):
        form = PostForm(data={"title": "   ", "content": "   "})
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("content", form.errors)

    def test_more_than_three_images_rejected(self):
        files = MultiValueDict({"images": [image_file(f"{i}.png") for i in range(4)]})
        form = PostForm(data={"title": "T", "content": "C"}, files=files)
        self.assertFalse(form.is_valid())
        self.assertIn("images", form.errors)

    def test_image_too_large_rejected(self):
        big = image_file("big.png")
        big.size = 5 * 1024 * 1024 + 1
        form = PostForm(data={"title": "T", "content": "C"}, files=MultiValueDict({"images": [big]}))
        self.assertFalse(form.is_valid())
        self.assertIn("images", form.errors)


class CommentAndReportFlowTests(TestCase):
    """คอมเมนต์และรายงานโพสต์ / คอมเมนต์"""

    def setUp(self):
        User = get_user_model()
        self.me = User.objects.create_user(username="me", password="x")
        self.other = User.objects.create_user(username="other", password="x")
        self.post = Post.objects.create(author=self.other, title="Hello", content="World")
        self.client.force_login(self.me)

    def test_create_comment(self):
        response = self.client.post(reverse("board:create_comment", args=[self.post.id]), {"content": "Nice!"})
        self.assertLess(response.status_code, 400)
        self.assertTrue(Comment.objects.filter(post=self.post, author=self.me, content="Nice!").exists())

    def test_invalid_comments_are_rejected(self):
        url = reverse("board:create_comment", args=[self.post.id])
        for content in ["", "x" * 2001, "bbbbbbbbbbbbbbbb"]:
            with self.subTest(length=len(content)):
                response = self.client.post(url, {"content": content})
                self.assertGreaterEqual(response.status_code, 400)
        self.assertFalse(Comment.objects.exists())

    def test_guest_cannot_read_comments(self):
        self.client.logout()
        response = self.client.get(reverse("board:post_comments", args=[self.post.id]))
        self.assertEqual(response.status_code, 302)

    def test_report_post(self):
        url = reverse("board:report_post", args=[self.post.id])
        self.assertEqual(self.client.post(url, {"reason": "Spam"}).json()["success"], True)
        self.assertEqual(PostReport.objects.filter(post=self.post, reporter=self.me).count(), 1)

        # รายงานซ้ำ / ไม่ใส่เหตุผล
        self.assertEqual(self.client.post(url, {"reason": "Again"}).status_code, 400)
        self.assertEqual(self.client.post(url, {"reason": ""}).status_code, 302)

    def test_cannot_report_own_post(self):
        mine = Post.objects.create(author=self.me, title="Mine", content="x")
        response = self.client.post(reverse("board:report_post", args=[mine.id]), {"reason": "x"})
        self.assertEqual(response.status_code, 400)

    def test_report_comment(self):
        comment = Comment.objects.create(post=self.post, author=self.other, content="Rude")
        url = reverse("board:report_comment", args=[comment.id])
        self.assertEqual(self.client.post(url, {"reason": ""}).status_code, 400)
        self.assertEqual(self.client.post(url, {"reason": "Rude"}).json()["success"], True)
        self.assertTrue(CommentReport.objects.filter(comment=comment, reporter=self.me).exists())

        missing = reverse("board:report_comment", args=[99999])
        self.assertEqual(self.client.post(missing, {"reason": "x"}).status_code, 404)
