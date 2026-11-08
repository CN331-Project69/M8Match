from django.test import TestCase
from django.contrib.auth import get_user_model

from categories.models import Category
from matching.models import Project
from matching.services import find_matching_projects


User = get_user_model()


class MatchingTests(TestCase):
    def setUp(self):
        self.python = Category.objects.create(name="Python")
        self.django = Category.objects.create(name="Django")
        self.java = Category.objects.create(name="Java")

        self.team_user = User.objects.create_user(
            username="team_user",
            password="test1234",
        )

        self.applicant_user = User.objects.create_user(
            username="applicant_user",
            password="test1234",
        )

    def test_match_when_categories_match_even_if_details_are_different(self):
        team_project = Project.objects.create(
            user=self.team_user,
            team_details="We are a development team",
            requirements_details="Looking for a backend developer",
        )
        team_project.required_categories.add(self.python)

        applicant_project = Project.objects.create(
            user=self.applicant_user,
            team_details="",
            requirements_details="I enjoy designing websites",
        )
        applicant_project.required_categories.add(self.python)

        matches = find_matching_projects(self.team_user)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["project"].user, self.applicant_user)
        self.assertEqual(matches[0]["matched_skills"], ["python"])

    def test_no_match_when_categories_do_not_match(self):
        team_project = Project.objects.create(
            user=self.team_user,
            team_details="We are a development team",
            requirements_details="Python",
        )
        team_project.required_categories.add(self.python)

        applicant_project = Project.objects.create(
            user=self.applicant_user,
            team_details="",
            requirements_details="Python",
        )
        applicant_project.required_categories.add(self.java)

        matches = find_matching_projects(self.team_user)

        self.assertEqual(len(matches), 0)

    def test_applicant_can_find_team_with_matching_category(self):
        applicant_project = Project.objects.create(
            user=self.applicant_user,
            team_details="",
            requirements_details="I want to join a team",
        )
        applicant_project.required_categories.add(self.python)

        team_project = Project.objects.create(
            user=self.team_user,
            team_details="We are a development team",
            requirements_details="Looking for a developer",
        )
        team_project.required_categories.add(self.python)

        matches = find_matching_projects(self.applicant_user)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["project"].user, self.team_user)
        self.assertEqual(matches[0]["matched_skills"], ["python"])

    def test_same_team_type_does_not_match(self):
        first_user = User.objects.create_user(
            username="first_user",
            password="test1234",
        )

        second_user = User.objects.create_user(
            username="second_user",
            password="test1234",
        )

        first_project = Project.objects.create(
            user=first_user,
            team_details="Team A",
            requirements_details="",
        )
        first_project.required_categories.add(self.python)

        second_project = Project.objects.create(
            user=second_user,
            team_details="Team B",
            requirements_details="",
        )
        second_project.required_categories.add(self.python)

        matches = find_matching_projects(first_user)

        self.assertEqual(len(matches), 0)
