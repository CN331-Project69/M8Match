from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from categories.models import Category
from .models import Post, PostImage
from .services import create_post, update_post, delete_post


User = get_user_model()


class PostServiceTests(TestCase):
    """ทดสอบการทำงานของ Post Service"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123"
        )

        self.category1 = Category.objects.create(
            name="Programming"
        )

        self.category2 = Category.objects.create(
            name="Design"
        )

    def create_test_image(self, name="test.png"):
        """สร้างไฟล์รูปภาพจำลองสำหรับทดสอบ"""
        return SimpleUploadedFile(
            name,
            b"test-image-content",
            content_type="image/png"
        )

    def test_create_post(self):
        """ทดสอบสร้าง Post พร้อม Category และรูปภาพ"""

        post = create_post(
            author=self.user,
            title="Test Post",
            content="This is a test post.",
            categories=[self.category1],
            images=[self.create_test_image()]
        )

        self.assertEqual(post.title, "Test Post")
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.categories.count(), 1)
        self.assertEqual(post.images.count(), 1)
        self.assertFalse(post.is_edited)

    def test_update_post(self):
        """ทดสอบแก้ไขข้อมูล Post และ Category"""

        post = create_post(
            author=self.user,
            title="Old Title",
            content="Old Content",
            categories=[self.category1]
        )

        updated_post = update_post(
            post=post,
            title="New Title",
            content="New Content",
            categories=[self.category2]
        )

        updated_post.refresh_from_db()

        self.assertEqual(updated_post.title, "New Title")
        self.assertEqual(updated_post.content, "New Content")
        self.assertEqual(
            list(updated_post.categories.all()),
            [self.category2]
        )
        self.assertTrue(updated_post.is_edited)

    def test_update_post_images(self):
        """ทดสอบเพิ่มและลบรูปภาพ"""

        post = create_post(
            author=self.user,
            title="Image Post",
            content="Testing images",
            images=[self.create_test_image("old.png")]
        )

        old_image = post.images.first()

        update_post(
            post=post,
            title=post.title,
            content=post.content,
            new_images=[self.create_test_image("new.png")],
            delete_images=[old_image]
        )

        self.assertEqual(post.images.count(), 1)
        self.assertTrue(post.is_edited)

    def test_update_without_changes(self):
        """ทดสอบว่าไม่ตั้ง is_edited เมื่อไม่มีการเปลี่ยนแปลง"""

        post = create_post(
            author=self.user,
            title="Same Title",
            content="Same Content"
        )

        update_post(
            post=post,
            title=post.title,
            content=post.content,
            categories=list(post.categories.all())
        )

        post.refresh_from_db()
        self.assertFalse(post.is_edited)

    def test_delete_post(self):
        """ทดสอบลบ Post และข้อมูลรูปภาพที่เกี่ยวข้อง"""

        post = create_post(
            author=self.user,
            title="Delete Me",
            content="This post will be deleted.",
            images=[self.create_test_image()]
        )

        post_id = post.id
        delete_post(post=post)

        self.assertFalse(
            Post.objects.filter(id=post_id).exists()
        )

        self.assertFalse(
            PostImage.objects.filter(post_id=post_id).exists()
        )


class PostPermissionTests(TestCase):
    """ทดสอบสิทธิ์การเข้าถึง Post"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="owner",
            password="testpassword123"
        )

        self.other_user = User.objects.create_user(
            username="other",
            password="testpassword123"
        )

        self.post = Post.objects.create(
            author=self.user,
            title="My Post",
            content="My content"
        )

    def test_guest_cannot_create_post(self):
        """Guest ไม่สามารถสร้าง Post ได้"""

        response = self.client.get(
            reverse("board:create_post")
        )

        self.assertEqual(response.status_code, 302)

    def test_guest_cannot_edit_post(self):
        """Guest ไม่สามารถแก้ไข Post ได้"""

        response = self.client.get(
            reverse("board:edit_post", args=[self.post.id])
        )

        self.assertEqual(response.status_code, 302)

    def test_guest_cannot_delete_post(self):
        """Guest ไม่สามารถลบ Post ได้"""

        response = self.client.post(
            reverse("board:delete_post", args=[self.post.id])
        )

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Post.objects.filter(id=self.post.id).exists()
        )

    def test_user_cannot_edit_other_users_post(self):
        """ผู้ใช้ไม่สามารถแก้ไข Post ของคนอื่นได้"""

        self.client.login(
            username="other",
            password="testpassword123"
        )

        response = self.client.get(
            reverse("board:edit_post", args=[self.post.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_delete_other_users_post(self):
        """ผู้ใช้ไม่สามารถลบ Post ของคนอื่นได้"""

        self.client.login(
            username="other",
            password="testpassword123"
        )

        response = self.client.post(
            reverse("board:delete_post", args=[self.post.id])
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            Post.objects.filter(id=self.post.id).exists()
        )