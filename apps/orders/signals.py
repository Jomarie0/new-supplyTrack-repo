import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order
from apps.inventory.models import Product, StockMovement
from apps.delivery.signals import delivery_confirmed  # Import the signal
from apps.delivery.models import Delivery

logger = logging.getLogger(__name__)
_previous_order_status = {}

@receiver(pre_save, sender=Order)
def store_initial_order_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            _previous_order_status[instance.pk] = Order.objects.get(pk=instance.pk).status
        except Order.DoesNotExist:
            pass

@receiver(post_save, sender=Order)
def update_inventory_on_order_change(sender, instance, created, **kwargs):
    product = instance.product
    quantity = instance.quantity
    current_status = instance.status

    if not created:
        previous_status = _previous_order_status.pop(instance.pk, None)

        if previous_status != current_status:
            # Pending to Canceled: No stock change (order was never completed)
            if previous_status == "Pending" and current_status == "Canceled":
                logger.info(f"Order {instance.order_id} changed from Pending to Canceled (no stock change).")

            # Pending to Completed: Decrease stock
            elif previous_status == "Pending" and current_status == "Completed":
                product.stock_quantity -= quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    movement_type='OUT',
                    quantity=quantity,
                    # reason=f"Order {instance.order_id} completed (from Pending)"
                )
                logger.info(f"Order {instance.order_id} marked as Completed from Pending. Stock decreased.")

            # Completed to Canceled: Increase stock
            elif previous_status == "Completed" and current_status == "Canceled":
                product.stock_quantity += quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    movement_type='IN',
                    quantity=quantity,
                    # reason=f"Order {instance.order_id} canceled (from Completed)"
                )
                logger.info(f"Order {instance.order_id} marked as Canceled from Completed. Stock increased.")

            # Completed to Pending: Increase stock
            elif previous_status == "Completed" and current_status == "Pending":
                product.stock_quantity += quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    movement_type='IN',
                    quantity=quantity,
                    # reason=f"Order {instance.order_id} changed from Completed to Pending"
                )
                logger.info(f"Order {instance.order_id} changed from Completed to Pending. Stock increased.")

            # Canceled to Pending: No stock change (order was never completed)
            elif previous_status == "Canceled" and current_status == "Pending":
                logger.info(f"Order {instance.order_id} changed from Canceled to Pending (no stock change).")

            # Canceled to Completed: Decrease stock (order is being reactivated and completed)
            elif previous_status == "Canceled" and current_status == "Completed":
                product.stock_quantity -= quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    movement_type='OUT',
                    quantity=quantity,
                    # reason=f"Order {instance.order_id} completed (from Canceled)"
                )
                logger.info(f"Order {instance.order_id} marked as Completed from Canceled. Stock decreased.")


@receiver(delivery_confirmed, sender='apps.delivery.models.Delivery')
def order_delivery_confirmed(sender, order, **kwargs):
    logger.info("order_delivery_confirmed signal receiver CALLED!")
    logger.info(f"Delivery confirmed for Order: {order.order_id}. Updating order status to 'Completed'.")
    order.status = 'Completed'
    order.save()
    logger.info(f"Order: {order.order_id} status AFTER SAVE: {order.status}")  # Added this
    logger.info(f"Order: {order.order_id} status updated to 'Completed'. Post-save signal will now handle inventory.")

@receiver(post_save, sender=Order)
def create_delivery_on_order_creation(sender, instance, created, **kwargs):
    if created:
        Delivery.objects.create(order=instance)
        logger.info(f"Delivery record created for new Order: {instance.order_id}")
