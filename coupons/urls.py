from django.urls import path

from . import views

app_name = "coupons"

urlpatterns = [
    # Back office — staff-only, pk URLs per the URL conventions.
    path("backoffice/coupons/", views.CouponListView.as_view(), name="list"),
    path("backoffice/coupons/add/", views.CouponCreateView.as_view(), name="create"),
    path(
        "backoffice/coupons/<int:pk>/edit/",
        views.CouponUpdateView.as_view(),
        name="update",
    ),
    path(
        "backoffice/coupons/<int:pk>/delete/",
        views.CouponDeleteView.as_view(),
        name="delete",
    ),
    path(
        "backoffice/coupons/<int:pk>/expire/",
        views.ExpireCouponView.as_view(),
        name="expire",
    ),
]
