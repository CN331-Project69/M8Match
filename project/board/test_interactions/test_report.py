
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError

from ..models import Post, Comment, PostReport, CommentReport
from ..report_service import (
    submit_post_report,
    submit_comment_report,
)


class ReportTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.owner = User.objects.create_user(
            username="owner",
            password="testpass123"
        )
        self.reporter = User.objects.create_user(
            username="reporter",
            password="testpass123"
        )

        self.post = Post.objects.create(
            author=self.owner,
            title="Test Post",
            content="This is a test post."
        )

        self.comment = Comment.objects.create(
            post=self.post,
            author=self.owner,
            content="Test Comment"
        )

    def test_report_post(self):
        report = submit_post_report(
            self.post.id,
            self.reporter,
            "Spam"
        )

        self.assertEqual(report.reason, "Spam")
        self.assertEqual(PostReport.objects.count(), 1)

    def test_report_comment(self):
        report = submit_comment_report(
            self.comment,
            self.reporter,
            "Inappropriate comment"
        )

        self.assertEqual(report.reason, "Inappropriate comment")
        self.assertEqual(CommentReport.objects.count(), 1)

    def test_cannot_report_own_post(self):
        with self.assertRaises(ValidationError):
            submit_post_report(
                self.post.id,
                self.owner,
                "My own post"
            )

    def test_cannot_report_own_comment(self):
        with self.assertRaises(ValidationError):
            submit_comment_report(
                self.comment,
                self.owner,
                "My own comment"
            )

    def test_duplicate_post_report(self):
        submit_post_report(
            self.post.id,
            self.reporter,
            "Spam"
        )

        with self.assertRaises(ValidationError):
            submit_post_report(
                self.post.id,
                self.reporter,
                "Spam again"
            )

    def test_guest_cannot_report(self):
        with self.assertRaises(PermissionDenied):
            submit_post_report(
                self.post.id,
                AnonymousUser(),
                "Spam"
            )

    def test_report_does_not_hide_post(self):
        submit_post_report(
            self.post.id,
            self.reporter,
            "Spam"
        )

        self.post.refresh_from_db()

        self.assertFalse(self.post.is_hidden)

    def test_report_hides_spam_post(self):
        # เปลี่ยนเนื้อหาให้ไม่ผ่านกฎ Spam
        self.post.content = "aaaaaaaaaaaa"
        self.post.save()

        submit_post_report(
            self.post.id,
            self.reporter,
            "Spam"
        )

        self.post.refresh_from_db()

        self.assertTrue(self.post.is_hidden)

    def test_report_hides_spam_comment(self):
        self.comment.content = "aaaaaaaaaaaa"
        self.comment.save()

        submit_comment_report(
            self.comment,
            self.reporter,
            "Spam"
        )

        self.comment.refresh_from_db()

        self.assertTrue(self.comment.is_hidden)
