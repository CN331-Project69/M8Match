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
    Find projects that match the current user's request.

    Matching rules:
    1. User with a team searches for people.
    2. User without a team searches for teams.
    3. At least one matching skill is required.
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

    has_team = bool(my_project.team_details.strip())

    my_skills = normalize_skills(my_project.requirements_details)

    if not my_skills:
        return []

    candidate_projects = (
        Project.objects.filter(is_active=True)
        .exclude(user=user)
        .select_related(
            "user",
            "user__profile",
        )
    )

    matches = []

    for candidate in candidate_projects:
        candidate_has_team = bool(candidate.team_details.strip())

        # Find people when the current user has a team.
        # Find teams when the current user has no team.
        if candidate_has_team == has_team:
            continue

        candidate_skills = normalize_skills(candidate.requirements_details)

        common_skills = my_skills & candidate_skills

        if common_skills:
            matches.append(
                {
                    "project": candidate,
                    "matched_skills": sorted(common_skills),
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
