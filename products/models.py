import secrets

from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.templatetags.static import static
from django.urls import reverse

# Categories with a dedicated placeholder illustration; anything else
# falls back to default.svg. A product without an uploaded image shows
# its category's placeholder, a static file.
PLACEHOLDER_CATEGORIES = {
    "home-assistants",
    "neural-implants",
    "neural-wearables",
    "accessories",
    "defense",
    "legacy-products",
}


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("products:category", kwargs={"slug": self.slug})

    @property
    def placeholder_image(self):
        """Static path of the placeholder image shown for this category's products."""
        if self.slug in PLACEHOLDER_CATEGORIES:
            return f"images/placeholders/{self.slug}.svg"
        return "images/placeholders/default.svg"


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        return self.filter(is_available=True)

    def search(self, text):
        """Simple icontains search over name and description."""
        return self.filter(
            models.Q(name__icontains=text) | models.Q(description__icontains=text)
        )


def product_image_path(instance, filename):
    """A fresh name per upload, so browsers never show a cached old image."""
    return f"products/{instance.slug}-{secrets.token_hex(4)}.webp"


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    # Always an 800×1000 WebP: everything stored here has been through
    # products.images.prepare_product_image.
    image = models.ImageField(upload_to=product_image_path, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Save, then delete the previous image file if it was replaced or
        cleared — after commit, so a rolled-back save keeps its image."""
        old_name = ""
        if self.pk:
            old_name = (
                Product.objects.filter(pk=self.pk)
                .values_list("image", flat=True)
                .first()
            ) or ""
        super().save(*args, **kwargs)
        if old_name and old_name != self.image.name:
            _delete_image_on_commit(self.image.storage, old_name)

    def get_absolute_url(self):
        return reverse("products:detail", kwargs={"slug": self.slug})

    @property
    def image_url(self):
        """The uploaded image's URL, or the category placeholder's.

        Falls back whenever the file isn't actually in storage, so a
        missing upload never renders as a broken image.
        """
        if self.image and self.image.storage.exists(self.image.name):
            return self.image.url
        return static(self.category.placeholder_image)


def _delete_image_on_commit(storage, name):
    transaction.on_commit(lambda: storage.delete(name))


# A signal rather than Product.delete(), because queryset deletes (the
# seed command's wipe) skip Model.delete() but still send post_delete.
@receiver(post_delete, sender=Product)
def delete_product_image(sender, instance, **kwargs):
    if instance.image:
        _delete_image_on_commit(instance.image.storage, instance.image.name)
