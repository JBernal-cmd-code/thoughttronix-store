"""Coupons at checkout: place_order's discount snapshot, the Apply preview,
and a refused code blocking the order with everything typed preserved."""

from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.urls import reverse
from django.utils import timezone

from coupons.models import Coupon, CouponError
from products.models import Product

from .models import CartItem, Order
from .services import place_order
from .test_checkout_form import VALID_DATA

# The cart_item fixture: 2 × Seraphine Home Hub at $349.99 = $699.98.
# FALL20 takes 20%: $140.00 off (139.996 rounded), leaving $559.98.


@pytest.fixture
def checkout_data():
    return dict(VALID_DATA)


@pytest.fixture
def pillow(category):
    return Product.objects.create(
        name="Charging Pillow",
        slug="charging-pillow",
        price=Decimal("69.00"),
        category=category,
    )


@pytest.fixture
def expired_coupon(db):
    now = timezone.now()
    return Coupon.objects.create(
        code="SUMMER25",
        percent_off=25,
        starts_at=now - timedelta(days=90),
        expires_at=now - timedelta(days=1),
    )


# --- place_order -------------------------------------------------------------


def test_an_order_wide_coupon_discounts_the_order(
    cart, cart_item, coupon, checkout_data
):
    order = place_order(cart, cart.user, checkout_data, coupon_code="fall20")

    assert order.subtotal == Decimal("699.98")
    assert order.discount == Decimal("140.00")
    assert order.total == Decimal("559.98")
    assert order.coupon == coupon
    assert order.coupon_code == "FALL20"
    assert order.coupon_percent == 20
    item = order.items.get()
    assert item.unit_price == Decimal("349.99")  # the price is kept, not rewritten
    assert item.discount == Decimal("140.00")
    assert item.net_total == Decimal("559.98")


def test_a_product_coupon_discounts_only_its_lines(
    cart, cart_item, product, pillow, checkout_data
):
    now = timezone.now()
    hub_sale = Coupon.objects.create(
        code="HUBSALE",
        percent_off=15,
        scope=Coupon.Scope.PRODUCTS,
        starts_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
    )
    hub_sale.products.set([product])
    cart.add(pillow)

    order = place_order(cart, cart.user, checkout_data, coupon_code="HUBSALE")

    hub_line, pillow_line = order.items.all()
    assert hub_line.discount == Decimal("105.00")  # 15% of 699.98, rounded
    assert pillow_line.discount == Decimal("0.00")
    assert order.discount == Decimal("105.00")
    assert order.total == Decimal("699.98") + Decimal("69.00") - Decimal("105.00")


def test_no_code_means_no_discount(cart, cart_item, coupon, checkout_data):
    order = place_order(cart, cart.user, checkout_data, coupon_code="")

    assert order.discount == Decimal("0.00")
    assert order.coupon is None
    assert order.coupon_code == ""
    assert order.total == Decimal("699.98")


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("THOUGHTS10", "We don't recognize that code."),
        ("SUMMER25", "This code has expired."),
    ],
)
def test_a_refused_code_places_nothing_and_keeps_the_cart(
    cart, cart_item, expired_coupon, checkout_data, code, message
):
    with pytest.raises(CouponError, match=message):
        place_order(cart, cart.user, checkout_data, coupon_code=code)

    assert not Order.objects.exists()
    assert CartItem.objects.exists()


# --- The checkout page -------------------------------------------------------


def test_checkout_places_a_discounted_order(client, customer, cart_item, coupon):
    client.force_login(customer)

    response = client.post(
        reverse("orders:checkout"), {**VALID_DATA, "coupon_code": "fall20"}, follow=True
    )

    order = Order.objects.get()
    assert order.total == Decimal("559.98")
    page = response.content.decode()
    assert "FALL20 saved you $140.00." in page


def test_an_expired_code_blocks_checkout_and_keeps_the_input(
    client, customer, cart_item, expired_coupon
):
    client.force_login(customer)

    response = client.post(
        reverse("orders:checkout"), {**VALID_DATA, "coupon_code": "summer25"}
    )

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "This code has expired." in page
    assert "12 Cortex Lane" in page  # everything typed is preserved
    assert 'value="SUMMER25"' in page
    assert not Order.objects.exists()
    assert CartItem.objects.exists()


def test_a_rerender_keeps_a_valid_code_applied(client, customer, cart_item, coupon):
    """Another field's error mustn't hide the discount the code still gives."""
    client.force_login(customer)
    bad = {**VALID_DATA, "card_cvv": "1", "coupon_code": "FALL20"}

    page = client.post(reverse("orders:checkout"), bad).content.decode()

    assert "559.98" in page
    assert "FALL20 applied" in page


# --- The Apply preview -------------------------------------------------------


def test_apply_previews_the_discount_without_saving(
    client, customer, cart_item, coupon
):
    client.force_login(customer)

    response = client.post(reverse("orders:apply_coupon"), {"coupon_code": "fall20"})

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page  # a partial, never base.html
    assert "−$140.00" in page
    assert "559.98" in page
    assert 'id="place-order-total" hx-swap-oob="true"' in page
    assert not Order.objects.exists()


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("NOPE", "We don&#x27;t recognize that code."),
        ("SUMMER25", "This code has expired."),
    ],
)
def test_apply_explains_a_refused_code(
    client, customer, cart_item, expired_coupon, code, message
):
    client.force_login(customer)

    page = client.post(
        reverse("orders:apply_coupon"), {"coupon_code": code}
    ).content.decode()

    assert message in page
    assert "699.98" in page  # the total is unchanged


def test_apply_requires_login(client, db):
    response = client.post(reverse("orders:apply_coupon"), {"coupon_code": "FALL20"})

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


# --- Receipts ----------------------------------------------------------------


def test_the_receipt_shows_the_discount(client, customer, cart, cart_item, coupon):
    order = place_order(cart, customer, dict(VALID_DATA), coupon_code="FALL20")
    client.force_login(customer)

    page = client.get(
        reverse("orders:detail", kwargs={"pk": order.pk})
    ).content.decode()

    assert "699.98" in page  # subtotal
    assert "−$140.00" in page
    assert "559.98" in page
