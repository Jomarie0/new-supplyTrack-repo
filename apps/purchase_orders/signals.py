from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import PurchaseOrder
from apps.inventory.models import Product, StockMovement

_previous_status = {}

@receiver(pre_save, sender=PurchaseOrder)
def store_initial_status(sender, instance, **kwargs):
    if instance.pk:  # Check if it's an existing instance (not new)
        try:
            _previous_status[instance.pk] = PurchaseOrder.objects.get(pk=instance.pk).status
        except PurchaseOrder.DoesNotExist:
            pass  # Handle case where the object might have been deleted

@receiver(post_save, sender=PurchaseOrder)
def update_inventory_on_purchase_order(sender, instance, created, **kwargs):
    if created:
        if instance.status == "Completed":
            product = instance.product
            product.stock_quantity += instance.quantity
            product.save()
            StockMovement.objects.create(
                product=product,
                movement_type='IN',
                quantity=instance.quantity
            )
    else:
        previous_status = _previous_status.pop(instance.pk, None)
        if previous_status != instance.status:
            if instance.status == "Completed":
                product = instance.product
                product.stock_quantity += instance.quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    movement_type='IN',
                    quantity=instance.quantity
                )
            elif instance.status == "Canceled" and previous_status == "Completed":
                product = instance.product
                product.stock_quantity -= instance.quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    movement_type='OUT',
                    quantity=instance.quantity
                )
            elif instance.status == "Pending" and previous_status == "Completed":
                product = instance.product
                product.stock_quantity -= instance.quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    movement_type='OUT',
                    quantity=instance.quantity
                )