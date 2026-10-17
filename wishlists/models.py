from django.conf import settings
from django.db import models
from django.utils import timezone

from products.models import Product


class Wishlist(models.Model):
    """A customer's private wishlist — one per user, created lazily.

    Never registered in Django admin: only its owner ever sees it.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist",
    )

    def __str__(self):
        return f"Wishlist for {self.user.username}"

    @classmethod
    def for_user(cls, user):
        """Return the user's wishlist, creating it on first touch."""
        wishlist, _ = cls.objects.get_or_create(user=user)
        return wishlist

    def add(self, product):
        """Save a product, available or not; saving it again does nothing."""
        item, _ = self.items.get_or_create(product=product)
        return item

    def remove(self, product):
        """Drop a product; removing one that isn't saved does nothing."""
        self.items.filter(product=product).delete()

    def lines(self):
        """Saved items, newest first, with their products loaded for display."""
        return self.items.select_related("product")

    def has(self, product):
        """Whether the product is on this wishlist."""
        return self.items.filter(product=product).exists()


class WishlistItem(models.Model):
    """One saved product; the wishlist–product pair is unique.

    ``added_at`` is a default rather than ``auto_now_add`` so ``seed`` can
    backdate it.
    """

    wishlist = models.ForeignKey(
        Wishlist, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="wishlist_items"
    )
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-added_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["wishlist", "product"], name="unique_wishlist_product"
            )
        ]

    def __str__(self):
        return self.product.name
