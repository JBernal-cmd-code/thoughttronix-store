"""Back-office coupon management — staff-only CRUD plus "Expire now".

Every view gates on StaffRequiredMixin; URLs use pks per the URL
conventions. The ``section`` context entry drives the active tab in the
staff shell (backoffice/base.html).
"""

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.mixins import StaffRequiredMixin

from .forms import CouponForm
from .models import Coupon, CouponError


class CouponListView(StaffRequiredMixin, ListView):
    """Every coupon — scheduled, active, and expired — with its use count."""

    template_name = "coupons/coupon_list.html"
    context_object_name = "coupons"
    extra_context = {"section": "coupons"}

    def get_queryset(self):
        return Coupon.objects.annotate(use_count=Count("orders")).prefetch_related(
            "products"
        )


class CouponCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Coupon
    form_class = CouponForm
    template_name = "coupons/coupon_form.html"
    success_url = reverse_lazy("coupons:list")
    success_message = "%(code)s created."
    extra_context = {"section": "coupons"}


class CouponUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Coupon
    form_class = CouponForm
    template_name = "coupons/coupon_form.html"
    success_url = reverse_lazy("coupons:list")
    success_message = "%(code)s saved."
    extra_context = {"section": "coupons"}


class CouponDeleteView(StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Coupon
    context_object_name = "coupon"
    template_name = "coupons/coupon_confirm_delete.html"
    success_url = reverse_lazy("coupons:list")
    success_message = "Coupon deleted."
    extra_context = {"section": "coupons"}


class ExpireCouponView(StaffRequiredMixin, View):
    """POST-only: end an active coupon right now."""

    def post(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        try:
            coupon.expire()
        except CouponError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"{coupon.code} has expired.")
        return redirect("coupons:list")
