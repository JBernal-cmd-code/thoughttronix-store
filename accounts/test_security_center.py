"""The Security Center: the hub, the nav link, and changing a password or
email."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

NEW_PASSWORD = "fresh-synapse-4242"

NEW_EMAIL = "casey.new@example.com"

SECURITY_PAGES = [
    "accounts:security",
    "accounts:password_change",
    "accounts:email_change",
]


def change_email(client, email=NEW_EMAIL, again=None, password="customer123"):
    return client.post(
        reverse("accounts:email_change"),
        {
            "new_email1": email,
            "new_email2": email if again is None else again,
            "password": password,
        },
        follow=True,
    )


def change_password(client, old="customer123", new=NEW_PASSWORD, again=None):
    return client.post(
        reverse("accounts:password_change"),
        {
            "old_password": old,
            "new_password1": new,
            "new_password2": new if again is None else again,
        },
        follow=True,
    )


# --- Access -------------------------------------------------------------------


@pytest.mark.parametrize("name", SECURITY_PAGES)
def test_anonymous_visitors_go_to_login(client, db, name):
    response = client.get(reverse(name))

    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("accounts:login"))


@pytest.mark.parametrize("name", SECURITY_PAGES)
@pytest.mark.parametrize("who", ["customer", "staff_user"])
def test_customers_and_staff_get_in(client, request, name, who):
    client.force_login(request.getfixturevalue(who))

    assert client.get(reverse(name)).status_code == HTTPStatus.OK


# --- Nav and hub --------------------------------------------------------------


def test_nav_shows_security_to_signed_in_users(client, customer):
    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()

    assert f'href="{reverse("accounts:security")}"' in page


def test_nav_hides_security_from_anonymous_visitors(client, db):
    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:security") not in page


def test_hub_shows_username_email_and_change_links(client, staff_user):
    client.force_login(staff_user)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "employee" in page
    assert "employee@example.com" in page
    assert reverse("accounts:password_change") in page
    assert reverse("accounts:email_change") in page


# --- Change password ----------------------------------------------------------


def test_wrong_current_password_is_refused(client, customer, mailoutbox):
    client.force_login(customer)

    response = change_password(client, old="not-my-password")

    assert response.context["form"].errors["old_password"]
    assert mailoutbox == []
    customer.refresh_from_db()
    assert customer.check_password("customer123")


@pytest.mark.parametrize(
    ("new", "again"),
    [("123", None), ("customer", None), (NEW_PASSWORD, "something-else-77")],
    ids=["too short", "too similar to username", "mismatch"],
)
def test_rejected_new_password_is_refused(client, customer, mailoutbox, new, again):
    client.force_login(customer)

    response = change_password(client, new=new, again=again)

    assert response.context["form"].errors["new_password2"]
    assert mailoutbox == []
    assert get_user_model().objects.get(pk=customer.pk).check_password("customer123")


def test_change_saves_password_and_returns_to_hub(client, customer):
    client.force_login(customer)

    response = change_password(client)

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    assert "Your password has been changed." in response.content.decode()
    customer.refresh_from_db()
    assert customer.check_password(NEW_PASSWORD)


def test_change_keeps_this_session_and_signs_out_others(client, customer):
    client.force_login(customer)
    other_device = Client()
    other_device.force_login(customer)

    change_password(client)

    assert client.get(reverse("accounts:security")).status_code == HTTPStatus.OK
    response = other_device.get(reverse("accounts:security"))
    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("accounts:login"))


def test_change_sends_password_changed_notice(client, customer, mailoutbox):
    client.force_login(customer)

    change_password(client)

    assert len(mailoutbox) == 1
    notice = mailoutbox[0]
    assert notice.to == ["customer@example.com"]
    assert "password" in notice.subject.lower()
    assert "was just changed" in notice.body


def test_staff_can_change_their_password(client, staff_user, mailoutbox):
    client.force_login(staff_user)

    change_password(client, old="employee123")

    staff_user.refresh_from_db()
    assert staff_user.check_password(NEW_PASSWORD)
    assert mailoutbox[0].to == ["employee@example.com"]


# --- Change email -------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "field", "message"),
    [
        (
            {"again": "someone.else@example.com"},
            "new_email2",
            "The two email addresses didn't match.",
        ),
        (
            {"password": "not-my-password"},
            "password",
            "Your password was entered incorrectly.",
        ),
        (
            {"email": "Employee@Example.com"},
            "new_email1",
            "That email address is already in use.",
        ),
        (
            {"email": "Customer@Example.com"},
            "new_email1",
            "That's already your email address.",
        ),
    ],
    ids=["mismatch", "wrong password", "used by another account", "unchanged"],
)
def test_bad_email_change_is_refused(
    client, customer, staff_user, mailoutbox, kwargs, field, message
):
    client.force_login(customer)

    response = change_email(client, **kwargs)

    assert any(message in error for error in response.context["form"].errors[field])
    assert mailoutbox == []
    customer.refresh_from_db()
    assert customer.email == "customer@example.com"


def test_duplicate_email_error_has_no_forgot_password_link(
    client, customer, staff_user
):
    client.force_login(customer)

    response = change_email(client, email="employee@example.com")

    assert reverse("accounts:password_reset") not in response.content.decode()


def test_email_change_saves_lowercase_and_returns_to_hub(client, customer):
    client.force_login(customer)

    response = change_email(client, email="Casey.New@Example.COM")

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    page = response.content.decode()
    assert "Your email address has been changed." in page
    assert NEW_EMAIL in page
    customer.refresh_from_db()
    assert customer.email == NEW_EMAIL


def test_email_change_notifies_the_old_address_only(client, customer, mailoutbox):
    client.force_login(customer)

    change_email(client)

    assert len(mailoutbox) == 1
    notice = mailoutbox[0]
    assert notice.to == ["customer@example.com"]
    assert "email" in notice.subject.lower()
    assert NEW_EMAIL in notice.body
    assert "Contact the store" in notice.body


def test_staff_can_change_their_email(client, staff_user, mailoutbox):
    client.force_login(staff_user)

    change_email(client, password="employee123")

    staff_user.refresh_from_db()
    assert staff_user.email == NEW_EMAIL
    assert mailoutbox[0].to == ["employee@example.com"]
