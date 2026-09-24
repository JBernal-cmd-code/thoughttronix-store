"""Seasonal discount coupons.

A coupon is a percentage off — the whole order, or only specific
products — valid between two moments. Its status (scheduled, active,
expired) is never stored: it is read off the dates. Orders snapshot
what a coupon gave them, so editing, expiring, or deleting a coupon
never rewrites an order.
"""

from collections.abc import Sequence
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from products.models import Product

CENT = Decimal("0.01")

ZERO = Decimal("0.00")


class CouponError(ValueError):
    """A code that can't be applied; the message is shown to the customer."""


def normalize_code(code: str) -> str:
    """Codes are case-insensitive: ``" fall20 "`` is ``"FALL20"``."""
    return code.strip().upper()


class CouponQuerySet(models.QuerySet):
    def get_by_code(self, code: str) -> "Coupon":
        """The coupon with this code, however it was typed.

        Raises ``CouponError`` if no coupon has the code.
        """
        try:
            return self.get(code=normalize_code(code))
        except self.model.DoesNotExist:
            raise CouponError("We don't recognize that code.") from None


class Coupon(models.Model):
    class Scope(models.TextChoices):
        ORDER = "ORDER", "Whole order"
        PRODUCTS = "PRODUCTS", "Specific products"

    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"

    code = models.CharField(max_length=30, unique=True)
    percent_off = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    scope = models.CharField(max_length=8, choices=Scope.choices, default=Scope.ORDER)
    # Used only when scope is PRODUCTS. A deleted product drops out of the
    # list; a product-scoped coupon left with none simply matches nothing
    # — it never widens into an order-wide one.
    products = models.ManyToManyField(Product, blank=True, related_name="coupons")
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    objects = CouponQuerySet.as_manager()

    class Meta:
        ordering = ["-starts_at", "code"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expires_at__gt=models.F("starts_at")),
                name="coupon_expires_after_it_starts",
                violation_error_message="The end must come after the start.",
            )
        ]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = normalize_code(self.code)
        super().save(*args, **kwargs)

    def status_at(self, now: datetime) -> "Coupon.Status":
        if now < self.starts_at:
            return self.Status.SCHEDULED
        if now >= self.expires_at:
            return self.Status.EXPIRED
        return self.Status.ACTIVE

    @property
    def status(self) -> "Coupon.Status":
        return self.status_at(timezone.now())

    def expire(self) -> None:
        """End an active coupon now. Past orders keep their discount."""
        if self.status is not self.Status.ACTIVE:
            raise CouponError(f"{self.code} isn't active, so it can't be expired.")
        self.expires_at = timezone.now()
        self.save(update_fields=["expires_at"])

    def discounts_for(
        self,
        lines: Sequence[tuple[Product, Decimal]],
        *,
        now: datetime | None = None,
    ) -> list[Decimal]:
        """The discount on each ``(product, line_total)`` line, in order.

        Each covered line loses ``percent_off`` of its total, rounded to
        the cent on its own — so an order's discount is exactly the sum of
        its lines'. Uncovered lines get zero.

        Raises ``CouponError`` if the coupon isn't active at ``now``
        (default: this moment) or covers none of the lines.
        """
        status = self.status_at(now or timezone.now())
        if status is self.Status.SCHEDULED:
            raise CouponError("This code isn't active yet.")
        if status is self.Status.EXPIRED:
            raise CouponError("This code has expired.")

        if self.scope == self.Scope.ORDER:
            covered = [True] * len(lines)
        else:
            product_ids = set(self.products.values_list("pk", flat=True))
            covered = [product.pk in product_ids for product, _ in lines]
        if not any(covered):
            raise CouponError("This code doesn't apply to anything in your cart.")

        return [
            self._percent_of(amount) if is_covered else ZERO
            for (_, amount), is_covered in zip(lines, covered, strict=True)
        ]

    def _percent_of(self, amount: Decimal) -> Decimal:
        return (amount * self.percent_off / 100).quantize(CENT, rounding=ROUND_HALF_UP)
