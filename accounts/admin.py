from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import SecurityEvent, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        *DjangoUserAdmin.fieldsets,
        ("ThoughtTronix", {"fields": ("job_title",)}),
    )
    # Email is required and unique, so the add form must ask for it too.
    add_fieldsets = (
        *DjangoUserAdmin.add_fieldsets,
        ("Contact", {"fields": ("email",)}),
    )
    list_display = ("username", "email", "job_title", "is_staff")


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    """The security activity log, for investigating a customer's "someone
    got into my account" report.

    Read-only for everyone, superusers included, so the log can be trusted
    as an audit record: events are written only by
    ``SecurityEvent.objects.record`` (and ``seed``), and removed only by its
    90-day pruning or by deleting the user.
    """

    list_display = ("user", "event_type", "created_at", "ip_address", "device")
    list_filter = ("event_type",)
    search_fields = ("user__username",)
    list_select_related = ("user",)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
