"""Django admin: the read-only security activity log and staff recovery."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import SecurityEvent

EventType = SecurityEvent.EventType


@pytest.fixture
def admin_client(client, db):
    admin = get_user_model().objects.create_superuser(
        "root", email="root@example.com", password="root123"
    )
    client.force_login(admin)
    return client


@pytest.fixture
def events(customer, staff_user):
    return {
        "failed": SecurityEvent.objects.create(
            user=customer,
            event_type=EventType.SIGN_IN_FAILED,
            ip_address="198.51.100.9",
        ),
        "changed": SecurityEvent.objects.create(
            user=customer,
            event_type=EventType.PASSWORD_CHANGED,
            ip_address="203.0.113.4",
        ),
        "staff": SecurityEvent.objects.create(
            user=staff_user, event_type=EventType.SIGNED_IN, ip_address="203.0.113.5"
        ),
    }


def changelist(client, **params):
    response = client.get(reverse("admin:accounts_securityevent_changelist"), params)
    assert response.status_code == HTTPStatus.OK
    return set(response.context["cl"].result_list)


# --- Viewing the log ----------------------------------------------------------


def test_superuser_can_view_the_security_event_changelist(admin_client, events):
    response = admin_client.get(reverse("admin:accounts_securityevent_changelist"))

    assert response.status_code == HTTPStatus.OK
    content = response.content.decode()
    for column in ("User", "Event type", "Created at", "Ip address", "Device"):
        assert column in content
    assert "198.51.100.9" in content


def test_changelist_filters_by_event_type(admin_client, events):
    assert changelist(admin_client, event_type=EventType.SIGN_IN_FAILED) == {
        events["failed"]
    }


def test_changelist_searches_by_username(admin_client, events):
    assert changelist(admin_client, q="employee") == {events["staff"]}


def test_superuser_can_view_a_single_event(admin_client, events):
    response = admin_client.get(
        reverse("admin:accounts_securityevent_change", args=[events["failed"].pk])
    )

    assert response.status_code == HTTPStatus.OK
    assert not response.context["has_change_permission"]


# --- Read-only ----------------------------------------------------------------


def test_superuser_cannot_add_an_event(admin_client, db):
    response = admin_client.get(reverse("admin:accounts_securityevent_add"))

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_superuser_cannot_change_an_event(admin_client, events):
    event = events["failed"]

    response = admin_client.post(
        reverse("admin:accounts_securityevent_change", args=[event.pk]),
        {"event_type": EventType.SIGNED_IN, "ip_address": "203.0.113.1"},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    event.refresh_from_db()
    assert event.event_type == EventType.SIGN_IN_FAILED


def test_superuser_cannot_delete_an_event(admin_client, events):
    event = events["failed"]

    response = admin_client.post(
        reverse("admin:accounts_securityevent_delete", args=[event.pk]),
        {"post": "yes"},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert SecurityEvent.objects.filter(pk=event.pk).exists()


def test_changelist_offers_no_bulk_delete(admin_client, events):
    response = admin_client.post(
        reverse("admin:accounts_securityevent_changelist"),
        {
            "action": "delete_selected",
            "_selected_action": [e.pk for e in events.values()],
            "post": "yes",
        },
    )

    # With delete blocked the changelist has no actions at all.
    assert response.context["action_form"] is None
    pks = [e.pk for e in events.values()]
    assert SecurityEvent.objects.filter(pk__in=pks).count() == len(pks)


# --- Staff recovery -------------------------------------------------------------


def test_superuser_can_set_a_staff_users_password(admin_client, staff_user):
    response = admin_client.post(
        reverse("admin:auth_user_password_change", args=[staff_user.pk]),
        {
            "usable_password": "true",
            "password1": "recovered-thought-42",
            "password2": "recovered-thought-42",
        },
    )

    assert response.status_code == HTTPStatus.FOUND
    staff_user.refresh_from_db()
    assert staff_user.check_password("recovered-thought-42")
