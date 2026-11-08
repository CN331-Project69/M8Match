import re

from .models import Project

from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from .models import Project, Swipe, Match


def normalize_skills(text):
    """
    Convert skill text into a set of normalized skills.
    Example: "Python, Django, UI/UX"
    """
    if not text:
        return set()

    skills = re.split(r"[,;\n]+", text)

    return {skill.strip().lower() for skill in skills if skill.strip()}


def find_matching_projects(user):
    """
    Find matching projects based on required categories.

    Matching rules:
    1. Users with a team search for people without a team.
    2. Users without a team search for teams.
    3. Both sides use required_categories for matching.
    """

    my_project = (
        Project.objects.filter(
            user=user,
            is_active=True,
        )
        .order_by("-id")
        .first()
    )

    if not my_project:
        return []

    has_team = bool(
        (my_project.team_details or "").strip() or my_project.team_categories.exists()
    )

    candidate_projects = (
        Project.objects.filter(is_active=True)
        .exclude(user=user)
        .select_related("user", "user__profile")
        .prefetch_related(
            "team_categories",
            "required_categories",
        )
    )

    my_categories = {
        category.name.strip().lower()
        for category in my_project.required_categories.all()
        if category.is_active
    }

    matches = []

    for candidate in candidate_projects:
        candidate_has_team = bool(
            (candidate.team_details or "").strip() or candidate.team_categories.exists()
        )

        # Only match users with different team statuses.
        if candidate_has_team == has_team:
            continue

        candidate_categories = {
            category.name.strip().lower()
            for category in candidate.required_categories.all()
            if category.is_active
        }

        common_categories = my_categories & candidate_categories

        if common_categories:
            # Collect all required categories from the candidate.
            all_categories = {
                category.name.strip().lower(): category.name.strip()
                for category in candidate.required_categories.all()
                if category.is_active
            }

            matches.append(
                {
                    "project": candidate,
                    "matched_skills": sorted(common_categories),
                    "all_skills": [
                        {
                            "name": name,
                            "is_matched": key in common_categories,
                        }
                        for key, name in sorted(
                            all_categories.items(),
                            key=lambda item: (
                                item[0] not in common_categories,
                                item[0],
                            ),
                        )
                    ],
                }
            )

    return matches


@transaction.atomic
def swipe_user(user, target_user_id, direction):
    """
    Save a user's swipe and create a Match
    when both users swipe right.
    """

    User = get_user_model()

    # Validate swipe direction
    if direction not in [Swipe.LEFT, Swipe.RIGHT]:
        raise ValidationError("Invalid swipe direction.")

    # Find target user
    try:
        target_user = User.objects.get(pk=target_user_id)
    except User.DoesNotExist:
        raise ValidationError("User not found.")

    # Prevent swiping yourself
    if user.pk == target_user.pk:
        raise ValidationError("You cannot swipe yourself.")

    # Prevent duplicate swipes
    if Swipe.objects.filter(
        swiper=user,
        swiped_user=target_user,
    ).exists():
        raise ValidationError("You have already swiped this user.")

    # Save swipe
    swipe = Swipe.objects.create(
        swiper=user,
        swiped_user=target_user,
        direction=direction,
    )

    matched = False
    match = None

    # Check mutual right swipe
    if direction == Swipe.RIGHT:
        mutual_like = Swipe.objects.filter(
            swiper=target_user,
            swiped_user=user,
            direction=Swipe.RIGHT,
        ).exists()

        if mutual_like:
            # Keep user order consistent
            user1, user2 = sorted(
                [user, target_user],
                key=lambda item: item.pk,
            )

            match, created = Match.objects.get_or_create(
                user1=user1,
                user2=user2,
            )

            matched = created

    return {
        "swipe": swipe,
        "matched": matched,
        "match": match,
    }
