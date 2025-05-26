# inventory/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Product, DemandCheckLog, StockMovement
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from datetime import timedelta
from .views import product_forecast_api

@receiver(post_save, sender=DemandCheckLog)
def send_restock_notification(sender, instance, created, **kwargs):
    """
    Send real-time notification when a new restock log is created
    and restock is needed.
    """
    if created and instance.restock_needed:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "notifications",
                {
                    "type": "restock_notification",
                    "message": {
                        "id": instance.id,
                        "product_name": instance.product.name,
                        "product_id": instance.product.product_id,
                        "forecasted_quantity": instance.forecasted_quantity,
                        "current_stock": instance.current_stock,
                        "message": f"Restock needed for {instance.product.name}. Current: {instance.current_stock}, Forecasted demand: {instance.forecasted_quantity}",
                        "timestamp": instance.checked_at.isoformat(),
                        "type": "restock_alert"
                    }
                }
            )

@receiver(post_save, sender=StockMovement)
def update_restock_logs_on_stock_change(sender, instance, created, **kwargs):
    """
    Update restock logs when stock is increased (movement_type == "IN").
    Resolve logs if stock now covers forecasted quantity.
    """
    if created and instance.movement_type == "IN":
        product = instance.product
        pending_logs = DemandCheckLog.objects.filter(
            product=product,
            restock_needed=True,
            is_deleted=False
        )

        for log in pending_logs:
            log.current_stock = product.stock_quantity
            if product.stock_quantity >= log.forecasted_quantity:
                # Soft delete (mark resolved)
                log.is_deleted = True
                log.save(update_fields=['is_deleted'])
                product_forecast_api()

                # Send resolution notification
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        "notifications",
                        {
                            "type": "restock_resolved",
                            "message": {
                                "id": log.id,
                                "product_name": log.product.name,
                                "message": f"Restock issue resolved for {log.product.name}",
                                "type": "restock_resolved"
                            }
                        }
                    )
            else:
                log.save(update_fields=['current_stock'])

@receiver(post_save, sender=Product)
def update_restock_logs_on_product_save(sender, instance, created, **kwargs):
    """
    Update restock logs when product stock is updated directly (not just through StockMovement).
    """
    if created:
        # Newly created product — no need to update logs yet
        return

    pending_logs = DemandCheckLog.objects.filter(
        product=instance,
        restock_needed=True,
        is_deleted=False
    )

    for log in pending_logs:
        old_stock = log.current_stock
        new_stock = instance.stock_quantity

        if old_stock != new_stock:
            log.current_stock = new_stock
            if new_stock >= log.forecasted_quantity:
                # Soft delete (mark resolved)
                log.is_deleted = True
                log.save(update_fields=['is_deleted'])

                # Send resolution notification
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        "notifications",
                        {
                            "type": "restock_resolved",
                            "message": {
                                "id": log.id,
                                "product_name": log.product.name,
                                "message": f"Restock issue resolved for {log.product.name}",
                                "type": "restock_resolved"
                            }
                        }
                    )
            else:
                log.save(update_fields=['current_stock'])

@receiver(pre_save, sender=Product)
def check_stock_threshold(sender, instance, **kwargs):
    """
    Before saving a product, check if stock dropped below reorder level.
    If so, create a restock log unless one exists in last 24 hours.
    """
    if not instance.pk:
        # New product, no old stock to compare
        return

    try:
        old_instance = Product.objects.get(pk=instance.pk)
    except Product.DoesNotExist:
        return

    # Check if stock crosses threshold downward
    if (old_instance.stock_quantity > old_instance.reorder_level and 
        instance.stock_quantity <= instance.reorder_level):

        # Check if a recent log exists (last 24 hours)
        recent_log = DemandCheckLog.objects.filter(
            product=instance,
            restock_needed=True,
            is_deleted=False,
            checked_at__gte=timezone.now() - timedelta(seconds=3)
        ).first()

        if not recent_log:
            # Create new restock log with suggested forecast quantity
            DemandCheckLog.objects.create(
                product=instance,
                forecasted_quantity=instance.reorder_level + 50,  # You can adjust this logic
                current_stock=instance.stock_quantity,
                restock_needed=True
            )
