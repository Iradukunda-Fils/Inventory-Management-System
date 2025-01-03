from django.contrib import admin
from .models import Category, Product, StockMovement, Sale, SalesSummary


# Define a custom AdminSite for enhanced customizations
class MyAdminSite(admin.AdminSite):
    site_header = "My Custom Admin"
    site_title = "Custom Admin Portal"
    index_title = "Welcome to My Custom Admin"


# Registering the models with the custom admin site
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created')
    search_fields = ('name',)
    list_filter = ('created',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'price', 'quantity', 'category', 'created_at', 'updated_at')
    search_fields = ('name', 'sku', 'category__name')
    list_filter = ('category', 'price', 'created_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity', 'reason', 'created_at')
    search_fields = ('product__name', 'reason')
    list_filter = ('movement_type', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'sale_price', 'total_amount', 'total_revenue', 'sale_date', 'created_at')
    search_fields = ('product__name',)
    list_filter = ('sale_date', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(SalesSummary)
class SalesSummaryAdmin(admin.ModelAdmin):
    list_display = ('product', 'total_sold', 'total_revenue', 'report_date')
    search_fields = ('product__name',)
    list_filter = ('report_date',)
    readonly_fields = ('report_date',)


