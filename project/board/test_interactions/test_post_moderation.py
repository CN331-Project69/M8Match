
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from ..models import Post
from ..services import create_post, update_post


class PostModerationTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="postuser",
            password="testpass123"
        )

    def test_create_normal_post(self):
        post = create_post(
            author=self.user,
            title="Looking for teammates",
            content="We need a Python developer."
        )

        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(post.author, self.user)

    def test_create_spam_post_rejected(self):
        with self.assertRaises(ValidationError):
            create_post(
                author=self.user,
                title="aaaaaaaaaaaa",
                content="Normal content"
            )

        self.assertEqual(Post.objects.count(), 0)

    def test_update_spam_post_rejected(self):
        post = create_post(
            author=self.user,
            title="Normal Post",
            content="Normal content"
        )

        with self.assertRaises(ValidationError):
            update_post(
                post=post,
                title="aaaaaaaaaaaa",
                content="Normal content"
            )

        post.refresh_from_db()

        self.assertEqual(post.title, "Normal Post")
        self.assertFalse(post.is_edited)

    def test_empty_title_rejected(self):
        with self.assertRaises(ValidationError):
            create_post(
                author=self.user,
                title="   ",
                content="Normal content"
            )

        self.assertEqual(Post.objects.count(), 0)
