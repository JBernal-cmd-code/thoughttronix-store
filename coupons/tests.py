"""Coupon rules: codes, status from dates, per-line discount math."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from products.models import Product

from .models import Coupon, CouponError

pytestmark = pytest.mark.django_db


def make_coupon(**overrides):
    now = timezone.now()
    fields = {
        "code": "HUBSALE",
        "percent_off": 15,
        "starts_at": now - timedelta(days=1),
        "expires_at": now + timedelta(days=1),
    }
    fields.update(overrides)
    return Coupon.objects.create(**fields)


# --- Codes -------------------------------------------------------------------


def test_codes_are_stored_uppercase_and_trimmed():
    assert make_coupon(code="  hubsale ").code == "HUBSALE"


def test_lookup_ignores_case_and_spaces(coupon):
    assert Coupon.objects.get_by_code(" fall20 ") == coupon


def test_an_unknown_code_is_not_recognized(db):
    with pytest.raises(CouponError, match="We don't recognize that code."):
        Coupon.objects.get_by_code("NOPE")


# --- Status is read off the dates --------------------------------------------


def test_status_follows_the_dates(coupon):
    assert coupon.status_at(coupon.starts_at - timedelta(seconds=1)) == "SCHEDULED"
    assert coupon.status_at(coupon.starts_at) == "ACTIVE"
    assert coupon.status_at(coupon.expires_at) == "EXPIRED"
    assert coupon.status == Coupon.Status.ACTIVE


def test_expire_ends_an_active_coupon_now(coupon):
    coupon.expire()

    coupon.refresh_from_db()
    assert coupon.status == Coupon.Status.EXPIRED


def test_only_an_active_coupon_can_be_expired():
    scheduled = make_coupon(
        starts_at=timezone.now() + timedelta(days=5),
        expires_at=timezone.now() + timedelta(days=10),
    )

    with pytest.raises(CouponError):
        scheduled.expire()


# --- Discounts ---------------------------------------------------------------


def test_an_order_wide_coupon_discounts_every_line(coupon, product):
    lines = [(product, Decimal("100.00")), (product, Decimal("50.00"))]

    assert coupon.discounts_for(lines) == [Decimal("20.00"), Decimal("10.00")]


def test_each_line_rounds_to_the_cent_half_up(coupon, product):
    # 20% of 0.03 is 0.006, and of 0.02 is 0.004: each line rounds alone.
    lines = [(product, Decimal("0.03")), (product, Decimal("0.02"))]

    assert coupon.discounts_for(lines) == [Decimal("0.01"), Decimal("0.00")]


def test_a_product_coupon_discounts_only_its_products(product, unavailable_product):
    hub_sale = make_coupon(scope=Coupon.Scope.PRODUCTS)
    hub_sale.products.set([product])
    lines = [(product, Decimal("100.00")), (unavailable_product, Decimal("100.00"))]

    assert hub_sale.discounts_for(lines) == [Decimal("15.00"), Decimal("0.00")]


@pytest.mark.parametrize(
    ("starts_in", "expires_in", "message"),
    [
        (1, 2, "This code isn't active yet."),
        (-2, -1, "This code has expired."),
    ],
)
def test_an_inactive_coupon_says_why(product, starts_in, expires_in, message):
    now = timezone.now()
    inactive = make_coupon(
        starts_at=now + timedelta(days=starts_in),
        expires_at=now + timedelta(days=expires_in),
    )

    with pytest.raises(CouponError, match=message):
        inactive.discounts_for([(product, Decimal("10.00"))])


def test_a_product_coupon_that_matches_nothing_is_refused(product, category):
    hub_sale = make_coupon(scope=Coupon.Scope.PRODUCTS)
    hub_sale.products.set([product])
    other = Product.objects.create(
        name="Charging Pillow", slug="charging-pillow", price=1, category=category
    )

    with pytest.raises(CouponError, match="doesn't apply to anything in your cart"):
        hub_sale.discounts_for([(other, Decimal("10.00"))])


def test_deleting_its_last_product_never_widens_a_product_coupon(product):
    hub_sale = make_coupon(scope=Coupon.Scope.PRODUCTS)
    hub_sale.products.set([product])
    stays = Product.objects.create(
        name="Charging Pillow",
        slug="charging-pillow",
        price=1,
        category=product.category,
    )
    product.delete()

    with pytest.raises(CouponError, match="doesn't apply"):
        hub_sale.discounts_for([(stays, Decimal("10.00"))])
