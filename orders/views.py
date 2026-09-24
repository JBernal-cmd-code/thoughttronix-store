"""Cart and checkout views — thin per the architecture convention.

The three HTMX interactions of the core live here: add-to-cart, quantity
change, and line removal. Each renders a partial (never ``base.html``);
the responses carry the navbar badge as an out-of-band swap via the
``oob_badge`` context flag. Checkout is conventional full-page work:
validate the form, hand everything to ``place_order``. The one HTMX
touch at checkout is the coupon preview: Apply re-renders the order
summary with the discount, saving nothing.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from accounts.mixins import StaffRequiredMixin
from accounts.models import Address
from coupons.models import Coupon, CouponError, normalize_code
from products.models import Product

from .forms import CheckoutForm, OrderStatusForm
from .models import Cart, CartItem, Order
from .services import place_order


class CartView(LoginRequiredMixin, TemplateView):
    """The customer's cart page."""

    template_name = "orders/cart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cart"] = Cart.for_user(self.request.user)
        return context


class AddToCartView(LoginRequiredMixin, View):
    """HTMX: add a product; the button swaps and the badge updates OOB.

    Looks the product up through ``available()``, so adding an
    unavailable product 404s — the same not-for-sale semantics as the
    public catalog.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product.objects.available(), pk=pk)
        item = Cart.for_user(request.user).add(product)
        return render(
            request,
            "orders/partials/_add_button.html",
            {"product": product, "in_cart": item.quantity, "oob_badge": True},
        )


class CartItemActionView(LoginRequiredMixin, View):
    """Base for HTMX line mutations: act, then re-render the cart contents.

    Items are always fetched through the owner's cart — never by bare pk.
    """

    def post(self, request, pk):
        item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        self.act(item)
        return render(
            request,
            "orders/partials/_cart_contents.html",
            {"cart": item.cart, "oob_badge": True},
        )

    def act(self, item):
        raise NotImplementedError


class IncrementCartItemView(CartItemActionView):
    def act(self, item):
        item.increment()


class DecrementCartItemView(CartItemActionView):
    def act(self, item):
        item.decrement()


class RemoveCartItemView(CartItemActionView):
    def act(self, item):
        item.delete()


def quote_with_code(cart, code):
    """The cart priced with ``code``, plus the reason if the code won't apply.

    A bad code prices the cart without a discount rather than failing:
    the summary always shows what checkout would charge right now.
    """
    if not code:
        return cart.quote(), ""
    try:
        return cart.quote(Coupon.objects.get_by_code(code)), ""
    except CouponError as error:
        return cart.quote(), str(error)


class ApplyCouponView(LoginRequiredMixin, View):
    """HTMX: preview a coupon at checkout — nothing is saved.

    Re-renders the order summary (with the coupon box and its message)
    and swaps the Place order total out-of-band. ``place_order`` checks
    the code again when the order is actually placed.
    """

    def post(self, request):
        code = normalize_code(request.POST.get("coupon_code", ""))
        quote, error = quote_with_code(Cart.for_user(request.user), code)
        return render(
            request,
            "orders/partials/_order_summary.html",
            {
                "quote": quote,
                "coupon_code": code,
                "coupon_error": error,
                "oob_total": True,
            },
        )


class CheckoutView(LoginRequiredMixin, FormView):
    """The single checkout page: validate the form, hand off to the service.

    A cart that can't check out (empty, or holding a product that has
    since become unavailable) is sent back to the cart page to be fixed —
    ``place_order`` enforces the same rules transactionally as the
    backstop.

    Saved addresses prefill the form: the newest by default, or the one
    named by ``?address=<pk>`` (the link the address book puts on each
    row). Both address sections are filled from the one address.
    """

    template_name = "orders/checkout.html"
    form_class = CheckoutForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        cart = Cart.for_user(request.user)
        if not cart.items.exists():
            messages.info(request, "Your cart is empty — add something first.")
            return redirect("orders:cart")
        unavailable = [
            line.product.name for line in cart.lines() if not line.product.is_available
        ]
        if unavailable:
            messages.warning(
                request,
                f"No longer available: {', '.join(unavailable)}. "
                "Remove them from the cart to check out.",
            )
            return redirect("orders:cart")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Prefill both address sections from one saved address, if any.

        An ``?address=`` pk that isn't the customer's own — a stale
        bookmark, a deleted address, someone guessing — is treated as no
        hint at all rather than an error: the prefill is a convenience,
        and a bad one shouldn't stand between a customer and a purchase.
        """
        initial = super().get_initial()
        addresses = self.request.user.addresses
        address = None
        requested = self.request.GET.get("address", "")
        if requested.isdigit():
            address = addresses.filter(pk=requested).first()
        if address is None:
            address = addresses.first()
        if address is not None:
            initial.update(address.as_checkout_initial())
        return initial

    def get_context_data(self, **kwargs):
        """The summary is priced with whatever code the form holds.

        On a re-render the typed code stays applied (or explained), so
        the summary still matches what Place order would charge. An
        error already on the field — ``place_order`` refusing the code —
        is the one shown.
        """
        context = super().get_context_data(**kwargs)
        form = context["form"]
        code = normalize_code(form["coupon_code"].value() or "")
        quote, error = quote_with_code(Cart.for_user(self.request.user), code)
        field_errors = form.errors.get("coupon_code")
        context["quote"] = quote
        context["coupon_code"] = code
        context["coupon_error"] = field_errors[0] if field_errors else error
        context["has_addresses"] = self.request.user.addresses.exists()
        return context

    def form_valid(self, form):
        """Place the order; a code that won't apply blocks it, input kept."""
        cart = Cart.for_user(self.request.user)
        try:
            order = place_order(
                cart,
                self.request.user,
                form.cleaned_data,
                coupon_code=form.cleaned_data["coupon_code"],
            )
        except CouponError as error:
            form.add_error("coupon_code", str(error))
            return self.form_invalid(form)
        if form.cleaned_data["save_address"]:
            Address.objects.create_from_checkout(self.request.user, form.cleaned_data)
        message = f"Order {order.number} placed. Thank you!"
        if order.discount:
            message += f" {order.coupon_code} saved you ${order.discount:,}."
        messages.success(self.request, message)
        return redirect(reverse("orders:confirmation", kwargs={"pk": order.pk}))


class OwnOrdersMixin(LoginRequiredMixin):
    """Orders are always fetched through the owner — never by bare pk."""

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderConfirmationView(OwnOrdersMixin, DetailView):
    template_name = "orders/confirmation.html"
    context_object_name = "order"


class OrderHistoryView(OwnOrdersMixin, ListView):
    """The customer's orders, most recent first per the model ordering."""

    template_name = "orders/order_history.html"
    context_object_name = "orders"


class OrderDetailView(OwnOrdersMixin, DetailView):
    template_name = "orders/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("items")


# --- The back office --------------------------------------------------------
#
# Staff-only order oversight: every customer's orders, filterable by
# status, with the status dropdown on the detail page. The ``section``
# context entry drives the active tab in the staff shell.


class ManageOrderListView(StaffRequiredMixin, ListView):
    """All orders, most recent first, filterable via ``?status=``."""

    template_name = "orders/manage_orders.html"
    context_object_name = "orders"
    paginate_by = 20
    extra_context = {"section": "orders"}

    def get_queryset(self):
        orders = Order.objects.select_related("user")
        status = self.request.GET.get("status", "")
        if status in Order.Status.values:
            orders = orders.filter(status=status)
        return orders

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Order.Status.choices
        context["active_status"] = self.request.GET.get("status", "")
        return context


class ManageOrderDetailView(StaffRequiredMixin, DetailView):
    """Any order's detail, with the status form alongside."""

    template_name = "orders/manage_order_detail.html"
    context_object_name = "order"
    queryset = Order.objects.select_related("user").prefetch_related("items")
    extra_context = {"section": "orders"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_form"] = OrderStatusForm(instance=self.object)
        return context


class UpdateOrderStatusView(StaffRequiredMixin, View):
    """POST-only: set an order's status from the back-office dropdown."""

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"{order.number} is now {order.get_status_display().lower()}.",
            )
        else:
            messages.error(request, "That isn't a status an order can have.")
        return redirect("orders:manage_order_detail", pk=order.pk)
