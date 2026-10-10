from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse


def signup_data(**overrides):
    """A valid signup POST, with any field overridden."""
    return {
        "username": "fresh-thinker",
        "email": "fresh@example.com",
        "password1": "neural-implant-9000",
        "password2": "neural-implant-9000",
        **overrides,
    }


# --- Signup -----------------------------------------------------------------


def test_signup_page_returns_200(client, db):
    response = client.get(reverse("accounts:signup"))

    assert response.status_code == HTTPStatus.OK


def test_signup_page_asks_for_email(client, db):
    response = client.get(reverse("accounts:signup"))

    assert "email" in response.context["form"].fields
    assert 'name="email"' in response.content.decode()


def test_signup_creates_plain_customer(client, db):
    response = client.post(reverse("accounts:signup"), signup_data(), follow=True)

    user = get_user_model().objects.get(username="fresh-thinker")
    assert user.email == "fresh@example.com"
    assert not user.is_staff
    assert not user.is_superuser

    # Signup hands off to the login page with a confirmation message;
    # auto-login is a student exercise, so the visitor is still anonymous.
    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    assert "Account created" in response.content.decode()
    assert not response.context["user"].is_authenticated


def test_signup_password_mismatch_shows_field_error(client, db):
    response = client.post(
        reverse("accounts:signup"), signup_data(password2="neural-implant-9001")
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["password2"]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def test_signup_without_email_is_refused(client, db):
    response = client.post(reverse("accounts:signup"), signup_data(email=""))

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["email"]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def test_signup_saves_email_lowercase(client, db):
    client.post(reverse("accounts:signup"), signup_data(email="Casey@Example.com"))

    user = get_user_model().objects.get(username="fresh-thinker")
    assert user.email == "casey@example.com"


@pytest.mark.parametrize(
    "typed", ["customer@example.com", "Customer@Example.com", "CUSTOMER@EXAMPLE.COM"]
)
def test_signup_refuses_registered_email_in_any_case(client, customer, typed):
    response = client.post(reverse("accounts:signup"), signup_data(email=typed))

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["email"] == [
        "That email address is already in use."
    ]
    assert "already in use" in response.content.decode()
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def test_database_refuses_duplicate_email(customer):
    # The constraint itself, below any form: a second account can't share
    # an email even if code skips validation.
    with pytest.raises(IntegrityError):
        get_user_model().objects.create_user(
            username="impostor", email="customer@example.com", password="x"
        )


def test_admin_add_user_form_asks_for_email(client, db):
    admin = get_user_model().objects.create_superuser(
        "root", email="root@example.com", password="root123"
    )
    client.force_login(admin)

    response = client.get(reverse("admin:accounts_user_add"))

    assert 'name="email"' in response.content.decode()


# --- Login and logout --------------------------------------------------------


def test_login_page_returns_200(client, db):
    response = client.get(reverse("accounts:login"))

    assert response.status_code == HTTPStatus.OK


def test_login_round_trip(client, customer):
    response = client.post(
        reverse("accounts:login"),
        {"username": "customer", "password": "customer123"},
        follow=True,
    )

    assert response.redirect_chain[-1][0] == reverse("products:catalog")
    assert response.context["user"] == customer


def test_login_bad_credentials_stays_put(client, customer):
    response = client.post(
        reverse("accounts:login"),
        {"username": "customer", "password": "wrong"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].non_field_errors()


def test_logout_signs_out_with_message(client, customer):
    client.force_login(customer)

    response = client.post(reverse("accounts:logout"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("products:catalog")
    assert "You have signed out." in response.content.decode()
    assert not response.context["user"].is_authenticated


# --- Auth-aware navbar --------------------------------------------------------


def test_navbar_offers_login_and_signup_to_visitors(client, db):
    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:login") in page
    assert reverse("accounts:signup") in page
    assert "Sign out" not in page


def test_navbar_greets_signed_in_customer(client, customer):
    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()

    assert "Hi, customer" in page
    assert "Sign out" in page
    assert reverse("accounts:signup") not in page
