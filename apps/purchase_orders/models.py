from django.db import models
from apps.inventory.models import Product
from apps.suppliers.models import Supplier
import string
import random
from django.contrib.auth import get_user_model
from apps.orders.models import Order  # Import the existing Order model

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
    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Completed", "Completed"), ("Canceled", "Canceled")],
        default="Pending"
    )

    def __str__(self):
        return f"{self.purchase_order_id} - {self.product.name} from {self.supplier.name}"
