"""Coupon forms: the shared code field and the back-office coupon form.

``CouponCodeField`` is the one place typed codes are normalized, so the
checkout and the back office agree that ``fall20`` is ``FALL20``.
"""

from django import forms

from products.forms import StyledModelForm

from .models import Coupon, normalize_code

DATETIME_FORMAT = "%Y-%m-%dT%H:%M"


class CouponCodeField(forms.CharField):
    """A coupon code, stripped and uppercased on the way in."""

    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 30)
        super().__init__(**kwargs)

    def to_python(self, value):
        return normalize_code(super().to_python(value))


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, **kwargs):
        super().__init__(format=DATETIME_FORMAT, **kwargs)


class CouponForm(StyledModelForm):
    """Create or edit a coupon.

    The model carries the percent range, the unique code, and the
    end-after-start rule; the one rule it can't carry is cross-field — a
    product-scoped coupon must name at least one product.
    """

    code = CouponCodeField(
        label="Code", help_text="Customers type this at checkout. Case doesn't matter."
    )

    class Meta:
        model = Coupon
        fields = ["code", "percent_off", "scope", "products", "starts_at", "expires_at"]
        labels = {
            "percent_off": "Percent off (1–99)",
            "scope": "Applies to",
            "starts_at": "Starts",
            "expires_at": "Expires",
        }
        help_texts = {
            "products": "Only used when the coupon applies to specific products.",
            "starts_at": "Times are UTC.",
        }
        widgets = {
            "starts_at": DateTimeLocalInput(),
            "expires_at": DateTimeLocalInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("starts_at", "expires_at"):
            self.fields[name].input_formats = [DATETIME_FORMAT]

    def clean(self):
        cleaned = super().clean()
        scope = cleaned.get("scope")
        if scope == Coupon.Scope.PRODUCTS and not cleaned.get("products"):
            self.add_error("products", "Pick at least one product for this coupon.")
        elif scope == Coupon.Scope.ORDER:
            # An order-wide coupon keeps no stale product list around.
            cleaned["products"] = []
        return cleaned
