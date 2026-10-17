"""Wishlist views — thin per the architecture convention.

Every view requires sign-in and acts only on the requester's own
wishlist; no URL takes a user id or a wishlist id. Add and remove are
separate POST endpoints, not a toggle, so a repeated request or a stale
tab can't flip the state; each re-renders the wishlist button partial.
The My wishlist page's Remove re-renders the contents partial instead.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import TemplateView

from products.models import Product

from .models import Wishlist, WishlistItem


class WishlistView(LoginRequiredMixin, TemplateView):
    """The requester's "My wishlist" page."""

    template_name = "wishlists/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["wishlist"] = Wishlist.for_user(self.request.user)
        return context


class RemoveWishlistItemView(LoginRequiredMixin, View):
    """HTMX: drop a saved item, then re-render the wishlist contents.

    The item is always fetched through the requester's wishlist — never by
    bare pk — so another user's item is a 404.
    """

    def post(self, request, pk):
        item = get_object_or_404(WishlistItem, pk=pk, wishlist__user=request.user)
        wishlist = item.wishlist
        item.delete()
        return render(
            request,
            "wishlists/partials/_wishlist_contents.html",
            {"wishlist": wishlist},
        )


class WishlistButtonView(LoginRequiredMixin, View):
    """Base for the button endpoints: act, then re-render the button.

    Any product can be saved or removed, available or not; a pk that
    doesn't exist is a 404.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        saved = self.act(Wishlist.for_user(request.user), product)
        return render(
            request,
            "wishlists/partials/_wishlist_button.html",
            {"product": product, "on_wishlist": saved},
        )

    def act(self, wishlist, product):
        """Change the wishlist; return whether the product is now saved."""
        raise NotImplementedError


class AddToWishlistView(WishlistButtonView):
    def act(self, wishlist, product):
        wishlist.add(product)
        return True


class RemoveFromWishlistView(WishlistButtonView):
    def act(self, wishlist, product):
        wishlist.remove(product)
        return False
