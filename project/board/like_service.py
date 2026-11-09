
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count

from .models import PostLike, Comment

'''
การกด Like มีทั้งการเพิ่มหรือลบข้อมูล และการนับจำนวน
@transaction.atomic
ช่วยให้การเปลี่ยนแปลงฐานข้อมูลในฟังก์ชันอยู่ภายใต้ Transaction เดียวกัน
หากเกิดข้อผิดพลาด การเปลี่ยนแปลงที่ยังไม่ Commit จะถูกย้อนกลับ
'''
@transaction.atomic
def toggle_like(post, user):
    # ตรวจสอบว่าผู้ใช้ Login แล้วหรือยัง
    if not user.is_authenticated:
        raise PermissionDenied(
            "Please log in to like this post."
        )

    # ค้นหาว่าเคย Like โพสต์นี้หรือยัง
    existing_like = PostLike.objects.filter(
        post=post,
        user=user
    ).first()

    # ถ้าเคย Like แล้ว ให้ยกเลิก Like
    if existing_like:
        existing_like.delete()
        liked = False

    # ถ้ายังไม่เคย Like ให้สร้าง Like ใหม่
    else:
        PostLike.objects.create(
            post=post,
            user=user
        )
        liked = True

    # นับจำนวน Like ล่าสุดจากฐานข้อมูล
    like_count = PostLike.objects.filter(
        post=post
    ).count()

    return {
        "liked": liked,
        "like_count": like_count
    }


def get_post_interaction_data(posts, user):
    posts = list(posts)

    if not posts:
        return {}

    post_ids = [post.id for post in posts]

    # นับจำนวน Like ของทุกโพสต์
    like_counts = dict(
        PostLike.objects
        .filter(post_id__in=post_ids)
        .values("post_id")
        .annotate(total=Count("id"))
        .values_list("post_id", "total")
    )

    # นับจำนวน Comment ที่ไม่ได้ถูกซ่อน
    comment_counts = dict(
        Comment.objects
        .filter(
            post_id__in=post_ids,
            is_hidden=False
        )
        .values("post_id")
        .annotate(total=Count("id"))
        .values_list("post_id", "total")
    )

    # ตรวจว่า User กด Like โพสต์ไหนแล้วบ้าง
    liked_post_ids = set()

    if user.is_authenticated:
        liked_post_ids = set(
            PostLike.objects
            .filter(
                post_id__in=post_ids,
                user=user
            )
            .values_list("post_id", flat=True)
        )

    result = {}

    for post in posts:
        result[post.id] = {
            "like_count": like_counts.get(post.id, 0),
            "comment_count": comment_counts.get(post.id, 0),
            "is_liked": post.id in liked_post_ids
        }

    return result


def get_liked_posts(user):
    # ตรวจสอบว่าผู้ใช้ Login แล้วหรือยัง
    if not user.is_authenticated:
        raise PermissionDenied(
            "Please log in to view My Likes"
        )

    # ค้นหา Like ของผู้ใช้
    liked_posts = (
        PostLike.objects
        .filter(
            user=user,
            post__is_hidden=False
        )
        .select_related(
            "post",
            "post__author"
        )
        .prefetch_related(
            "post__categories",
            "post__images"
        )
        .order_by("-created_at", "-pk")
    )

    # คืนรายการ Post ตามลำดับ Like
    return [like.post for like in liked_posts]
