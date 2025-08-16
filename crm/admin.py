from django.contrib import admin
from .models import Customer, Product, Order


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "phone")
    search_fields = ("name", "email", "phone")
    ordering = ("id",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "stock")
    search_fields = ("name",)
    list_filter = ("stock",)
    ordering = ("id",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "total_amount", "order_date")
    search_fields = ("customer__name", "customer__email")
    list_filter = ("order_date",)
    ordering = ("-order_date",)
