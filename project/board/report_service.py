
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from .models import Post, PostReport, CommentReport
from .moderation.service import (
    review_reported_post,
    review_reported_comment,
)

def validate_report(user, owner, reason):
    # ต้อง Login ก่อน
    if not user.is_authenticated:
        raise PermissionDenied(
            "Please log in to report."
        )

    # ห้ามรายงานเนื้อหาของตัวเอง
    if user.pk == owner.pk:
        raise ValidationError(
            "Cannot report your own post."
        )

    # ตรวจสอบเหตุผล
    if not isinstance(reason, str) or not reason.strip():
        raise ValidationError(
            "Please provide a reason."
        )

    if len(reason.strip()) > 1000:
        raise ValidationError(
            "Maximum 1,000 characters."
        )

    return reason.strip()


def submit_post_report(post_id, user, reason):
    # ค้นหาโพสต์ที่ต้องการรายงาน
    post = (
        Post.objects
        .select_related("author")
        .filter(pk=post_id)
        .first()
    )

    if post is None:
        raise ValidationError("Post not found.")

    reason = validate_report(user, post.author, reason)

    # ป้องกันการรายงานซ้ำ
    try:
        with transaction.atomic():
            report, created = PostReport.objects.get_or_create(
                post=post,
                reporter=user,
                defaults={"reason": reason}
            )
    except IntegrityError:
        raise ValidationError("Unable to save report.")

    if not created:
        raise ValidationError("You have already reported this post.")

    # ตรวจเนื้อหาซ้ำหลังได้รับ Report ใหม่
    review_reported_post(post)

    return report


def submit_comment_report(comment, user, reason):
    reason = validate_report(user, comment.author, reason)

    try:
        with transaction.atomic():
            report, created = CommentReport.objects.get_or_create(
                comment=comment,
                reporter=user,
                defaults={"reason": reason}
            )
    except IntegrityError:
        raise ValidationError("Unable to save report.")

    if not created:
        raise ValidationError( "You have already reported this comment." )

    # ตรวจเนื้อหาคอมเมนต์ซ้ำ
    review_reported_comment(comment)

    return report
