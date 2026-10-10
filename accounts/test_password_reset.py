import re
from datetime import timedelta
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.test import Client
from django.urls import reverse

NEW_PASSWORD = "fresh-synapse-4242"


def request_reset(client, email):
    return client.post(reverse("accounts:password_reset"), {"email": email})


def reset_link(message):
    """The path of the reset link in a reset email."""
    return re.search(r"https?://[^/\s]+(/\S+)", message.body).group(1)


def set_new_password(client, link, password=NEW_PASSWORD):
    """Follow a reset link and submit a new password, as a browser would."""
    page = client.get(link, follow=True)
    form_url = page.redirect_chain[-1][0] if page.redirect_chain else link
    return client.post(
        form_url,
        {"new_password1": password, "new_password2": password},
        follow=True,
    )


# --- Ways in ------------------------------------------------------------------


def test_login_page_links_to_forgot_password(client, db):
    page = client.get(reverse("accounts:login")).content.decode()

    assert reverse("accounts:password_reset") in page
    assert "Forgot your password?" in page


def test_signup_duplicate_email_links_to_forgot_password(client, customer):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "fresh-thinker",
            "email": "Customer@Example.com",
            "password1": "neural-implant-9000",
            "password2": "neural-implant-9000",
        },
    )

    assert reverse("accounts:password_reset") in response.content.decode()


def test_signup_other_email_errors_do_not_link_to_forgot_password(client, db):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "fresh-thinker",
            "email": "not-an-email",
            "password1": "neural-implant-9000",
            "password2": "neural-implant-9000",
        },
    )

    assert response.context["form"].errors["email"]
    assert reverse("accounts:password_reset") not in response.content.decode()


def test_forgot_password_page_returns_200(client, db):
    response = client.get(reverse("accounts:password_reset"))

    assert response.status_code == HTTPStatus.OK


# --- The request --------------------------------------------------------------


@pytest.mark.parametrize(
    "typed", ["customer@example.com", "Customer@Example.com", "CUSTOMER@EXAMPLE.COM"]
)
def test_registered_customer_gets_one_email_in_any_case(
    client, customer, mailoutbox, typed
):
    response = request_reset(client, typed)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("accounts:password_reset_done")
    assert len(mailoutbox) == 1
    message = mailoutbox[0]
    assert message.to == ["customer@example.com"]
    assert "Your username is: customer" in message.body
    assert not message.alternatives  # plain text only


def test_reset_link_works(client, customer, mailoutbox):
    request_reset(client, "customer@example.com")

    page = client.get(reset_link(mailoutbox[0]), follow=True)

    assert page.context["validlink"]


def make_inactive(user):
    user.is_active = False
    user.save()


def make_unusable(user):
    user.set_unusable_password()
    user.save()


@pytest.mark.parametrize(
    "account",
    ["unregistered", "staff", "inactive", "unusable password"],
)
def test_ineligible_accounts_get_no_email_and_the_same_page(
    client, customer, staff_user, mailoutbox, account
):
    email = {
        "unregistered": "nobody@example.com",
        "staff": "employee@example.com",
        "inactive": "customer@example.com",
        "unusable password": "customer@example.com",
    }[account]
    if account == "inactive":
        make_inactive(customer)
    elif account == "unusable password":
        make_unusable(customer)

    response = request_reset(client, email)
    done = client.get(response.url).content.decode()

    assert response.url == reverse("accounts:password_reset_done")
    assert mailoutbox == []
    assert "If an account exists for <span" in done
    assert email in done


def test_done_page_is_identical_for_registered_and_unregistered(client, customer):
    def done_page(email):
        request_reset(client, email)
        page = client.get(reverse("accounts:password_reset_done")).content.decode()
        # Only the typed address and the per-request CSRF token may differ.
        page = page.replace(email, "EMAIL")
        return re.sub(r'"X-CSRFToken": "[^"]+"', "", page)

    assert done_page("customer@example.com") == done_page("nobody@example.com")


def test_done_page_shows_typed_address_but_url_never_does(client, db):
    response = request_reset(client, "Casey@Exampel.com")
    done = client.get(response.url)

    assert "Casey" not in response.url
    assert "Casey@Exampel.com" in done.content.decode()
    assert "spelled" in done.content.decode()


# --- The link -----------------------------------------------------------------


def test_used_link_is_rejected(client, customer, mailoutbox):
    request_reset(client, "customer@example.com")
    link = reset_link(mailoutbox[0])
    set_new_password(client, link)

    page = client.get(link, follow=True)

    assert not page.context["validlink"]
    assert "doesn't work" in page.content.decode()


def test_link_older_than_one_hour_is_rejected(
    client, customer, mailoutbox, monkeypatch
):
    request_reset(client, "customer@example.com")
    link = reset_link(mailoutbox[0])
    issued = PasswordResetTokenGenerator._now
    monkeypatch.setattr(
        PasswordResetTokenGenerator,
        "_now",
        lambda self: issued(self) + timedelta(hours=1, seconds=1),
    )

    page = client.get(link, follow=True)

    assert not page.context["validlink"]


def test_reset_timeout_is_one_hour(settings):
    assert settings.PASSWORD_RESET_TIMEOUT == 3600


# --- After the reset ----------------------------------------------------------


def test_reset_sets_password_and_lands_on_sign_in(client, customer, mailoutbox):
    request_reset(client, "customer@example.com")

    response = set_new_password(client, reset_link(mailoutbox[0]))

    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    assert "Your password has been reset" in response.content.decode()
    assert not response.context["user"].is_authenticated
    customer.refresh_from_db()
    assert customer.check_password(NEW_PASSWORD)


def test_reset_sends_password_changed_notice(client, customer, mailoutbox):
    request_reset(client, "customer@example.com")

    set_new_password(client, reset_link(mailoutbox[0]))

    assert len(mailoutbox) == 2
    notice = mailoutbox[1]
    assert notice.to == ["customer@example.com"]
    assert "password" in notice.subject.lower()
    assert "was just changed" in notice.body


def test_reset_signs_out_existing_sessions(client, customer, mailoutbox):
    other_device = Client()
    other_device.force_login(customer)
    assert other_device.get(reverse("accounts:addresses")).status_code == HTTPStatus.OK

    request_reset(client, "customer@example.com")
    set_new_password(client, reset_link(mailoutbox[0]))

    response = other_device.get(reverse("accounts:addresses"))
    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("accounts:login"))


def test_rejected_new_password_keeps_the_old_one(client, customer, mailoutbox):
    request_reset(client, "customer@example.com")

    response = set_new_password(client, reset_link(mailoutbox[0]), password="123")

    assert response.context["form"].errors
    assert len(mailoutbox) == 1
    assert get_user_model().objects.get(pk=customer.pk).check_password("customer123")
