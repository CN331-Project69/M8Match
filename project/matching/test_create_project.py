from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Category

from .models import Project


class CreateProjectViewTests(TestCase):
    """กรอกโปรเจกต์ / ทีม แล้วไปหน้า Find Match"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="me", password="x")
        self.web = Category.objects.create(name="Web Dev", slug="web-dev")
        self.ui = Category.objects.create(name="UI Design", slug="ui-design")
        self.client.force_login(self.user)
        self.url = reverse("create_project")

    def test_requires_at_least_one_required_skill(self):
        response = self.client.post(self.url, {"requirements_details": "Need help"})
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertFalse(Project.objects.exists())

    def test_create_then_update_project(self):
        response = self.client.post(self.url, {
            "team_details": "We are 2 devs",
            "requirements_details": "Need a designer",
            "team_categories": [self.web.id],
            "required_categories": [self.ui.id],
        })
        self.assertRedirects(response, reverse("find_match"), fetch_redirect_response=False)
        project = Project.objects.get(user=self.user)
        self.assertEqual(list(project.required_categories.all()), [self.ui])
        self.assertTrue(self.client.get(self.url).context["has_team"])

        self.client.post(self.url, {"requirements_details": "Updated", "required_categories": [self.web.id]})
        self.assertEqual(Project.objects.filter(user=self.user).count(), 1)
        project.refresh_from_db()
        self.assertEqual(project.requirements_details, "Updated")

        page = self.client.get(self.url)
        self.assertEqual(page.status_code, 200)
        # ส่งครั้งที่สองไม่ได้ใส่ข้อมูลทีม -> ข้อมูลทีมถูกล้าง
        self.assertFalse(page.context["has_team"])
        self.assertEqual(list(page.context["selected_required_categories"]), [self.web.id])
