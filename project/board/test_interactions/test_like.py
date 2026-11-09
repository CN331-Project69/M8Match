
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied

from ..models import Post, PostLike, Comment
from ..like_service import (
    toggle_like,
    get_post_interaction_data,
    get_liked_posts,
)


class LikeTests(TestCase):

    def setUp(self):
        # สร้าง User สำหรับทดสอบ
        User = get_user_model()

        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

        # สร้าง Post สำหรับทดสอบ
        self.post = Post.objects.create(
            author=self.user,
            title="Test Post",
            content="This is a test post."
        )

    def test_like_post(self):
        # กด Like ครั้งแรก
        result = toggle_like(self.post, self.user)

        self.assertTrue(result["liked"])
        self.assertEqual(result["like_count"], 1)

        # ตรวจว่ามี Like อยู่ในฐานข้อมูลจริง
        self.assertTrue(
            PostLike.objects.filter(
                post=self.post,
                user=self.user
            ).exists()
        )

    def test_unlike_post(self):
        # กด Like ก่อน
        toggle_like(self.post, self.user)

        # กดซ้ำเพื่อ Unlike
        result = toggle_like(self.post, self.user)

        self.assertFalse(result["liked"])
        self.assertEqual(result["like_count"], 0)

        # ตรวจว่า Like ถูกลบจากฐานข้อมูลแล้ว
        self.assertFalse(
            PostLike.objects.filter(
                post=self.post,
                user=self.user
            ).exists()
        )

    def test_guest_cannot_like(self):
        guest = AnonymousUser()

        with self.assertRaises(PermissionDenied):
            toggle_like(self.post, guest)

    def test_post_interaction_data(self):
        # สร้างโพสต์ที่สอง
        post2 = Post.objects.create(
            author=self.user,
            title="Second Post",
            content="Another test post."
        )

        # Like โพสต์แรก
        toggle_like(self.post, self.user)

        # เพิ่ม Comment ให้โพสต์แรก
        Comment.objects.create(
            post=self.post,
            author=self.user,
            content="Hello!"
        )

        # ดึงข้อมูลทั้งสองโพสต์พร้อมกัน
        data = get_post_interaction_data(
            [self.post, post2],
            self.user
        )

        self.assertEqual(
            data[self.post.id]["like_count"], 1
        )
        self.assertEqual(
            data[self.post.id]["comment_count"], 1
        )
        self.assertTrue(
            data[self.post.id]["is_liked"]
        )

        # โพสต์ที่สองยังไม่มี Like / Comment
        self.assertEqual(data[post2.id]["like_count"], 0)
        self.assertEqual(data[post2.id]["comment_count"], 0)
        self.assertFalse(data[post2.id]["is_liked"])

    def test_guest_interaction_data(self):
        toggle_like(self.post, self.user)

        data = get_post_interaction_data(
            [self.post],
            AnonymousUser()
        )

        # Guest เห็นจำนวน Like แต่ไม่ได้ Like เอง
        self.assertEqual(
            data[self.post.id]["like_count"], 1
        )
        self.assertFalse(
            data[self.post.id]["is_liked"]
        )

    def test_hidden_post_not_in_my_likes(self):
        # สร้างโพสต์ที่ถูกซ่อน
        hidden_post = Post.objects.create(
            author=self.user,
            title="Hidden Post",
            content="Hidden content",
            is_hidden=True
        )

        # Like ทั้งสองโพสต์
        toggle_like(self.post, self.user)
        toggle_like(hidden_post, self.user)

        # ดึง My Likes
        liked_posts = get_liked_posts(self.user)

        self.assertIn(self.post, liked_posts)
        self.assertNotIn(hidden_post, liked_posts)
