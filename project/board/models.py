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


class PostLike(models.Model):
    # Post ที่ถูกกด Like
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="likes"
    )

    # User ที่กด Like
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="board_likes"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # User หนึ่งคนมีข้อมูล Like สำหรับ Post เดียวกันได้เพียงหนึ่งรายการ
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["post", "user"],
                name="unique_post_like"
            )
        ]


class Comment(models.Model):
    # โพสต์ที่คอมเมนต์นี้อยู่
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    # เจ้าของคอมเมนต์
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="board_comments"
    )

    # เนื้อหาคอมเมนต์
    content = models.TextField()

    # สถานะการแก้ไขและซ่อนคอมเมนต์
    is_edited = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)

    # วันเวลาที่สร้างและแก้ไข
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]


class PostReport(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="reports"
    )

    # ผู้กดรายงานไม่ใช่เจ้าของ Post
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_post_reports"
    )

    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["post", "reporter"],
                name="unique_post_report"
            )
        ]


class CommentReport(models.Model):
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name="reports"
    )

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_comment_reports"
    )

    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["comment", "reporter"],
                name="unique_comment_report"
            )
        ]
