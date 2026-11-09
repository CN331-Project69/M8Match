from django.urls import path

from . import views


app_name = "board"

urlpatterns = [
    path("", views.board_view, name="board"),
    path("my-posts/", views.my_posts_view, name="my_posts"),
    path("create/", views.create_post, name="create_post"),
    path("edit/<int:pk>/", views.edit_post, name="edit_post"),
    path("delete/<int:pk>/", views.delete_post, name="delete_post"),
    path("like/<int:pk>/", views.toggle_like, name="toggle_like"),
    path("post/<int:pk>/comments/", views.post_comments, name="post_comments"),
    path("post/<int:pk>/comment/create/", views.create_comment, name="create_comment"),
    path("post/<int:pk>/report/", views.report_post, name="report_post"),
    path("comment/<int:comment_id>/report/", views.report_comment, name="report_comment"),
]
