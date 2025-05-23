from django.db import models
from apps.inventory.models import Product
from apps.suppliers.models import Supplier
import string, random
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone

User = get_user_model()


def generate_unique_order_id():
    while True:
        order_id = 'ORD'+''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not Order.objects.filter(order_id=order_id).exists():
            return order_id


class Order(models.Model):
    order_id = models.CharField(max_length=20, unique=True, editable=False, default=generate_unique_order_id)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    
    # Add unit price and total price for better sales analytics
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    order_date = models.DateTimeField(default=timezone.now)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Completed", "Completed"), ("Canceled", "Canceled")],
        default="Pending"
    )
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # optional, if you want customer info
    
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
        if not self.unit_price:
            self.unit_price = self.product.price
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_id} - {self.product.name}"
