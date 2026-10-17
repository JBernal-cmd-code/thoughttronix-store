from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path(
        "reviews/create/<int:pk>/",
        views.CreateReviewView.as_view(),
        name="create",
    ),
    path("reviews/<int:pk>/edit/", views.EditReviewView.as_view(), name="edit"),
    path("reviews/<int:pk>/cancel/", views.CancelEditView.as_view(), name="cancel"),
    path(
        "reviews/<int:pk>/update/",
        views.UpdateReviewView.as_view(),
        name="update",
    ),
    path(
        "reviews/<int:pk>/delete/",
        views.DeleteReviewView.as_view(),
        name="delete",
    ),
]
