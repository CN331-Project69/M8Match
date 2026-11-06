from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    team_details = models.TextField(blank=True)
    requirements_details = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s Project"