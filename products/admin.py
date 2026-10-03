from django.contrib import admin
from django.contrib.admin.widgets import AdminFileWidget

from .forms import ProductForm
from .models import Category, Product, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # The back-office form, so admin uploads get the same image validation
    # and processing (products.images.prepare_product_image).
    form = ProductForm
    list_display = ("name", "category", "price", "is_available")
    list_filter = ("category", "is_available", "tags")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # ProductForm's widget leaves the current image and Remove checkbox
        # to the back-office template; the admin draws its own.
        if db_field.name == "image":
            kwargs["widget"] = AdminFileWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)
