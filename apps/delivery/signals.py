# apps/delivery/signals.py

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# Import your models from their respective apps
from apps.orders.models import Order # Assuming Order model is in an app named 'orders'
from .models import Delivery # Assuming Delivery is in the same app as signals.py

logger = logging.getLogger(__name__)

# --- Signal for Order status changes affecting Delivery status ---
@receiver(post_save, sender=Order)
def update_delivery_status_from_order(sender, instance, created, **kwargs):
    # This signal triggers AFTER an Order object is saved.
    # We only want to act if the 'status' field of the Order has changed,
    # and if the order was not just created (initial delivery creation is handled by another signal).
    if created or (kwargs.get('update_fields') and 'status' not in kwargs['update_fields']):
        return # Do not proceed if it's a new order or status wasn't updated

    order = instance
    delivery = getattr(order, 'delivery', None) # Safely get the associated delivery object

    # We only update if a Delivery object already exists.
    # If it doesn't, it implies the Order was just created and the 'create_delivery_on_order_creation'
    # signal (in orders/signals.py) should have handled its initial creation.
    if not delivery:
        logger.warning(f"No Delivery object found for Order {order.order_id} when trying to update delivery status from order status change. This shouldn't happen if create_delivery_on_order_creation signal is working correctly.")
        return

    # Store old status to check for changes and prevent unnecessary saves
    # Fetching the delivery instance from DB directly is important if other fields were changed
    # in the same save that triggered this signal, but the status was not.
    try:
        old_delivery_status = Delivery.objects.get(pk=delivery.pk).delivery_status
    except Delivery.DoesNotExist:
        old_delivery_status = None # Should not happen if delivery exists

    # Determine the desired delivery status based on the order's new status
    new_delivery_status = old_delivery_status # Default to current status
    
    if order.status in ["Pending", "Processing"] and old_delivery_status != Delivery.PENDING_DISPATCH:
        new_delivery_status = Delivery.PENDING_DISPATCH
    elif order.status == "Shipped" and old_delivery_status != Delivery.OUT_FOR_DELIVERY:
        new_delivery_status = Delivery.OUT_FOR_DELIVERY

    # Only save if the delivery status actually needs to change
    if new_delivery_status != old_delivery_status:
        delivery.delivery_status = new_delivery_status
        # Use update_fields to prevent infinite loops and only save the changed field
        delivery.save(update_fields=['delivery_status']) 
        logger.info(f"Delivery {delivery.id} status updated to '{new_delivery_status}' based on Order {order.order_id} status change.")


# --- Signal for Delivery status changes affecting Order status ---
@receiver(post_save, sender=Delivery)
def update_order_status_from_delivery(sender, instance, created, **kwargs):
    # This signal triggers AFTER a Delivery object is saved.
    # We only want to act if the 'delivery_status' field of the Delivery has changed.
    # 'created' here means a new Delivery object was just made.
    if created or (kwargs.get('update_fields') and 'delivery_status' not in kwargs['update_fields']):
        return # Do not proceed if it's a new delivery or status wasn't updated

    delivery = instance
    order = delivery.order # Get the associated Order object

    # Store old status to check for changes and prevent unnecessary saves
    # Fetching the order instance from DB directly is important if other fields were changed
    # in the same save that triggered this signal, but the status was not.
    try:
        old_order_status = Order.objects.get(pk=order.pk).status
    except Order.DoesNotExist:
        old_order_status = None # Should not happen if order exists

    # Logic: Delivery status -> Order status
    if delivery.delivery_status == Delivery.DELIVERED:
        if old_order_status != "Completed": # Only update if not already Completed
            order.status = "Completed"
            # Set delivered_at for the Delivery when it truly becomes 'delivered'
            if not delivery.delivered_at: # Only set if not already set
                delivery.delivered_at = timezone.now()
                # Save delivery again with only the delivered_at field. This won't
                # re-trigger the post_save for delivery_status.
                delivery.save(update_fields=['delivered_at']) 
                logger.info(f"Delivery {delivery.id} delivered_at set to {delivery.delivered_at}.")
            
            # Save the order, specifying 'status' to prevent re-triggering signals unnecessarily
            order.save(update_fields=['status']) 
            logger.info(f"Order {order.order_id} status updated to 'Completed' based on Delivery {delivery.id} status.")

    elif delivery.delivery_status == Delivery.FAILED:
        # Example: If a delivery fails, the order status could be changed to 'Returned' or 'Canceled'
        if old_order_status not in ["Canceled", "Returned"]: # Avoid changing if already in a final state
            order.status = "Returned" # Or 'Canceled' depending on your business logic
            order.save(update_fields=['status'])
            logger.info(f"Order {order.order_id} status updated to 'Returned' based on Delivery {delivery.id} failure.")