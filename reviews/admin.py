from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Every review across the store, in one place.

    Add and change are blocked for everyone, superusers included, so the
    admin can't become a way around the purchase rule or the "Edited by
    staff" mark: reviews are written on the product page and edited through
    ``Review.edit``. Delete is allowed.
    """

    list_display = ("product", "user", "rating", "created_at", "edited_by_staff")
    list_filter = ("rating",)
    search_fields = ("product__name", "user__username")
    list_select_related = ("product", "user")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
