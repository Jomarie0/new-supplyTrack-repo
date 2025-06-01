# apps/orders/signals.py

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order, OrderItem # Make sure OrderItem is correctly used if needed
from apps.inventory.models import Product, StockMovement
# from apps.delivery.signals import delivery_confirmed # REMOVE this line
from apps.delivery.models import Delivery # Keep this if you use Delivery directly here (e.g., for creation)

logger = logging.getLogger(__name__)

# This is still useful to track status changes for logging/debugging
_previous_order_status = {}

@receiver(pre_save, sender=Order)
def store_initial_order_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            _previous_order_status[instance.pk] = Order.objects.get(pk=instance.pk).status
        except Order.DoesNotExist:
            pass # Object is new, no previous status to store

@receiver(post_save, sender=Order)
def manage_order_status_changes(sender, instance, created, **kwargs):
    current_status = instance.status

    if not created:
        previous_status = _previous_order_status.pop(instance.pk, None)

        if previous_status != current_status:
            logger.info(f"Order {instance.order_id} status changed from '{previous_status}' to '{current_status}'.")

            # Handle stock adjustments based on status changes if needed
            # IMPORTANT: We are deducting stock at checkout. This signal handles *reversals* or *adjustments*.
            
            # If status changes from 'Processing' or 'Shipped' to 'Canceled' or 'Returned':
            # Re-add stock to inventory.
            if previous_status in ["Processing", "Shipped"] and current_status in ["Canceled", "Returned"]:
                for item in instance.items.all():
                    # Ensure you're working with the correct product variant's stock if applicable
                    # Assuming item.product_variant.product gives you the main product for stock tracking
                    product = item.product_variant.product 
                    product.stock_quantity += item.quantity
                    product.save()
                    StockMovement.objects.create(
                        product=product,
                        movement_type='IN',
                        quantity=item.quantity,
                        # reason=f"Order {instance.order_id} {current_status} - stock returned"
                    )
                logger.info(f"Stock for Order {instance.order_id} has been restored due to status change to '{current_status}'.")
            
            # If status changes from 'Canceled' or 'Returned' back to 'Processing' or 'Shipped':
            # Deduct stock again (e.g., if an order is reactivated). This requires careful stock checks.
            elif previous_status in ["Canceled", "Returned"] and current_status in ["Processing", "Shipped"]:
                for item in instance.items.all():
                    # Ensure you're working with the correct product variant's stock if applicable
                    product = item.product_variant.product
                    if product.stock_quantity >= item.quantity: # Only deduct if enough stock
                        product.stock_quantity -= item.quantity
                        product.save()
                        StockMovement.objects.create(
                            product=product,
                            movement_type='OUT',
                            quantity=item.quantity,
                            # reason=f"Order {instance.order_id} reactivated - stock deducted"
                        )
                        logger.info(f"Stock for Order {instance.order_id} deducted due to status change to '{current_status}'.")
                    else:
                        logger.warning(f"Failed to deduct stock for {product.name} (Order {instance.order_id}) on status change to '{current_status}'. Insufficient stock.")
                        # Consider setting order item status to 'backordered' or similar here
    elif created:
        # For newly created orders, stock has already been deducted in checkout_view.
        # This signal now primarily focuses on creating the Delivery record, handled by `create_delivery_on_order_creation`.
        logger.info(f"New Order {instance.order_id} created with status '{instance.status}'.")


# This signal ensures a Delivery record is created automatically for every new Order
@receiver(post_save, sender=Order)
def create_delivery_on_order_creation(sender, instance, created, **kwargs):
    if created: # Only for newly created Order instances
        # Check if a Delivery object already exists for this order (shouldn't if 'created' is true, but good practice)
        if not hasattr(instance, 'delivery'): # Uses the related_name 'delivery' from OneToOneField
            # Create a new Delivery instance linked to this order
            # The default status of Delivery will be PENDING_DISPATCH as per your model
            Delivery.objects.create(order=instance)
            logger.info(f"Delivery record created for new Order: {instance.order_id}")
        else:
            logger.info(f"Delivery record already exists for Order: {instance.order_id}, skipping creation.")