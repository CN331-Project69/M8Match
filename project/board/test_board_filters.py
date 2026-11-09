from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Category
from board.models import Post


User = get_user_model()


class BoardFilterTests(TestCase):

    def setUp(self):
        # สร้างผู้ใช้สำหรับทดสอบ
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123"
        )

        # สร้าง Category สำหรับทดสอบ
        self.programming = Category.objects.create(
            name="Programming",
            slug="programming"
        )

        self.design = Category.objects.create(
            name="Design",
            slug="design"
        )

        # สร้างโพสต์ตัวอย่าง
        self.post1 = Post.objects.create(
            author=self.user,
            title="Python Tutorial",
            content="Learn Python programming"
        )
        self.post1.categories.add(self.programming)

        self.post2 = Post.objects.create(
            author=self.user,
            title="Web Design",
            content="Learn website design"
        )
        self.post2.categories.add(self.design)

        self.post3 = Post.objects.create(
            author=self.user,
            title="Django Project",
            content="Build a web application"
        )
        self.post3.categories.add(self.programming)

        self.url = reverse("board:board")

    def test_search_by_title(self):
        # ค้นหาจากชื่อโพสต์
        response = self.client.get(
            self.url,
            {"q": "Python"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["posts"]), 1)
        self.assertEqual(
            response.context["posts"][0]["title"],
            "Python Tutorial"
        )

    def test_search_by_content(self):
        # ค้นหาจากเนื้อหาโพสต์
        response = self.client.get(
            self.url,
            {"q": "website design"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["posts"]), 1)
        self.assertEqual(
            response.context["posts"][0]["title"],
            "Web Design"
        )

    def test_filter_by_category(self):
        # กรองโพสต์ตาม Category
        response = self.client.get(
            self.url,
            {"category": self.programming.id}
        )

        self.assertEqual(response.status_code, 200)

        titles = {
            post["title"]
            for post in response.context["posts"]
        }

        self.assertEqual(
            titles,
            {"Python Tutorial", "Django Project"}
        )

    def test_filter_multiple_categories(self):
        # เลือกหลาย Category พร้อมกัน
        response = self.client.get(
            self.url,
            {
                "category": [
                    self.programming.id,
                    self.design.id
                ]
            }
        )

        self.assertEqual(response.status_code, 200)

        titles = {
            post["title"]
            for post in response.context["posts"]
        }

        self.assertEqual(
            titles,
            {
                "Python Tutorial",
                "Web Design",
                "Django Project"
            }
        )

    def test_search_and_category_filter_together(self):
        # Search และ Category Filter ต้องทำงานร่วมกัน
        response = self.client.get(
            self.url,
            {
                "q": "Project",
                "category": self.programming.id
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["posts"]), 1)
        self.assertEqual(
            response.context["posts"][0]["title"],
            "Django Project"
        )

    def test_pagination_shows_ten_posts_per_page(self):
        # เพิ่มโพสต์ให้มีทั้งหมดมากกว่า 10 โพสต์
        for number in range(12):
            Post.objects.create(
                author=self.user,
                title=f"Extra Post {number}",
                content="Extra content"
            )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["posts"]), 10)
        self.assertTrue(response.context["page_obj"].has_next())

        # ตรวจสอบหน้าที่สอง
        response = self.client.get(
            self.url,
            {"page": 2}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["posts"]), 5)

    def test_guest_only_receives_preview_content(self):
        # สร้างโพสต์ที่มีเนื้อหายาวเกิน 250 ตัวอักษร
        secret_text = "SECRET_TEXT_" * 30

        post = Post.objects.create(
            author=self.user,
            title="Long Post",
            content=secret_text
        )

        # Guest เปิดหน้า Board โดยไม่ได้ Login
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        # ตรวจสอบว่าเนื้อหาส่วนที่เหลือไม่ถูกส่งไปในหน้าเว็บ
        self.assertNotContains(response, secret_text)

        guest_post = next(
            item
            for item in response.context["posts"]
            if item["id"] == post.id
        )

        self.assertEqual(len(guest_post["content"]), 250)
        self.assertTrue(guest_post["is_truncated"])
