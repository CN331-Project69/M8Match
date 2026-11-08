from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Post, PostImage
from .moderation.service import moderate_post


def _delete_storage_file(storage, name):
    """
    ลบไฟล์จริงจาก Storage

    แยกเป็นฟังก์ชันเพื่อให้เรียกหลัง Database Commit
    และจัดการไฟล์ได้จากจุดเดียว
    """

    if storage and name:
        storage.delete(name)


def _schedule_image_deletion(image):
    """
    กำหนดให้ลบไฟล์รูปหลัง Transaction สำเร็จ
    """

    if image and image.name:
        storage = image.storage
        image_name = image.name

        transaction.on_commit(
            lambda storage=storage, name=image_name:
            _delete_storage_file(storage, name)
        )


def _save_new_images(post, images):
    """
    บันทึกรูปภาพใหม่ให้ Post

    เก็บชื่อไฟล์ไว้เพื่อใช้ล้างไฟล์ที่อัปโหลดแล้ว
    หาก Database Transaction เกิดข้อผิดพลาด
    """

    saved_images = []

    try:
        for image in images:
            post_image = PostImage.objects.create(
                post=post,
                image=image,
            )

            saved_images.append(post_image)

    except Exception:
        # ล้างไฟล์ที่อัปโหลดไปแล้วเมื่อเกิดข้อผิดพลาด
        for post_image in saved_images:
            if post_image.image:
                _delete_storage_file(
                    post_image.image.storage,
                    post_image.image.name,
                )

        raise

    return saved_images


# สร้าง Post ใหม่ พร้อมบันทึก Category และรูปภาพ
@transaction.atomic
def create_post(
    *,
    author,
    title,
    content,
    categories=None,
    images=None,
):

    # ตรวจสอบเนื้อหาก่อนสร้าง Post
    result = moderate_post(
        title=title,
        content=content,
        user=author
    )

    if not result["is_allowed"]:
        raise ValidationError(result["errors"])

    images = list(images or [])

    # สร้าง Post
    post = Post.objects.create(
        author=author,
        title=title,
        content=content,
    )

    # เชื่อม Category ที่เลือกกับ Post
    if categories is not None:
        post.categories.set(categories)

    # บันทึกรูปภาพทั้งหมด
    _save_new_images(post, images)

    return post


# แก้ไข Post พร้อมจัดการ Category และรูปภาพ
@transaction.atomic
def update_post(
    *,
    post,
    title,
    content,
    categories=None,
    new_images=None,
    delete_images=None,
):

    new_images = list(new_images or [])
    delete_images = list(delete_images or [])

    # เก็บ Object เดิมไว้ เพื่อให้ผู้เรียกใช้งานเห็นค่าที่เปลี่ยน
    original_post = post

    # ล็อกแถว Post ระหว่างแก้ไข
    locked_post = (
        Post.objects
        .select_for_update()
        .get(pk=original_post.pk)
    )

    # ดึงข้อมูลล่าสุดกลับมาใส่ Object เดิม
    original_post.refresh_from_db()

    post = original_post


    # ตรวจสอบเนื้อหาใหม่ก่อนแก้ไข Post
    result = moderate_post(
        title=title,
        content=content,
        user=post.author
    )

    if not result["is_allowed"]:
        raise ValidationError(result["errors"])


    # ตรวจสอบ Category เดิม
    old_category_ids = set(
        post.categories.values_list("id", flat=True)
    )

    new_categories = (
        list(categories)
        if categories is not None
        else list(post.categories.all())
    )

    new_category_ids = {
        category.id for category in new_categories
    }

    # ตรวจสอบว่าข้อมูลหลักเปลี่ยนไปหรือไม่
    post_changed = (
        post.title != title
        or post.content != content
        or old_category_ids != new_category_ids
    )

    # ตรวจสอบว่ารูปที่เลือกจะลบเป็นของ Post นี้จริง
    requested_image_ids = {
        image.pk
        for image in delete_images
        if getattr(image, "pk", None) is not None
    }

    images_to_delete = list(
        post.images.filter(pk__in=requested_image_ids)
    )

    actual_image_ids = {
        image.pk for image in images_to_delete
    }

    if actual_image_ids != requested_image_ids:
        raise ValidationError(
            "One or more selected images do not belong to this post."
        )

    # ตรวจสอบว่ามีการเปลี่ยนรูปภาพหรือไม่
    images_changed = bool(
        new_images or images_to_delete
    )

    # บันทึกเมื่อมีการเปลี่ยนแปลงจริง
    if post_changed or images_changed:

        post.title = title
        post.content = content
        post.is_edited = True

        post.save(
            update_fields=[
                "title",
                "content",
                "is_edited",
                "updated_at",
            ]
        )

        # อัปเดต Category
        if categories is not None:
            post.categories.set(new_categories)

        # ลบรูปเดิมหลัง Database Commit
        for post_image in images_to_delete:
            _schedule_image_deletion(post_image.image)
            post_image.delete()

        # เพิ่มรูปใหม่
        _save_new_images(post, new_images)

    return post


# ลบ Post และไฟล์รูปภาพที่เกี่ยวข้อง
@transaction.atomic
def delete_post(*, post):

    # ดึง Post ล่าสุดและล็อกแถวระหว่างลบ
    post = (
        Post.objects
        .select_for_update()
        .get(pk=post.pk)
    )

    # เก็บข้อมูลไฟล์ก่อนลบ Post
    image_files = [
        (image.image.storage, image.image.name)
        for image in post.images.all()
        if image.image
    ]

    # ลบ Post และข้อมูลรูปที่เชื่อมอยู่
    post.delete()

    # ลบไฟล์จริงเมื่อ Database Transaction สำเร็จ
    for storage, image_name in image_files:

        transaction.on_commit(
            lambda storage=storage, name=image_name:
            _delete_storage_file(storage, name)
        )