
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import Post, Comment
from .moderation.service import moderate_comment


def get_comments(post, user):
    if not user.is_authenticated:
        raise PermissionDenied(
            "Log in to view comments."
        )

    if not Post.objects.filter(
        pk=post.pk,
        is_hidden=False
    ).exists():
        raise PermissionDenied(
            "Unable to view comments for this post."
        )

    return (
        Comment.objects
        .filter(
            post=post,
            is_hidden=False
        )
        .select_related("author")
        .order_by("created_at", "id")
    )


@transaction.atomic
def create_comment(post, user, content):
    # ตรวจสอบการเข้าสู่ระบบ
    if not user.is_authenticated:
        raise PermissionDenied(
            "Log in to write comments."
        )

    # ตรวจสอบเนื้อหาด้วย Moderation
    result = moderate_comment(
        content=content,
        user=user
    )

    if not result["is_allowed"]:
        raise ValidationError(result["errors"])

    # ตรวจสอบว่า Post ยังแสดงอยู่
    if not Post.objects.filter(
        pk=post.pk,
        is_hidden=False
    ).exists():
        raise ValidationError(
            "Cannot comment on this post."
        )

    # สร้าง Comment
    return Comment.objects.create(
        post=post,
        author=user,
        content=content.strip()
    )
