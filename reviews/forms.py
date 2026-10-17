from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    """A whole-star rating and a comment. The comment is stripped, so one
    that's only spaces is refused as empty."""

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.RadioSelect,
            "comment": forms.Textarea(
                attrs={"rows": 4, "class": "textarea textarea-bordered w-full"}
            ),
        }
        error_messages = {
            "rating": {"required": "Pick a star rating."},
            "comment": {"required": "Write a few words about the product."},
        }
