from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


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
