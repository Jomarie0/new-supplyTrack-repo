# apps/purchasing/models.py

from django.db import models
from django.utils import timezone
import random
import string
from decimal import Decimal # Ensure Decimal is imported

# Assuming your Product model is in apps.inventory
from apps.inventory.models import Product # <-- Keep this for PurchaseOrderItem
# Assuming your ProductVariant model is also in apps.inventory or apps.products
# Use ProductVariant if you purchase specific variants (e.g., Red T-shirt size M)
# If you only purchase base products, keep Product.
# from apps.store.models import ProductVariant # <--- NEW: Assuming ProductVariant is here

# Assuming your Supplier model is in apps.suppliers
from apps.suppliers.models import Supplier # <-- Keep this

# No need to import Order or User directly here unless explicitly used in these models
# from apps.orders.models import Order
# from django.contrib.auth import get_user_model
# User = get_user_model()


def generate_unique_purchase_order_id():
    """Generates a unique Purchase Order number."""
    while True:
        po_id = 'PO' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not PurchaseOrder.objects.filter(purchase_order_id=po_id).exists():
            return po_id


class PurchaseOrder(models.Model):
    """Represents a purchase order placed with a supplier."""

    purchase_order_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        default=generate_unique_purchase_order_id,
        help_text="Unique identifier for the purchase order."
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE, # Changed to CASCADE for simplicity, adjust if needed
        related_name='purchase_orders',
        help_text="The supplier from whom items are ordered.",
        null=True, 
        blank=True
    )
    
    # --- REMOVED: product, quantity, unit_price fields from here ---
    # product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # quantity = models.PositiveIntegerField()
    # unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    # total_cost will now be a summary of items

    order_date = models.DateTimeField(default=timezone.now, help_text="Date when the purchase order was created.")
    expected_delivery_date = models.DateField(null=True, blank=True, help_text="Estimated date for delivery of items.")
    received_date = models.DateField(null=True, blank=True, help_text="Actual date when all items were received.")

    # Expanded status choices for better workflow tracking
    STATUS_DRAFT = 'draft'
    STATUS_PENDING = 'pending' # PO created, not yet sent to supplier
    STATUS_ORDERED = 'ordered' # PO sent to supplier, awaiting confirmation/shipment
    STATUS_PARTIALLY_RECEIVED = 'partially_received' # Some items received
    STATUS_RECEIVED = 'received' # All items received
    STATUS_CANCELLED = 'cancelled'

    PO_STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PENDING, 'Pending Confirmation'),
        (STATUS_ORDERED, 'Ordered'),
        (STATUS_PARTIALLY_RECEIVED, 'Partially Received'),
        (STATUS_RECEIVED, 'Received'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    status = models.CharField(
        max_length=30, # Increased max_length for new statuses
        choices=PO_STATUS_CHOICES,
        default=STATUS_DRAFT,
        help_text="Current status of the purchase order."
    )
    
    # total_cost will be a calculated property, not a stored field, or updated by signals
    # If you want to store it for reporting, it should be updated by a method/signal
    # For now, let's make it a property, or keep it as a field and update it via save/delete of items.
    # Let's keep it as a field and update it via a method called from item save/delete.
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total cost of all items in the purchase order."
    )

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True, help_text="Any additional notes for the purchase order.")


    def __str__(self):
        return f"PO {self.purchase_order_id} - {self.supplier.name if self.supplier else 'No Supplier'}"

    # Custom save method for soft delete and PO number generation
    def save(self, *args, **kwargs):
        # Generate PO number only if it's a new instance and not already set
        if not self.pk and not self.purchase_order_id:
            self.purchase_order_id = generate_unique_purchase_order_id()
        super().save(*args, **kwargs)

    # Soft delete: mark as deleted with timestamp instead of actual deletion
    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    # Optional: restore method
    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    def calculate_total_cost(self):
        """Calculates and updates the total cost of the purchase order."""
        # Sums the total_price property from all related PurchaseOrderItems
        total = sum(item.total_price for item in self.items.all())
        if self.total_cost != total: # Only save if value actually changed
            self.total_cost = total
            self.save(update_fields=['total_cost']) # Save only the total_cost field

    class Meta:
        verbose_name_plural = "Purchase Orders"
        ordering = ['-order_date']


class PurchaseOrderItem(models.Model):
    """Represents a single item within a Purchase Order."""
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items', # This is how you'll access items from a PO: po.items.all()
        help_text="The purchase order this item belongs to."
    )
    
    """kapag wala sa pamimilian pede customized"""
    product_name_text = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional product name if no variant selected."
    )
    
    description = models.TextField(blank=True, null=True, help_text="Optional description for the order item.")

    
    product_variant = models.ForeignKey(
        'store.ProductVariant', # Link to your existing ProductVariant model
        on_delete=models.CASCADE,
        related_name='purchase_order_items',
        blank=True, null=True,
        help_text="The specific product variant being ordered."
    )
    quantity_ordered = models.PositiveIntegerField(
        help_text="The quantity of the product variant ordered."
    )
    quantity_received = models.PositiveIntegerField(
        default=0,
        help_text="The quantity of the product variant actually received so far."
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The cost per unit of the product variant at the time of order."
    )
    # You might want to add a received_date for this specific item if tracking partials closely

    def __str__(self):
        return f"{self.quantity_ordered}x {self.product_variant.product.name} (PO: {self.purchase_order.purchase_order_id})"

    @property
    def total_price(self):
        """Calculates the total price for this specific purchase order item."""
        return self.quantity_ordered * self.unit_cost

    @property
    def is_fully_received(self):
        return self.quantity_received >= self.quantity_ordered

    # Override save and delete to update parent PO's total_cost
    def save(self, *args, **kwargs):
        # Set unit_cost if not provided (e.g., when creating from form)
        if not self.unit_cost and self.product_variant:
            # Assuming ProductVariant has a 'cost' or 'price' field for purchasing
            self.unit_cost = self.product_variant.cost_price or self.product_variant.price or Decimal('0.00')
        super().save(*args, **kwargs)
        # Recalculate total cost of the parent PurchaseOrder after saving an item
        self.purchase_order.calculate_total_cost()

    def delete(self, *args, **kwargs):
        po = self.purchase_order # Get PO before deleting item
        super().delete(*args, **kwargs)
        # Recalculate total cost of the parent PurchaseOrder after deleting an item
        po.calculate_total_cost()


    class Meta:
        verbose_name_plural = "Purchase Order Items"
        unique_together = ('purchase_order', 'product_variant') # A variant can only be on a PO once
        ordering = ['product_variant__product__name'] # Order items by product name