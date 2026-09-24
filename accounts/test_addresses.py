"""The address book: owner-scoped CRUD, validation, and ordering."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import Address

VALID_ADDRESS = {
    "full_name": "Casey Monroe",
    "street": "77 Cortex Lane",
    "line2": "Unit 7",
    "city": "Amarillo",
    "state": "TX",
    "zip_code": "79101",
}


@pytest.fixture
def other_customer(db):
    return get_user_model().objects.create_user(username="other", password="x")


@pytest.fixture
def others_address(other_customer):
    return Address.objects.create(
        user=other_customer,
        full_name="Dana Cole",
        street="9 Axon Avenue",
        city="Norman",
        state="OK",
        zip_code="73019",
    )


# --- Model behavior ----------------------------------------------------------


def test_addresses_come_newest_first(customer, address):
    newer = Address.objects.create(
        user=customer,
        full_name="Casey Monroe",
        street="1500 Dendrite Drive",
        city="Albuquerque",
        state="NM",
        zip_code="87102",
    )

    assert list(customer.addresses.all()) == [newer, address]


def test_checkout_initial_fills_both_sections(address):
    initial = address.as_checkout_initial()

    assert initial["shipping_street"] == "214 Synapse Street"
    assert initial["billing_street"] == "214 Synapse Street"
    assert initial["shipping_zip"] == "79015"
    assert initial["billing_zip"] == "79015"
    assert initial["shipping_name"] == "Casey Monroe"
    assert len(initial) == 12


# --- The list page -----------------------------------------------------------


def test_address_book_requires_login(client, db):
    response = client.get(reverse("accounts:addresses"))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_list_shows_the_customers_addresses(client, customer, address):
    client.force_login(customer)

    response = client.get(reverse("accounts:addresses"))

    assert response.status_code == HTTPStatus.OK
    assert "214 Synapse Street" in response.content.decode()


def test_list_has_a_designed_empty_state(client, customer):
    client.force_login(customer)

    response = client.get(reverse("accounts:addresses"))

    assert "No saved addresses yet" in response.content.decode()


def test_list_hides_another_customers_addresses(client, customer, others_address):
    client.force_login(customer)

    response = client.get(reverse("accounts:addresses"))

    assert "9 Axon Avenue" not in response.content.decode()


# --- Create, edit, delete ----------------------------------------------------


def test_create_attaches_the_address_to_the_signed_in_user(client, customer):
    client.force_login(customer)

    response = client.post(reverse("accounts:address_create"), VALID_ADDRESS)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("accounts:addresses")
    assert customer.addresses.get().street == "77 Cortex Lane"


def test_create_rejects_a_bad_zip(client, customer):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:address_create"), {**VALID_ADDRESS, "zip_code": "790"}
    )

    assert response.status_code == HTTPStatus.OK
    assert "Enter a ZIP code like 79016" in response.content.decode()
    assert not Address.objects.exists()


def test_edit_updates_the_address(client, customer, address):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:address_update", kwargs={"pk": address.pk}),
        {**VALID_ADDRESS, "city": "Canyon"},
    )

    address.refresh_from_db()
    assert response.status_code == HTTPStatus.FOUND
    assert address.street == "77 Cortex Lane"
    assert address.city == "Canyon"


def test_delete_removes_the_address(client, customer, address):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:address_delete", kwargs={"pk": address.pk})
    )

    assert response.status_code == HTTPStatus.FOUND
    assert not Address.objects.exists()


def test_customers_cannot_touch_anothers_address(client, customer, others_address):
    client.force_login(customer)
    pk = others_address.pk

    for name in ("address_update", "address_delete"):
        url = reverse(f"accounts:{name}", kwargs={"pk": pk})
        assert client.get(url).status_code == HTTPStatus.NOT_FOUND
        assert client.post(url, VALID_ADDRESS).status_code == HTTPStatus.NOT_FOUND

    others_address.refresh_from_db()
    assert others_address.street == "9 Axon Avenue"
