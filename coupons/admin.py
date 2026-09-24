from django.contrib import admin

from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "percent_off", "scope", "starts_at", "expires_at")
    list_filter = ("scope",)
    search_fields = ("code",)
    filter_horizontal = ("products",)
