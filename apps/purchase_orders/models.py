from django.db import models
from apps.inventory.models import Product
from apps.suppliers.models import Supplier
import string
import random
from django.contrib.auth import get_user_model
from apps.orders.models import Order  # Import the existing Order model
from decimal import Decimal
from django.utils import timezone

User  = get_user_model()

def generate_unique_purchase_order_id():
    while True:
        po_id = 'PO' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not PurchaseOrder.objects.filter(purchase_order_id=po_id).exists():
            return po_id

class PurchaseOrder(models.Model):
    purchase_order_id = models.CharField(max_length=20, unique=True, editable=False, default=generate_unique_purchase_order_id)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    
    # Fixed: added default values to avoid integrity errors
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Completed", "Completed"), ("Canceled", "Canceled")],
        default="Pending"
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def delete(self, using=None, keep_parents=False):
        # Soft delete: mark as deleted with timestamp instead of actual deletion
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    # Optional: you can add a restore method
    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    def save(self, *args, **kwargs):
        # Default unit price fallback if not provided
        if not self.unit_price:
            self.unit_price = self.product.price
        self.total_cost = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.purchase_order_id} - {self.product.name} from {self.supplier.name}"
