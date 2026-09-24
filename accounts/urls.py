from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", views.SignOutView.as_view(), name="logout"),
    # The address book — pks, since these are the customer's own records
    # and have no public-facing slug.
    path("addresses/", views.AddressListView.as_view(), name="addresses"),
    path(
        "addresses/new/",
        views.AddressCreateView.as_view(),
        name="address_create",
    ),
    path(
        "addresses/<int:pk>/edit/",
        views.AddressUpdateView.as_view(),
        name="address_update",
    ),
    path(
        "addresses/<int:pk>/delete/",
        views.AddressDeleteView.as_view(),
        name="address_delete",
    ),
]
