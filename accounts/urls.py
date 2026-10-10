from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", views.SignOutView.as_view(), name="logout"),
    # Forgot password. Completion lands on the sign-in page, not its own.
    path(
        "password-reset/",
        views.PasswordResetRequestView.as_view(),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        views.PasswordResetRequestDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.PasswordResetSetView.as_view(),
        name="password_reset_confirm",
    ),
    # Security Center — always the signed-in user, so no ids in the URL.
    path("security/", views.SecurityCenterView.as_view(), name="security"),
    path(
        "security/password/",
        views.ChangePasswordView.as_view(),
        name="password_change",
    ),
    path("security/email/", views.ChangeEmailView.as_view(), name="email_change"),
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
