import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Profile

# GIF ขนาด 1x1 พิกเซล สำหรับทดสอบอัปโหลดรูป
TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00"
    b"\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)
TEMP_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ProfileViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="mate", email="mate@example.com", password="pass12345"
        )
        self.client.force_login(self.user)

    def test_profile_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("profile_detail"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_empty_profile_shows_username_and_prompts(self):
        response = self.client.get(reverse("profile_detail"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "@mate")
        self.assertContains(response, "Add skills")
        self.assertContains(response, reverse("edit_profile"))

    def test_skills_render_as_tags(self):
        Profile.objects.create(user=self.user, display_name="Mate", skills="Python, , Django ,UI/UX")
        response = self.client.get(reverse("profile_detail"))
        for skill in ("Python", "Django", "UI/UX"):
            self.assertContains(response, f'<li class="skill-tag">{skill}</li>', html=True)

    def test_edit_page_renders(self):
        response = self.client.get(reverse("edit_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Save Profile")

    def test_edit_profile_saves_and_redirects(self):
        response = self.client.post(
            reverse("edit_profile"),
            {
                "display_name": "Mate Jr.",
                "about_me": "Hi!",
                "skills": "Go, Rust",
                "profile_picture": SimpleUploadedFile("a.gif", TINY_GIF, content_type="image/gif"),
            },
        )
        self.assertRedirects(response, reverse("profile_detail"), fetch_redirect_response=False)
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.display_name, "Mate Jr.")
        self.assertEqual(profile.skill_list, ["Go", "Rust"])
        self.assertTrue(profile.profile_picture)

        page = self.client.get(reverse("profile_detail"))
        self.assertContains(page, "Your profile has been updated.")
        self.assertContains(page, profile.profile_picture.url)
