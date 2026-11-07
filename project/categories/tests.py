from django.test import TestCase
from django.urls import reverse
from django.db import IntegrityError, transaction

from .models import Category


class CategoryModelTests(TestCase):
    def test_create_category(self):
        """Category can be created successfully."""

        category = Category.objects.create(
            name="Programming", description="Programming competitions"
        )

        self.assertEqual(category.name, "Programming")
        self.assertEqual(category.description, "Programming competitions")
        self.assertTrue(category.is_active)

    def test_category_name_must_be_unique(self):
        """Duplicate category names are not allowed."""

        Category.objects.create(name="Programming")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(name="Programming")

    def test_category_slug_is_generated_automatically(self):
        """Slug should be generated from category name."""

        category = Category.objects.create(name="Artificial Intelligence")

        self.assertEqual(category.slug, "artificial-intelligence")

    def test_category_string_representation(self):
        category = Category.objects.create(name="Finance")

        self.assertEqual(str(category), "Finance")


class CategoryViewTests(TestCase):
    def setUp(self):
        self.active_category = Category.objects.create(
            name="Programming", is_active=True
        )

        self.inactive_category = Category.objects.create(
            name="Finance", is_active=False
        )

    def test_category_list_returns_200(self):
        """Category list page should load successfully."""

        response = self.client.get(reverse("categories:category-list"))

        self.assertEqual(response.status_code, 200)

    def test_category_list_uses_correct_template(self):
        response = self.client.get(reverse("categories:category-list"))

        self.assertTemplateUsed(response, "categories/category_list.html")

    def test_only_active_categories_are_displayed(self):
        """Inactive categories should not appear."""

        response = self.client.get(reverse("categories:category-list"))

        categories = response.context["categories"]

        self.assertIn(self.active_category, categories)

        self.assertNotIn(self.inactive_category, categories)

        self.assertContains(response, "Programming")

        self.assertNotContains(response, "Finance")
