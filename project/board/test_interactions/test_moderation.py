
from django.test import SimpleTestCase

from ..moderation.service import (
    moderate_post,
    moderate_comment,
)


class ModerationTests(SimpleTestCase):

    def test_normal_comment(self):
        result = moderate_comment("สนใจเข้าร่วมทีม")

        self.assertTrue(result["is_allowed"])

    def test_empty_comment(self):
        result = moderate_comment("   ")

        self.assertFalse(result["is_allowed"])
        self.assertIn("content", result["errors"])

    def test_spam_comment(self):
        result = moderate_comment("aaaaaaaaaaaa")

        self.assertFalse(result["is_allowed"])

    def test_normal_post(self):
        result = moderate_post(
            "หาสมาชิกทีม",
            "ต้องการคนเขียน Python"
        )

        self.assertTrue(result["is_allowed"])

    def test_empty_post_title(self):
        result = moderate_post(
            "",
            "เนื้อหาปกติ"
        )

        self.assertFalse(result["is_allowed"])
        self.assertIn("title", result["errors"])

    def test_suspicious_link_warning(self):
        result = moderate_comment(
            "ดูรายละเอียด http://192.0.2.1"
        )

        self.assertTrue(result["is_allowed"])
        self.assertIn("content", result["warnings"])
