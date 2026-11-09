
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError

from ..models import Post, Comment
from ..comment_service import get_comments, create_comment


class CommentTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="commentuser",
            password="testpass123"
        )

        self.post = Post.objects.create(
            author=self.user,
            title="Looking for teammates",
            content="We need a Python developer."
        )

    def test_create_comment(self):
        comment = create_comment(
            self.post,
            self.user,
            "I'm interested!"
        )

        self.assertEqual(comment.content, "I'm interested!")
        self.assertEqual(comment.author, self.user)
        self.assertEqual(Comment.objects.count(), 1)

    def test_guest_cannot_create_comment(self):
        with self.assertRaises(PermissionDenied):
            create_comment(
                self.post,
                AnonymousUser(),
                "Hello!"
            )

    def test_guest_cannot_view_comments(self):
        with self.assertRaises(PermissionDenied):
            get_comments(self.post, AnonymousUser())

    def test_empty_comment(self):
        with self.assertRaises(ValidationError):
            create_comment(self.post, self.user, "   ")

    def test_hidden_post_cannot_comment(self):
        self.post.is_hidden = True
        self.post.save()

        with self.assertRaises(ValidationError):
            create_comment(
                self.post,
                self.user,
                "Hello!"
            )

    def test_hidden_comment_not_displayed(self):
        Comment.objects.create(
            post=self.post,
            author=self.user,
            content="Visible comment"
        )

        Comment.objects.create(
            post=self.post,
            author=self.user,
            content="Hidden comment",
            is_hidden=True
        )

        comments = get_comments(self.post, self.user)

        self.assertEqual(comments.count(), 1)
        self.assertEqual(
            comments.first().content,
            "Visible comment"
        )

    def test_spam_comment_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_comment(
                self.post,
                self.user,
                "aaaaaaaaaaaa"
            )

        # ต้องไม่มี Comment ถูกสร้าง
        self.assertEqual(
            Comment.objects.count(),
            0
        )
