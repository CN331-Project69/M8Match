from django.db import models
from django.conf import settings
from django.db.models import Q, F


class Project(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    team_details = models.TextField(blank=True)
    requirements_details = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s Project"


class Swipe(models.Model):
    LEFT = "left"
    RIGHT = "right"

    SWIPE_CHOICES = [
        (LEFT, "Swipe Left"),
        (RIGHT, "Swipe Right"),
    ]

    swiper = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="swipes_made",
    )

    swiped_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="swipes_received",
    )

    direction = models.CharField(
        max_length=5,
        choices=SWIPE_CHOICES,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["swiper", "swiped_user"],
                name="unique_user_swipe",
            ),
            models.CheckConstraint(
                condition=~Q(swiper=F("swiped_user")),
                name="prevent_self_swipe",
            ),
        ]

    def __str__(self):
        return f"{self.swiper} -> {self.swiped_user}: {self.direction}"


class Match(models.Model):
    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="matches_as_user1",
    )

    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="matches_as_user2",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user1", "user2"],
                name="unique_user_match",
            ),
            models.CheckConstraint(
                condition=~Q(user1=F("user2")),
                name="prevent_self_match",
            ),
        ]

    def __str__(self):
        return f"{self.user1} matched with {self.user2}"
