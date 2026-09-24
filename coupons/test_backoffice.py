"""Back-office coupon management: access control, CRUD, validation, expiry."""

from datetime import timedelta
from http import HTTPStatus

import pytest
from django.urls import reverse
from django.utils import timezone

from orders.models import Order
from orders.services import place_order
from orders.test_checkout_form import VALID_DATA

from .models import Coupon

pytestmark = pytest.mark.django_db

FORMAT = "%Y-%m-%dT%H:%M"


def coupon_urls(coupon):
    """Every staff-only coupon URL that answers a GET."""
    return [
        reverse("coupons:list"),
        reverse("coupons:create"),
        reverse("coupons:update", kwargs={"pk": coupon.pk}),
        reverse("coupons:delete", kwargs={"pk": coupon.pk}),
    ]


def coupon_data(**overrides):
    now = timezone.now()
    data = {
        "code": "winter15",
        "percent_off": "15",
        "scope": Coupon.Scope.ORDER,
        "starts_at": (now - timedelta(days=1)).strftime(FORMAT),
        "expires_at": (now + timedelta(days=30)).strftime(FORMAT),
    }
    data.update(overrides)
    return data


# --- Access control ----------------------------------------------------------


def test_anonymous_users_are_sent_to_login(client, coupon):
    for url in coupon_urls(coupon):
        response = client.get(url)

        assert response.status_code == HTTPStatus.FOUND, url
        assert reverse("accounts:login") in response.url


def test_customers_get_403(client, customer, coupon):
    client.force_login(customer)

    for url in coupon_urls(coupon):
        assert client.get(url).status_code == HTTPStatus.FORBIDDEN, url
    expire = reverse("coupons:expire", kwargs={"pk": coupon.pk})
    assert client.post(expire).status_code == HTTPStatus.FORBIDDEN


def test_staff_get_200(client, staff_user, coupon):
    client.force_login(staff_user)

    for url in coupon_urls(coupon):
        response = client.get(url)

        assert response.status_code == HTTPStatus.OK, url
        assert "{#" not in response.content.decode(), url


def test_the_staff_shell_has_a_coupons_tab(client, staff_user):
    client.force_login(staff_user)

    page = client.get(reverse("orders:manage_orders")).content.decode()

    assert reverse("coupons:list") in page


# --- Creating and editing ----------------------------------------------------


def test_staff_can_create_an_order_wide_coupon(client, staff_user):
    client.force_login(staff_user)

    response = client.post(reverse("coupons:create"), coupon_data(), follow=True)

    coupon = Coupon.objects.get()
    assert coupon.code == "WINTER15"  # typed lowercase, stored uppercase
    assert coupon.percent_off == 15
    assert coupon.status == Coupon.Status.ACTIVE
    assert "WINTER15 created." in response.content.decode()


def test_staff_can_create_a_product_coupon(client, staff_user, product):
    client.force_login(staff_user)

    client.post(
        reverse("coupons:create"),
        coupon_data(scope=Coupon.Scope.PRODUCTS, products=[str(product.pk)]),
    )

    assert list(Coupon.objects.get().products.all()) == [product]


def test_a_product_coupon_needs_a_product(client, staff_user):
    client.force_login(staff_user)

    response = client.post(
        reverse("coupons:create"), coupon_data(scope=Coupon.Scope.PRODUCTS)
    )

    assert response.status_code == HTTPStatus.OK
    assert "Pick at least one product" in response.content.decode()
    assert not Coupon.objects.exists()


def test_an_order_wide_coupon_drops_any_picked_products(client, staff_user, product):
    client.force_login(staff_user)

    client.post(reverse("coupons:create"), coupon_data(products=[str(product.pk)]))

    assert not Coupon.objects.get().products.exists()


@pytest.mark.parametrize("percent", ["0", "100", "12.5"])
def test_percent_must_be_a_whole_number_from_1_to_99(client, staff_user, percent):
    client.force_login(staff_user)

    response = client.post(reverse("coupons:create"), coupon_data(percent_off=percent))

    assert response.status_code == HTTPStatus.OK
    assert not Coupon.objects.exists()


def test_the_end_must_come_after_the_start(client, staff_user):
    client.force_login(staff_user)
    now = timezone.now()

    response = client.post(
        reverse("coupons:create"),
        coupon_data(
            starts_at=now.strftime(FORMAT),
            expires_at=(now - timedelta(days=1)).strftime(FORMAT),
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert "The end must come after the start." in response.content.decode()
    assert not Coupon.objects.exists()


def test_codes_are_unique_whatever_the_case(client, staff_user, coupon):
    client.force_login(staff_user)

    response = client.post(reverse("coupons:create"), coupon_data(code="fall20"))

    assert response.status_code == HTTPStatus.OK
    assert "already exists" in response.content.decode()
    assert Coupon.objects.count() == 1


def test_staff_can_edit_a_coupon(client, staff_user, coupon):
    client.force_login(staff_user)

    client.post(
        reverse("coupons:update", kwargs={"pk": coupon.pk}),
        coupon_data(code="FALL20", percent_off="30"),
    )

    coupon.refresh_from_db()
    assert coupon.percent_off == 30


# --- Expiring and deleting never touch past orders ---------------------------


@pytest.fixture
def discounted_order(cart, cart_item, coupon):
    return place_order(cart, cart.user, dict(VALID_DATA), coupon_code="FALL20")


def test_expire_now_ends_the_coupon(client, staff_user, coupon, discounted_order):
    client.force_login(staff_user)

    response = client.post(reverse("coupons:expire", kwargs={"pk": coupon.pk}))

    assert response.url == reverse("coupons:list")
    coupon.refresh_from_db()
    assert coupon.status == Coupon.Status.EXPIRED
    discounted_order.refresh_from_db()
    assert discounted_order.coupon == coupon
    assert discounted_order.discount == 140


def test_deleting_a_coupon_keeps_the_orders_snapshot(
    client, staff_user, coupon, discounted_order
):
    client.force_login(staff_user)

    client.post(reverse("coupons:delete", kwargs={"pk": coupon.pk}))

    assert not Coupon.objects.exists()
    order = Order.objects.get()
    assert order.coupon is None
    assert order.coupon_code == "FALL20"
    assert order.coupon_percent == 20
    assert order.discount == 140
    assert order.items.get().discount == 140


def test_editing_a_coupon_never_reprices_an_order(
    client, staff_user, coupon, discounted_order
):
    client.force_login(staff_user)

    client.post(
        reverse("coupons:update", kwargs={"pk": coupon.pk}),
        coupon_data(code="FALL20", percent_off="50"),
    )

    discounted_order.refresh_from_db()
    assert discounted_order.coupon_percent == 20
    assert discounted_order.discount == 140


# --- The list ----------------------------------------------------------------


def test_the_list_shows_status_and_use_count(
    client, staff_user, coupon, discounted_order
):
    client.force_login(staff_user)

    response = client.get(reverse("coupons:list"))

    assert response.context["coupons"][0].use_count == 1
    page = response.content.decode()
    assert "FALL20" in page
    assert "Active" in page
    assert "Expire now" in page


def test_the_list_has_a_designed_empty_state(client, staff_user):
    client.force_login(staff_user)

    page = client.get(reverse("coupons:list")).content.decode()

    assert "No coupons yet" in page
