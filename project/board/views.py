from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured, ValidationError, PermissionDenied
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from categories.models import Category

from .forms import PostForm, PostEditForm
from .models import Post
from .services import (
    create_post as create_post_service,
    update_post as update_post_service,
    delete_post as delete_post_service,
)
from .integrations import get_board_adapter, default_chat_url, default_public_profile_url


# จำนวนตัวอักษรที่ Guest สามารถเห็นได้
GUEST_PREVIEW_LENGTH = 250

# จำนวนโพสต์ต่อหนึ่งหน้า
POSTS_PER_PAGE = 10


def _get_valid_count(value):
    """
    ตรวจสอบจำนวน Like หรือ Comment ที่ได้รับจาก Adapter

    ไม่รับค่าที่ผิดรูปแบบหรือค่าติดลบ
    เพื่อไม่ให้ข้อมูลผิดพลาดถูกนำไปแสดงบนหน้า Board
    """

    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
    ):
        return value

    return None


def get_post_cards(posts, user, adapter=None):
    """
    เตรียมข้อมูล Post Card สำหรับหน้า Board

    เชื่อมข้อมูล Like, Comment และ Public Profile
    ผ่าน Integration Adapter โดยไม่เรียก Model
    ของระบบเพื่อนโดยตรง
    """

    post_cards = []

    # แปลง QuerySet เป็น List เพื่อให้ใช้ข้อมูลชุดเดียวกัน
    posts = list(posts)

    # ดึงข้อมูล Like และ Comment แบบ Batch
    interaction_data = {}

    if adapter is not None and posts:
        interaction_data = (
            adapter.get_post_interaction_data(posts, user) or {}
        )

        if not isinstance(interaction_data, dict):
            raise ImproperlyConfigured(
                "get_post_interaction_data() must return a dictionary."
            )

    # เก็บ URL ของ Profile เพื่อไม่เรียกซ้ำ
    profile_urls = {}

    for post in posts:

        # --------------------------------------------
        # ข้อมูล Profile ของผู้เขียน
        # --------------------------------------------

        profile = getattr(post.author, "profile", None)

        author_name = (
            profile.display_name
            if profile and profile.display_name
            else post.author.username
        )

        profile_picture = None

        if profile and profile.profile_picture:
            profile_picture = profile.profile_picture.url

        # เตรียม URL สำหรับเชื่อมไป Public Profile และปุ่มแชท
        # (หน้าโปรไฟล์และแชทต้อง Login ก่อน Guest จึงเห็นแค่ชื่อ)
        profile_url = None
        chat_url = None

        if user.is_authenticated:
            author_id = post.author_id

            if author_id not in profile_urls:
                url = None
                if adapter is not None:
                    url = adapter.get_public_profile_url(post.author)
                # Adapter ยังไม่เชื่อม/ไม่มี URL -> ใช้หน้าโปรไฟล์มาตรฐานของเว็บ
                profile_urls[author_id] = url or default_public_profile_url(post.author)

            profile_url = profile_urls[author_id]

            # ไม่ต้องมีปุ่มแชทกับตัวเอง
            if author_id != user.id:
                chat_url = default_chat_url(post.author)

        # --------------------------------------------
        # ข้อมูล Like และ Comment
        # --------------------------------------------

        post_interactions = interaction_data.get(post.id, {})

        if not isinstance(post_interactions, dict):
            post_interactions = {}

        like_count = _get_valid_count(
            post_interactions.get("like_count")
        )

        comment_count = _get_valid_count(
            post_interactions.get("comment_count")
        )

        # Guest ไม่มีสถานะ Like ส่วนตัว
        is_liked = False

        if user.is_authenticated:
            is_liked = bool(
                post_interactions.get("is_liked", False)
            )

        # --------------------------------------------
        # สร้างข้อมูล Post Card
        # --------------------------------------------

        card = {
            "id": post.id,
            "title": post.title,

            "author_name": author_name,
            "author_picture": profile_picture,
            "author_profile_url": profile_url,
            "author_chat_url": chat_url,

            "created_at": post.created_at,
            "updated_at": post.updated_at,
            "is_edited": post.is_edited,

            "is_owner": (
                user.is_authenticated
                and post.author_id == user.id
            ),

            "images": [
                image.image.url
                for image in post.images.all()
                if image.image
            ],

            "categories": [
                {
                    "id": category.id,
                    "name": category.name,
                }
                for category in post.categories.all()
            ],

            # ข้อมูล Like
            "like_count": like_count,
            "is_liked": is_liked,

            # ข้อมูล Comment เฉพาะจำนวน
            "comment_count": comment_count,
        }

        # จำกัดเนื้อหาที่ Guest สามารถเห็นได้
        if user.is_authenticated:
            card["content"] = post.content
            card["is_truncated"] = False

        else:
            card["content"] = post.content[:GUEST_PREVIEW_LENGTH]
            card["is_truncated"] = (
                len(post.content) > GUEST_PREVIEW_LENGTH
            )

        post_cards.append(card)

    return post_cards


def _normalize_moderation_messages(data):
    """
    จัดรูปแบบข้อความจาก Moderation ให้เป็น List
    เพื่อให้ View และ Template นำไปใช้งานได้สม่ำเสมอ
    """

    normalized = {}

    for field_name, value in data.items():

        if isinstance(value, str):
            normalized[field_name] = [value]

        elif isinstance(value, (list, tuple)):
            normalized[field_name] = [
                str(message)
                for message in value
            ]

        else:
            raise ImproperlyConfigured(
                "Moderation messages must be strings or lists."
            )

    return normalized


def _apply_post_moderation(form, adapter, user):
    """
    ส่งข้อมูล Post ไปตรวจสอบผ่าน Moderation Adapter

    หากยังไม่มี Adapter จะคงพฤติกรรมเดิมของ Board
    ไว้ระหว่างการพัฒนาและรอการเชื่อมต่อระบบจริง
    """

    if adapter is None:

        # อนุญาตให้ข้าม Moderation เฉพาะตอนพัฒนาในเครื่อง
        if settings.DEBUG:
            return True, {}

        # Production ต้องปฏิเสธหากยังไม่มีระบบตรวจสอบ
        form.add_error(
            None,
            "ไม่สามารถบันทึกโพสต์ได้ในขณะนี้ "
            "เนื่องจากระบบตรวจสอบเนื้อหายังไม่พร้อมใช้งาน"
        )

        return False, {}

    result = adapter.moderate_post(
        title=form.cleaned_data["title"],
        content=form.cleaned_data["content"],
        user=user,
    )

    if not isinstance(result, dict):
        raise ImproperlyConfigured(
            "moderate_post() must return a dictionary."
        )

    if not isinstance(result.get("is_allowed"), bool):
        raise ImproperlyConfigured(
            "moderate_post() must return a boolean is_allowed value."
        )

    errors = result.get("errors") or {}
    warnings = result.get("warnings") or {}

    if not isinstance(errors, dict) or not isinstance(warnings, dict):
        raise ImproperlyConfigured(
            "Moderation errors and warnings must be dictionaries."
        )

    errors = _normalize_moderation_messages(errors)
    warnings = _normalize_moderation_messages(warnings)

    # แสดงข้อผิดพลาดใต้ Field ที่เกี่ยวข้อง
    for field_name, field_messages in errors.items():

        # หากระบุ Field ที่ไม่มีอยู่ ให้แสดงเป็น Non-field error
        if field_name not in form.fields:
            field_name = None

        if isinstance(field_messages, str):
            field_messages = [field_messages]

        for message in field_messages:
            form.add_error(field_name, str(message))

    # หากไม่ผ่านแต่ระบบไม่ได้ส่งเหตุผลกลับมา
    if not result["is_allowed"] and not errors:
        form.add_error(
            None,
            "ไม่สามารถบันทึกโพสต์นี้ได้ เนื่องจากไม่ผ่านการตรวจสอบ"
        )

    return result["is_allowed"], warnings


def board_view(request):
    """
    หน้า Board หลัก พร้อมระบบค้นหา
    กรอง Category และแบ่งหน้า
    """

    posts = (
        Post.objects
        .filter(is_hidden=False)
        .select_related("author", "author__profile")
        .prefetch_related("images", "categories")
        .order_by("-created_at")
    )

    # รับคำค้นหาจากช่อง Search
    search_query = request.GET.get("q", "").strip()

    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query)
            | Q(content__icontains=search_query)
        )

    # ดึงเฉพาะ Category ที่เปิดใช้งาน
    categories = list(
        Category.objects
        .filter(is_active=True)
        .order_by("name")
    )

    # ตรวจสอบ ID ของ Category ที่มีอยู่จริง
    valid_category_ids = {
        str(category.id)
        for category in categories
    }

    # รองรับการเลือกหลาย Category
    requested_categories = request.GET.getlist("category")

    selected_categories = [
        int(category_id)
        for category_id in requested_categories
        if category_id.isdigit()
        and category_id in valid_category_ids
    ]

    # กรองโพสต์ตาม Category ที่เลือก
    if selected_categories:
        posts = posts.filter(
            categories__id__in=selected_categories
        ).distinct()

    # แบ่งหน้า หน้าละ 10 โพสต์
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    # โหลด Adapter สำหรับเชื่อมระบบอื่น
    adapter = get_board_adapter()

    post_cards = get_post_cards(
        page_obj.object_list,
        request.user,
        adapter,
    )

    return render(request, "board/board.html", {
        "posts": post_cards,
        "page_obj": page_obj,
        "categories": categories,
        "search_query": search_query,
        "selected_categories": selected_categories,
    })


@login_required
def my_posts_view(request):
    """แสดงโพสต์ของตัวเองและโพสต์ที่กด Like"""

    # กำหนดค่าเริ่มต้นไว้ก่อน เผื่อยังไม่มีระบบ Like จาก Adapter
    liked_posts_queryset = []

    adapter = get_board_adapter()

    # ดึงโพสต์ที่ผู้ใช้สร้างเอง
    my_posts_queryset = (
        Post.objects
        .filter(author=request.user)
        .select_related("author")
        .prefetch_related("images", "categories")
        .order_by("-created_at")
    )

    my_posts = get_post_cards(
        my_posts_queryset,
        request.user,
        adapter
    )

    # เตรียมรายการ My Likes
    liked_posts = []

    # ดึงข้อมูลจริงผ่าน Adapter เมื่อระบบ Like เชื่อมต่อแล้ว
    if adapter is not None:
        liked_posts_queryset = adapter.get_liked_posts(request.user)

    # ตรวจสอบว่า Adapter ส่งข้อมูลกลับมาเป็นรายการ Post
    if (
        isinstance(liked_posts_queryset, (str, bytes, dict))
        or not hasattr(liked_posts_queryset, "__iter__")
    ):
        raise ImproperlyConfigured(
            "get_liked_posts() must return an iterable of Posts."
        )

    # กรองโพสต์ที่ถูกซ่อนออกอีกชั้น
    if hasattr(liked_posts_queryset, "filter"):
        liked_posts_queryset = liked_posts_queryset.filter(is_hidden=False)

        if liked_posts_queryset is None:
            raise ImproperlyConfigured(
                "Liked posts queryset cannot be None."
            )

        if hasattr(liked_posts_queryset, "select_related"):
            liked_posts_queryset = (
                liked_posts_queryset
                .select_related("author")
                .prefetch_related("images", "categories")
            )

    liked_posts = get_post_cards(
        liked_posts_queryset,
        request.user,
        adapter,
    )

    return render(
        request,
        "board/my_posts.html",
        {
            "posts": my_posts,
            "liked_posts": liked_posts,
        }
    )


@login_required
def create_post(request):
    """สร้าง Post ใหม่"""

    moderation_warnings = {}

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)

        if form.is_valid():

            # โหลด Adapter สำหรับตรวจสอบ Moderation
            adapter = get_board_adapter()

            allowed, moderation_warnings = (
                _apply_post_moderation(
                    form,
                    adapter,
                    request.user,
                )
            )

            # บันทึกเฉพาะเมื่อผ่าน Moderation
            if allowed:
                create_post_service(
                    author=request.user,
                    title=form.cleaned_data["title"],
                    content=form.cleaned_data["content"],
                    categories=form.cleaned_data["categories"],
                    images=form.cleaned_data["images"],
                )

                return redirect("board:board")

    else:
        form = PostForm()

    return render(request, "board/post_form.html", {
        "form": form,
        "action": "create",
        "moderation_warnings": moderation_warnings,
    })


@login_required
def edit_post(request, pk):
    """แก้ไข Post ของตัวเองเท่านั้น"""

    post = get_object_or_404(
        Post,
        pk=pk,
        author=request.user,
    )

    moderation_warnings = {}

    if request.method == "POST":
        form = PostEditForm(
            request.POST,
            request.FILES,
            instance=post,
        )

        if form.is_valid():

            # โหลด Adapter สำหรับตรวจสอบ Moderation
            adapter = get_board_adapter()

            allowed, moderation_warnings = (
                _apply_post_moderation(
                    form,
                    adapter,
                    request.user,
                )
            )

            # บันทึกการแก้ไขเฉพาะเมื่อผ่าน Moderation
            if allowed:
                update_post_service(
                    post=post,
                    title=form.cleaned_data["title"],
                    content=form.cleaned_data["content"],
                    categories=form.cleaned_data["categories"],
                    new_images=form.cleaned_data["images"],
                    delete_images=form.cleaned_data["delete_images"],
                )

                return redirect("board:board")

    else:
        form = PostEditForm(instance=post)

    return render(request, "board/post_form.html", {
        "form": form,
        "post": post,
        "action": "edit",
        "moderation_warnings": moderation_warnings,
    })


@login_required
def delete_post(request, pk):
    """ลบ Post ของตัวเองเท่านั้น"""

    post = get_object_or_404(
        Post,
        pk=pk,
        author=request.user,
    )

    if request.method == "POST":
        delete_post_service(post=post)
        return redirect("board:board")

    return render(request, "board/confirm_delete.html", {
        "post": post,
    })


@login_required
@require_POST
def toggle_like(request, pk):
    """
    กด Like หรือ Unlike โพสต์

    ใช้ Adapter เชื่อมกับระบบ Like ของสมาชิกคนอื่น
    ไม่สร้างข้อมูล Like ใน Board เอง
    """

    # ตรวจสอบว่าโพสต์มีอยู่จริงและไม่ถูกซ่อน
    post = get_object_or_404(
        Post.objects.filter(is_hidden=False),
        pk=pk
    )

    # โหลดระบบ Like ผ่าน Adapter
    adapter = get_board_adapter()

    # ยังไม่สามารถกด Like ได้หากระบบเพื่อนยังไม่เชื่อมต่อ
    if adapter is None:
        return HttpResponse(
            "Like system is not connected yet.",
            status=503
        )

    # เรียก Adapter เพื่อสลับสถานะ Like / Unlike
    result = adapter.toggle_like(post, request.user)

    # ตรวจสอบรูปแบบข้อมูลที่ Adapter ส่งกลับ
    if not isinstance(result, dict):
        raise ImproperlyConfigured(
            "toggle_like() must return a dictionary."
        )

    if not isinstance(result.get("liked"), bool):
        raise ImproperlyConfigured(
            "toggle_like() must return a boolean 'liked' value."
        )

    if _get_valid_count(result.get("like_count")) is None:
        raise ImproperlyConfigured(
            "toggle_like() must return a valid 'like_count'."
        )

    # กด Like ผ่าน JavaScript (fetch) -> ตอบเป็น JSON ไม่ต้องโหลดหน้าใหม่
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse({
            "liked": result["liked"],
            "like_count": _get_valid_count(result["like_count"]),
        })

    # กลับไปยังหน้าที่ผู้ใช้กด Like โดยป้องกันการ Redirect ออกเว็บอื่น
    next_url = request.POST.get("next", "")

    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        next_url = None

    return redirect(next_url or "board:board")


@login_required
@require_GET
def post_comments(request, pk):
    """ดึงความคิดเห็นของโพสต์สำหรับผู้ใช้ที่เข้าสู่ระบบแล้ว"""

    post = get_object_or_404(
        Post.objects.filter(is_hidden=False),
        pk=pk
    )

    adapter = get_board_adapter()

    if adapter is None:
        return JsonResponse(
            {"error": "Comment system is not connected yet."},
            status=503
        )

    comments = adapter.get_comments(post, request.user)

    # กำหนดให้ Adapter คืนค่าเป็นรายการ Dictionary
    if not isinstance(comments, (list, tuple)):
        raise ImproperlyConfigured(
            "get_comments() must return a list of dictionaries."
        )

    required_fields = {
        "id", "author_name", "content", "created_at"
    }

    for comment in comments:
        if not isinstance(comment, dict):
            raise ImproperlyConfigured(
                "Each comment must be a dictionary."
            )

        if not required_fields.issubset(comment.keys()):
            raise ImproperlyConfigured(
                "Comment data is missing required fields."
            )

    return JsonResponse({"comments": comments}, encoder=DjangoJSONEncoder)


@login_required
@require_POST
def create_comment(request, pk):
    """ตรวจสอบและส่งความคิดเห็นผ่านระบบ Moderation"""

    post = get_object_or_404(
        Post.objects.filter(is_hidden=False),
        pk=pk
    )

    content = request.POST.get("content", "").strip()

    if not content:
        return JsonResponse(
            {"error": "Please enter your comment."},
            status=400
        )

    if len(content) > 2000:
        return JsonResponse(
            {"error": "Maximum 2,000 characters."},
            status=400
        )

    adapter = get_board_adapter()

    if adapter is None:
        return JsonResponse(
            {"error": "Comment system is not connected yet."},
            status=503
        )

    result = adapter.moderate_comment(content, request.user)

    if not isinstance(result, dict):
        raise ImproperlyConfigured(
            "moderate_comment() must return a dictionary."
        )

    if not isinstance(result.get("is_allowed"), bool):
        raise ImproperlyConfigured(
            "Moderation result must contain boolean is_allowed."
        )

    errors = result.get("errors", {})
    warnings = result.get("warnings", {})

    if not isinstance(errors, dict) or not isinstance(warnings, dict):
        raise ImproperlyConfigured(
            "Moderation errors and warnings must be dictionaries."
        )

    for collection in (errors, warnings):
        for item in collection.values():
            if not isinstance(item, (str, list, tuple)):
                raise ImproperlyConfigured(
                    "Moderation messages must be strings or lists."
                )

    if not result["is_allowed"]:
        error_messages = []

        for field_errors in errors.values():
            if isinstance(field_errors, str):
                error_messages.append(field_errors)
            else:
                error_messages.extend(str(e) for e in field_errors)

        return JsonResponse(
            {
                "error": "; ".join(error_messages)
                or "This comment was hidden due to a policy violation."
            },
            status=400
        )

    try:
        comment = adapter.create_comment(
            post,
            request.user,
            content
        )
    except ValidationError as e:
        return JsonResponse(
            {"error": "; ".join(e.messages)},
            status=400
        )
    except PermissionDenied:
        return JsonResponse(
            {"error": "You don't have permission to comment."},
            status=403
        )

    warning_messages = []

    for warning_list in warnings.values():
        if isinstance(warning_list, str):
            warning_messages.append(warning_list)
        else:
            warning_messages.extend(str(w) for w in warning_list)

    return JsonResponse({
        "success": True,
        "comment_id": comment.id,
        "message": "Comment submitted!",
        "warnings": warning_messages
    })


@login_required
@require_POST
def report_post(request, pk):
    """ส่งรายงานโพสต์ผ่านระบบ Report ของทีม"""

    post = get_object_or_404(
        Post.objects.filter(is_hidden=False),
        pk=pk
    )

    reason = request.POST.get("reason", "").strip()

    if not reason or len(reason) > 1000:
        messages.error(
            request,
            "Please provide a reason for reporting (Max 1,000 characters)."
        )
        return redirect("board:board")

    adapter = get_board_adapter()

    if adapter is None:
        return HttpResponse(
            "Report system is not connected yet.",
            status=503
        )

    # ส่งข้อมูลให้ระบบ Report ของทีมตรวจสอบ

    try:
        adapter.submit_post_report(
            post.id,
            request.user,
            reason
        )

    except ValidationError as e:
        return JsonResponse(
            {"error": "; ".join(e.messages)},
            status=400
        )

    except PermissionDenied:
        return JsonResponse(
            {"error": "You don't have permission to comment."},
            status=403
        )

    return JsonResponse({
        "success": True,
        "message": "Report submitted!"
    })


@login_required
@require_POST
def report_comment(request, comment_id):
    """ส่งรายงานความคิดเห็นผ่านระบบ Report ของทีม"""

    reason = request.POST.get("reason", "").strip()

    if not reason or len(reason) > 1000:
        return JsonResponse(
            {"error": "Please provide a reason for reporting (Max 1,000 characters)."},
            status=400
        )

    adapter = get_board_adapter()

    if adapter is None:
        return JsonResponse(
            {"error": "Report system is not connected yet."},
            status=503
        )

    comment = adapter.get_comment_for_report(comment_id)

    if comment is None:
        return JsonResponse(
            {"error": "Comment not found."},
            status=404
        )

    try:
        adapter.submit_comment_report(
            comment,
            request.user,
            reason
        )

    except ValidationError as e:
        return JsonResponse(
            {"error": "; ".join(e.messages)},
            status=400
        )

    except PermissionDenied:
        return JsonResponse(
            {"error": "You don't have permission to comment."},
            status=403
        )

    return JsonResponse({
        "success": True,
        "message": "Report submitted!"
    })
