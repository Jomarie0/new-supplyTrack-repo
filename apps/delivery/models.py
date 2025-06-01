from django.db import models
from apps.orders.models import Order
from django.utils import timezone

class Delivery(models.Model):
    PENDING_DISPATCH = 'pending_dispatch'
    OUT_FOR_DELIVERY = 'out_for_delivery'
    DELIVERED = 'delivered'
    FAILED = 'failed'
    DELIVERY_STATUS_CHOICES = [
        (PENDING_DISPATCH, 'Pending Dispatch'),
        (OUT_FOR_DELIVERY, 'Out for Delivery'),
        (DELIVERED, 'Delivered'),
        (FAILED, 'Failed'),
    ]
    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='delivery')
    delivery_status = models.CharField(
        max_length=50,
        choices=DELIVERY_STATUS_CHOICES,
        default=PENDING_DISPATCH
    )
    delivered_at = models.DateTimeField(null=True, blank=True)

    is_archived = models.BooleanField(default=False)  # new field

    def __str__(self):
        return f"Delivery for Order {self.order.order_id} - Status: {self.get_delivery_status_display()}"

    class Meta:
        verbose_name_plural = "Deliveries"

    def save(self, *args, **kwargs):
        # Store old status to check for changes
        old_delivery_status = None
        if self.pk: # Only if object exists (i.e., not a new delivery)
            old_delivery_status = Delivery.objects.get(pk=self.pk).delivery_status

        super().save(*args, **kwargs) # Save the delivery first

        # Logic to update Order status based on Delivery status
        if self.delivery_status != old_delivery_status: # Only if status has actually changed
            if self.delivery_status == 'delivered' and self.order.status != 'Completed':
                self.order.status = 'Completed'
                self.order.save()
            elif self.delivery_status == 'failed':
                # If a delivery fails, the order status should reflect that it's no longer 'Shipped'
                # but is now in a state of needing attention for a return.
                if self.order.status == 'Shipped' or self.order.status == 'Out for Delivery': # Assuming you might have Out for Delivery as an Order status
                    self.order.status = 'Returned' # Or 'Failed Delivery - Awaiting Return'
                    self.order.save()
                    # IMPORTANT: Do NOT add to stock here. The item is still in transit.
            # You might want to handle 'out_for_delivery' or 'pending_dispatch' to set order.status to 'Shipped'
            # if it's not already.
            # elif self.delivery_status in ['pending_dispatch', 'out_for_delivery'] and self.order.status not in ['Shipped', 'Completed', 'Canceled', 'Returned']:
            #     self.order.status = 'Shipped'
            #     self.order.save()
