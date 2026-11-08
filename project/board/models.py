from django.db import models
from django.conf import settings


class Post(models.Model):
    # ผู้เขียนโพส เชื่อมกับระบบ User ของโปรเจกต์
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="board_posts"
    )

    # หัวข้อและเนื้อหาโพส
    title = models.CharField(max_length=200)
    content = models.TextField()

    # เลือก Category ได้หลายหมวด หรือไม่เลือกเลยก็ได้
    categories = models.ManyToManyField(
        "categories.Category",
        blank=True,
        related_name="posts"
    )

    # สถานะของโพส
    is_edited = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)

    # วันเวลาที่สร้างและแก้ไขล่าสุด
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.author}"


class PostImage(models.Model):
    # รูปภาพแต่ละรูปจะเชื่อมกับโพสหนึ่งโพส
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(upload_to="board_posts/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for post {self.post.id}"