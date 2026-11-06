from django.db import models
from django.conf import settings

# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=50, blank=True)
    about_me = models.TextField(blank=True)
    skills = models.CharField(max_length=255, blank=True, help_text="เช่น Python, Django, UI/UX")
    # ImageField ต้องติดตั้งไลบรารี Pillow (pip install Pillow) ก่อนรัน makemigrations
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"