from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxLengthValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Product

MAX_STARS = 5
COMMENT_MAX_LENGTH = 2000


def validate_not_blank(value):
    """Refuse a comment that's only whitespace — it says nothing."""
    if not value.strip():
        raise ValidationError("Write a few words about the product.")


def star_row(filled):
    """Five booleans, ``filled`` of them True — one per star, for templates."""
    return [index < filled for index in range(MAX_STARS)]


@dataclass(frozen=True)
class ReviewSection:
    """Everything the product page's reviews section shows for one requester.

    ``own`` is the requester's review (pinned, never in ``others``);
    ``may_review`` is whether they get the create form.
    """

    product: Product
    count: int
    average: float | None
    own: "Review | None"
    may_review: bool
    others: list["Review"]

    @property
    def average_stars(self):
        return star_row(round(self.average or 0))


class ReviewQuerySet(models.QuerySet):
    def section(self, product, user):
        """The reviews section for ``product`` as ``user`` sees it.

        Works through the reverse relation too (``product.reviews``), so the
        product page can build it without importing this module.
        """
        reviews = list(self.filter(product=product).select_related("user"))
        own = None
        if user.is_authenticated:
            own = next((r for r in reviews if r.user_id == user.pk), None)
        count = len(reviews)
        return ReviewSection(
            product=product,
            count=count,
            average=sum(r.rating for r in reviews) / count if count else None,
            own=own,
            may_review=(
                user.is_authenticated
                and own is None
                and Review.is_eligible(user, product)
            ),
            others=[r for r in reviews if r is not own],
        )


class Review(models.Model):
    """A verified purchaser's star rating and comment on one product.

    One per customer per product, enforced by the database. Eligibility is
    checked only when a review is created; a later cancellation never
    removes or hides it. ``created_at`` is a default rather than
    ``auto_now_add`` so ``seed`` can backdate it.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(n, f"{n} star{'s' if n > 1 else ''}") for n in range(1, 6)],
        validators=[MinValueValidator(1), MaxValueValidator(MAX_STARS)],
    )
    comment = models.TextField(
        max_length=COMMENT_MAX_LENGTH,
        validators=[validate_not_blank, MaxLengthValidator(COMMENT_MAX_LENGTH)],
    )
    edited_by_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    objects = ReviewQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"], name="unique_review_user_product"
            )
        ]

    def __str__(self):
        return f"{self.product.name} — {self.rating}★"

    @classmethod
    def is_eligible(cls, user, product):
        """Whether ``user`` may review ``product``: their own account has an
        order containing it that wasn't cancelled.

        The order's account decides it, never a name typed on the order.
        Placed, Shipped, and Delivered all count; availability doesn't
        matter.
        """
        return (
            OrderItem.objects.filter(order__user=user, product=product)
            .exclude(order__status=Order.Status.CANCELLED)
            .exists()
        )

    @property
    def author_name(self):
        """First name and last initial ("Jordan P."), else "Verified buyer".

        Never the username or email.
        """
        first = self.user.first_name.strip()
        if not first:
            return "Verified buyer"
        last = self.user.last_name.strip()
        return f"{first} {last[0].upper()}." if last else first

    @property
    def stars(self):
        return star_row(self.rating)
