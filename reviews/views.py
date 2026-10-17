"""Review views — thin per the architecture convention.

Every endpoint requires sign-in, enforced on the server. Create re-renders
the whole reviews section, so the summary always stays correct.
"""

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views import View

from accounts.mixins import HtmxLoginRequiredMixin
from products.models import Product

from .forms import ReviewForm
from .models import Review

SECTION = "reviews/partials/_reviews_section.html"
CARD = "reviews/partials/_review_card.html"
EDIT_FORM = "reviews/partials/_review_edit_form.html"


def render_section(request, product, **extra):
    """The reviews section for ``product`` as the requester sees it."""
    context = {"section": Review.objects.section(product, request.user), **extra}
    return render(request, SECTION, context)


class CreateReviewView(HtmxLoginRequiredMixin, View):
    """HTMX: write the requester's review of a product they bought."""

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        # A repeat (stale tab, double click) shows the existing review. It's
        # checked before eligibility: a review outlives a later cancellation.
        if product.reviews.filter(user=request.user).exists():
            return render_section(request, product, already_reviewed=True)
        if not Review.is_eligible(request.user, product):
            raise PermissionDenied
        form = ReviewForm(request.POST)
        if not form.is_valid():
            return render_section(request, product, form=form)
        form.instance.user = request.user
        form.instance.product = product
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            # A simultaneous duplicate got past the check above; the unique
            # constraint refused it.
            return render_section(request, product, already_reviewed=True)
        return render_section(request, product)


class ChangeableReviewMixin(HtmxLoginRequiredMixin):
    """Look up the review in the URL for someone allowed to change it.

    Anyone else gets a 404, so the response doesn't reveal it exists.
    """

    def get_review(self):
        review = get_object_or_404(
            Review.objects.select_related("user", "product"), pk=self.kwargs["pk"]
        )
        if not review.can_be_changed_by(self.request.user):
            raise Http404
        return review


class EditReviewView(ChangeableReviewMixin, View):
    """HTMX: swap one review card for its edit form."""

    def get(self, request, pk):
        review = self.get_review()
        form = ReviewForm(instance=review)
        return render(request, EDIT_FORM, {"review": review, "form": form})


class CancelEditView(ChangeableReviewMixin, View):
    """HTMX: put the review card back, unchanged."""

    def get(self, request, pk):
        return render(request, CARD, {"review": self.get_review()})


class UpdateReviewView(ChangeableReviewMixin, View):
    """HTMX: save an edit and re-render the whole section."""

    def post(self, request, pk):
        review = self.get_review()
        form = ReviewForm(request.POST)
        if not form.is_valid():
            response = render(request, EDIT_FORM, {"review": review, "form": form})
            # The form posts to the section; errors belong back in the card.
            response["HX-Retarget"] = f"#review-{review.pk}"
            response["HX-Reswap"] = "outerHTML"
            return response
        review.edit(request.user, **form.cleaned_data)
        return render_section(request, review.product)


class DeleteReviewView(ChangeableReviewMixin, View):
    """HTMX: delete the review and re-render the whole section."""

    def post(self, request, pk):
        review = self.get_review()
        review.delete()
        return render_section(request, review.product)
