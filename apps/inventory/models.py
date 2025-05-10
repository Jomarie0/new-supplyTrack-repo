from django.db import models
from apps.suppliers.models import Supplier
import uuid

class Product(models.Model):
    product_id = models.CharField(max_length=10, unique=True, blank=False, null=False)

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    unit = models.CharField(max_length=50, default=0)
    category = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.pk and not self.product_id:
            # Only generate a new product_id on creation
            self.product_id = uuid.uuid4().hex[:10].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class StockMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    movement_type = models.CharField(
        max_length=10,
        choices=[("IN", "Stock In"), ("OUT", "Stock Out")],
    )
    quantity = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.movement_type} - {self.product.name} ({self.quantity})"
