from django.db import models
from apps.inventory.models import Product
from apps.suppliers.models import Supplier
import string, random
from django.contrib.auth import get_user_model

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
    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Completed", "Completed"), ("Canceled", "Canceled")],
        default="Pending"
    )

    def __str__(self):
        return f"{self.order_id} - {self.product.name}"



# def generate_unique_purchase_order_id():
#     while True:
#         po_id = 'PO' + ''.join(random.choices(string.digits, k=8))
#         if not PurchaseOrder.objects.filter(purchase_order_id=po_id).exists():
#             return po_id


# class PurchaseOrder(models.Model):
#     purchase_order_id = models.CharField(max_length=20, unique=True, editable=False, default=generate_unique_purchase_order_id)
#     supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
#     created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     expected_delivery = models.DateField(null=True, blank=True)  # Added expected_delivery field

#     status = models.CharField(
#         max_length=10,
#         choices=[
#             ('pending', 'Pending'),
#             ('delivered', 'Delivered'),
#             ('cancelled', 'Cancelled')
#         ],
#         default='pending'
#     )

#     def __str__(self):
#         return f"{self.purchase_order_id} - {self.supplier.name}"

#     def total_cost(self):
#         return sum(item.total_price() for item in self.items.all())



# class PurchaseOrderItem(models.Model):
#     order = models.ForeignKey(PurchaseOrder, related_name='items', on_delete=models.CASCADE)
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     quantity = models.PositiveIntegerField()
#     unit_price = models.DecimalField(max_digits=10, decimal_places=2)

#     def __str__(self):
#         return f"{self.product.name} x {self.quantity}"

#     def total_price(self):
#         return self.quantity * self.unit_price
