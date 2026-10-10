"""Security activity: recording and pruning events, the sign-in source, the
device label, and the hub's recent-activity list."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from accounts.models import SecurityEvent
from accounts.user_agents import describe_user_agent

FIREFOX_ON_WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"
)

SIGNED_IN = SecurityEvent.EventType.SIGNED_IN


@pytest.fixture
def other_customer(db):
    return get_user_model().objects.create_user(
        username="other", email="other@example.com", password="other123"
    )


def backdated_event(user, days_ago, ip="203.0.113.10"):
    return SecurityEvent.objects.create(
        user=user,
        event_type=SIGNED_IN,
        created_at=timezone.now() - timedelta(days=days_ago),
        ip_address=ip,
    )


# --- Recording ----------------------------------------------------------------


def test_signing_in_records_a_signed_in_event(client, customer):
    client.post(
        reverse("accounts:login"),
        {"username": "customer", "password": "customer123"},
        REMOTE_ADDR="203.0.113.7",
        HTTP_USER_AGENT=FIREFOX_ON_WINDOWS,
    )

    event = customer.security_events.get()
    assert event.event_type == SIGNED_IN
    assert event.ip_address == "203.0.113.7"
    assert event.user_agent == FIREFOX_ON_WINDOWS
    assert event.device == "Firefox on Windows"


def test_a_wrong_password_records_no_signed_in_event(client, customer):
    client.post(reverse("accounts:login"), {"username": "customer", "password": "nope"})

    assert not customer.security_events.filter(event_type=SIGNED_IN).exists()


def test_record_without_remote_address_leaves_ip_empty(customer):
    request = RequestFactory().get("/")
    del request.META["REMOTE_ADDR"]

    event = SecurityEvent.objects.record(customer, SIGNED_IN, request)

    assert event.ip_address is None
    assert event.user_agent == ""


def test_record_prunes_only_this_users_old_events(customer, other_customer):
    stale = backdated_event(customer, days_ago=91)
    recent = backdated_event(customer, days_ago=89)
    someone_elses_stale = backdated_event(other_customer, days_ago=200)

    new = SecurityEvent.objects.record(customer, SIGNED_IN, RequestFactory().get("/"))

    assert set(customer.security_events.all()) == {recent, new}
    assert not SecurityEvent.objects.filter(pk=stale.pk).exists()
    assert SecurityEvent.objects.filter(pk=someone_elses_stale.pk).exists()


# --- Device label -------------------------------------------------------------


@pytest.mark.parametrize(
    ("user_agent", "label"),
    [
        (FIREFOX_ON_WINDOWS, "Firefox on Windows"),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Chrome on Windows",
        ),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "Edge on Windows",
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/18.0 Safari/605.1.15",
            "Safari on macOS",
        ),
        (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 "
            "Mobile/15E148 Safari/604.1",
            "Safari on iOS",
        ),
        (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/129.0.0.0 "
            "Mobile/15E148 Safari/604.1",
            "Chrome on iOS",
        ),
        (
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
            "Chrome on Android",
        ),
        (
            "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
            "Firefox on Linux",
        ),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 OPR/114.0.0.0",
            "Opera on Windows",
        ),
        ("curl/8.9.1", "Unknown device"),
        ("", "Unknown device"),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Unknown browser on Windows"),
    ],
    ids=[
        "firefox-windows",
        "chrome-windows",
        "edge-windows",
        "safari-macos",
        "safari-ios",
        "chrome-ios",
        "chrome-android",
        "firefox-linux",
        "opera-windows",
        "unknown",
        "empty",
        "unknown browser",
    ],
)
def test_describe_user_agent(user_agent, label):
    assert describe_user_agent(user_agent) == label


# --- The hub's recent activity ------------------------------------------------


def test_hub_shows_ten_newest_events_of_the_signed_in_user_only(
    client, customer, other_customer
):
    for days_ago in range(1, 13):
        backdated_event(customer, days_ago, ip=f"198.51.100.{days_ago}")
    backdated_event(other_customer, days_ago=0, ip="203.0.113.99")
    client.force_login(customer)
    customer.security_events.filter(ip_address__isnull=True).delete()

    response = client.get(reverse("accounts:security"))

    events = list(response.context["events"])
    assert [e.ip_address for e in events] == [f"198.51.100.{n}" for n in range(1, 11)]
    page = response.content.decode()
    assert "198.51.100.11" not in page
    assert "203.0.113.99" not in page


def test_hub_event_shows_type_time_ip_and_device(client, customer):
    SecurityEvent.objects.create(
        user=customer,
        event_type=SIGNED_IN,
        created_at=timezone.now().replace(year=2026, month=10, day=3, hour=14),
        ip_address="203.0.113.7",
        user_agent=FIREFOX_ON_WINDOWS,
    )
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "Signed in" in page
    assert "Oct 3, 2026, 2:" in page
    assert "203.0.113.7" in page
    assert "Firefox on Windows" in page


def test_hub_shows_empty_state_without_events(client, customer):
    client.force_login(customer)
    customer.security_events.all().delete()

    page = client.get(reverse("accounts:security")).content.decode()

    assert "No security activity yet" in page
