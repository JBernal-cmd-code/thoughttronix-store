"""Review views — thin per the architecture convention.

Every endpoint requires sign-in, enforced on the server. Create re-renders
the whole reviews section, so the summary always stays correct.
"""

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, render
from django.views import View

from accounts.mixins import HtmxLoginRequiredMixin
from products.models import Product

from .forms import ReviewForm
from .models import Review

SECTION = "reviews/partials/_reviews_section.html"


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
