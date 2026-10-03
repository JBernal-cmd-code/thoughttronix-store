"""Back-office forms for the catalog models.

ModelForms inherit the models' own rules (name required, slug unique);
the explicit ``price`` declaration adds the one rule the model doesn't
carry — the price must be positive. Widgets get their DaisyUI classes
in one shared ``__init__`` loop, as on ``CheckoutForm``.

The product image is validated and processed by
``products.images.prepare_product_image``; the form only calls it.
"""

from decimal import Decimal

from django import forms
from django.core.files.uploadedfile import UploadedFile

from .images import prepare_product_image
from .models import Category, Product, Tag


class ProductImageInput(forms.ClearableFileInput):
    """A clearable file input that renders only the file picker.

    The back-office template draws the current image and the Remove
    checkbox itself; the widget still reads that checkbox
    (``<name>-clear``) when the form is submitted.
    """

    template_name = "django/forms/widgets/file.html"


class StyledModelForm(forms.ModelForm):
    """Base form that dresses every widget in DaisyUI classes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "toggle toggle-primary"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "textarea w-full"
                widget.attrs.setdefault("rows", 6)
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs["class"] = "select h-auto w-full"
                widget.attrs.setdefault("size", 8)
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            elif isinstance(widget, forms.FileInput):
                widget.attrs["class"] = "file-input w-full"
            else:
                widget.attrs["class"] = "input w-full"


class ProductForm(StyledModelForm):
    price = forms.DecimalField(
        label="Price (USD)",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "slug",
            "tagline",
            "description",
            "image",
            "price",
            "category",
            "tags",
            "is_available",
            "is_featured",
        ]
        # A plain FileField: Django's ImageField would reject bad files
        # first, with its own generic message, before clean_image runs.
        field_classes = {"image": forms.FileField}
        widgets = {
            "image": ProductImageInput(
                attrs={"accept": "image/jpeg,image/png,image/webp"}
            )
        }
        help_texts = {
            "image": "JPEG, PNG, or WebP, up to 10 MB and at least 800×1000 "
            "pixels. It's cropped from the center to a 4:5 portrait.",
        }
        error_messages = {
            "image": {
                "contradiction": "Choose a new image or remove the current "
                "one, not both.",
            },
        }

    def clean_image(self):
        """Process a new upload; pass a cleared or unchanged image through."""
        image = self.cleaned_data["image"]
        if isinstance(image, UploadedFile):
            return prepare_product_image(image)
        return image


class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug"]


class TagForm(StyledModelForm):
    class Meta:
        model = Tag
        fields = ["name", "slug"]
