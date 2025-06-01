# apps/orders/models.py

from django.db import models
# Import Product from your inventory app - ALREADY THERE
from apps.inventory.models import Product
# Import ProductVariant from your store app - NEW IMPORT
from apps.store.models import ProductVariant # <--- NEW IMPORT
from apps.suppliers.models import Supplier # ALREADY THERE
import string, random
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone

User = get_user_model()



def generate_unique_order_id():
    while True:
        order_id = 'ORD' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not Order.objects.filter(order_id=order_id).exists():
            return order_id


class Order(models.Model):
    order_id = models.CharField(max_length=20, unique=True, editable=False, default=generate_unique_order_id)
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    shipping_address = models.TextField()
    billing_address = models.TextField(blank=True, null=True)
    
    PAYMENT_METHODS = [
        ('COD', 'Cash on Delivery'),
    ]
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='COD')
    
    ORDER_STATUS_CHOICES = [
        ("Pending", "Pending"), ("Processing", "Processing"), 
        ("Shipped", "Shipped"), ("Completed", "Completed"),
        ("Canceled", "Canceled"), ("Returned", "Returned"),
    ]
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="Pending")
    
    order_date = models.DateTimeField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-order_date']
    @property
    def get_total_cost(self):
        """Calculates the total price of all items in the order."""
        if self.items.exists():
            return sum(item.item_total for item in self.items.all())
        return Decimal('0.00')

    # @property
    # def get_total_cost(self): # <-- RENAMED TO get_total_cost
    #     """Calculates the total price of all items in the order."""
    #     # This will now correctly sum the item_total from each OrderItem
    #     return sum(item.item_total for item in self.items.all()) if self.items.exists() else Decimal('0.00')

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = generate_unique_order_id()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    def __str__(self):
        return f"Order {self.order_id} - {self.customer.username if self.customer else 'Guest'}"


class OrderItem(models.Model):
    """
    Represents a single item within an order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    
    # ***MODIFIED: Added a default value for price_at_order***
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00')) 
    
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('order', 'product_variant')
        ordering = ['added_at']

    @property
    def item_total(self): # <-- RENAMED FROM get_cart_total TO item_total
        """Calculates the total price for this specific order item."""
        # Ensure price_at_order is a Decimal before multiplication
        return self.price_at_order * self.quantity

    def save(self, *args, **kwargs):
        # Set price_at_order if not already set or is 0
        # ***MODIFIED: Robustly set price_at_order***
        if not self.price_at_order or self.price_at_order == Decimal('0.00'):
            if self.product_variant:
                # Use variant's price if available, fallback to product's price, or default to 0
                self.price_at_order = self.product_variant.price or \
                                      (self.product_variant.product.price if self.product_variant.product else Decimal('0.00')) or \
                                      Decimal('0.00')
            else:
                self.price_at_order = Decimal('0.00') # Fallback if product_variant is missing
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product_variant.product.name} ({self.product_variant.sku or 'Default'})"

