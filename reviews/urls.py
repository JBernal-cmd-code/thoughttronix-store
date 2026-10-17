from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path(
        "reviews/create/<int:pk>/",
        views.CreateReviewView.as_view(),
        name="create",
    ),
]
