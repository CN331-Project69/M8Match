
import re


MAX_POST_TITLE_LENGTH = 200
MAX_POST_CONTENT_LENGTH = 10000
MAX_COMMENT_LENGTH = 2000


def create_result(is_allowed=True, errors=None, warnings=None):
    return {
        "is_allowed": is_allowed,
        "errors": errors or {},
        "warnings": warnings or {}
    }


def check_empty(value):
    return not isinstance(value, str) or not value.strip()


def check_length(value, max_length):
    return isinstance(value, str) and len(value) > max_length


def check_spam(value):
    if not isinstance(value, str):
        return False

    # ตัวอักษรเดียวกันซ้ำติดกัน 9 ตัวขึ้นไป
    return bool(re.search(r"(.)\1{9,}", value))


def check_suspicious_links(value):
    if not isinstance(value, str):
        return False

    # ตรวจ URL ที่มีรูปแบบ IP Address
    return bool(
        re.search(
            r"https?://\d{1,3}(?:\.\d{1,3}){3}",
            value,
            flags=re.IGNORECASE
        )
    )


def moderate_comment(content, user=None):
    errors = {}
    warnings = {}

    if check_empty(content):
        errors["content"] = "Please enter a comment."

    elif check_length(content, MAX_COMMENT_LENGTH):
        errors["content"] = "Comment exceeds limit."

    elif check_spam(content):
        errors["content"] = "Potential spam detected."

    if check_suspicious_links(content):
        warnings["content"] = (
            "Suspicious link detected."
        )

    return create_result(
        is_allowed=not bool(errors),
        errors=errors,
        warnings=warnings
    )


def moderate_post(title, content, user=None):
    errors = {}
    warnings = {}

    # ตรวจ Title
    if check_empty(title):
        errors["title"] = "Title cannot be empty."

    elif check_length(title, MAX_POST_TITLE_LENGTH):
        errors["title"] = "Title exceeds limit."

    elif check_spam(title):
        errors["title"] = "Potential spam detected."

    # ตรวจ Content
    if check_empty(content):
        errors["content"] = "Please enter post content."

    elif check_length(content, MAX_POST_CONTENT_LENGTH):
        errors["content"] = "Content exceeds limit."

    elif check_spam(content):
        errors["content"] = "Potential spam detected."

    if (
        check_suspicious_links(title)
        or check_suspicious_links(content)
    ):
        warnings["content"] = (
            "Suspicious link detected."
        )

    return create_result(
        is_allowed=not bool(errors),
        errors=errors,
        warnings=warnings
    )


def review_reported_post(post):
    # ตรวจเนื้อหาปัจจุบันของ Post
    result = moderate_post(
        title=post.title,
        content=post.content,
        user=post.author
    )

    # ซ่อนเฉพาะเมื่อไม่ผ่าน Moderation
    if not result["is_allowed"]:
        post.is_hidden = True
        post.save(update_fields=["is_hidden"])

    return result


def review_reported_comment(comment):
    # ตรวจเนื้อหาปัจจุบันของ Comment
    result = moderate_comment(
        content=comment.content,
        user=comment.author
    )

    # ซ่อนเฉพาะเมื่อไม่ผ่าน Moderation
    if not result["is_allowed"]:
        comment.is_hidden = True
        comment.save(update_fields=["is_hidden"])

    return result
