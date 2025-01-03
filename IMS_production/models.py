from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid
from decimal import Decimal

# Create your models here.

class Category(models.Model):
    name = models.CharField(_("Category"), max_length=50)
    description = models.TextField(_("Description"))
    created = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Category: {self.name}"

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created']),
            models.Index(fields=['name','created']),
        ]


class Product(models.Model):
    name = models.CharField(_("Product Name"), max_length=50)
    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField(_("Description"))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(_("Price"), max_digits=10, decimal_places=2, default=0.00)
    quantity = models.IntegerField(_("Quantity"))
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Generate SKU only if it doesn't already exist
        self.sku = self.generate_sku()
        super().save(*args, **kwargs)

    def generate_sku(self):
        # Use a combination of name and a UUID for uniqueness
        base_sku = self.name[:3].upper() if self.name else 'PRD'
        unique_id = str(uuid.uuid4()).replace('-', '')[:6]  # Generate a short unique ID
        return f"{base_sku}-{unique_id}"
    
    def __str__(self):
        return f"Product: {self.name} - Price: {self.price}"
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['sku']),
            models.Index(fields=['price']),
            models.Index(fields=['price','name']),
            models.Index(fields=['quantity']),
            models.Index(fields=['name','price','quantity']),
            models.Index(fields=['created_at']),
        ]


class StockMovement(models.Model):
    MOVES = [
        ('Addition', 'Addition'),
        ('Subtraction', 'Subtraction')
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    movement_type = models.CharField(_("Movement Type"), choices=MOVES, max_length=50)
    quantity = models.IntegerField(_("Quantity"))
    reason = models.CharField(_("Reason"), max_length=100)
    created_at = models.DateTimeField(auto_now=True)
    
    def __str__(self) -> str:
        return f"Movement: {self.movement_type} for Product: {self.product.name}"
    
    class Meta:
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['movement_type']),
            models.Index(fields=['created_at']),
        ]


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sales')
    quantity = models.IntegerField(_("Quantity"))
    sale_price = models.DecimalField(_("Sale Price"), max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.IntegerField(_("Total Amount"))
    total_revenue = models.DecimalField(_("Total Revenue"), max_digits=10, decimal_places=2)
    sale_date = models.DateField(_("Date"), default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Calculate total amount
        self.total_amount = Decimal(self.quantity) * self.sale_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Product: {self.product.name} Sold on {self.sale_date}"
    
    class Meta:
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['sale_date']),
            models.Index(fields=['created_at']),
        ]


class SalesSummary(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sales_summary")
    total_sold = models.IntegerField()
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2)
    report_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Sales Summary for {self.product.name} on {self.report_date}"
    
    class Meta:
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['total_sold']),
            models.Index(fields=['total_revenue']),
            models.Index(fields=['report_date']),
        ]
