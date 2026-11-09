
from .integrations import BoardIntegrationAdapter

from .like_service import (
    toggle_like,
    get_post_interaction_data,
    get_liked_posts,
)

from .comment_service import (
    get_comments,
    create_comment,
)

from .report_service import (
    submit_post_report,
    submit_comment_report,
)

from .moderation.service import (
    moderate_post,
    moderate_comment,
)

from .models import Comment


class M8MatchBoardAdapter(BoardIntegrationAdapter):

    def get_post_interaction_data(self, posts, user):
        return get_post_interaction_data(posts, user)

    def toggle_like(self, post, user):
        return toggle_like(post, user)

    def get_liked_posts(self, user):
        return get_liked_posts(user)

    def get_comments(self, post, user):
        comments = get_comments(post, user)

        return [
            {
                "id": comment.id,
                "author_id": comment.author_id,
                "author_name": comment.author.username,
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
            }
            for comment in comments
        ]

    def create_comment(self, post, user, content):
        return create_comment(post, user, content)

    def submit_post_report(self, post_id, user, reason):
        return submit_post_report(post_id, user, reason)

    def submit_comment_report(self, comment, user, reason):
        return submit_comment_report(comment, user, reason)

    def moderate_post(self, title, content, user):
        return moderate_post(title, content, user)

    def moderate_comment(self, content, user):
        return moderate_comment(content, user)

    def get_public_profile_url(self, user):
        return None

    def get_comment_for_report(self, comment_id):
        return Comment.objects.filter(
            pk=comment_id,
            is_hidden=False,
            post__is_hidden=False
        ).first()
