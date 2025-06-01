# apps/purchasing/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import PurchaseOrder, PurchaseOrderItem # Import both models
from apps.inventory.models import Product, StockMovement # For stock updates
from decimal import Decimal # Ensure Decimal is imported
from datetime import timezone

# --- Signal for Stock Update when PurchaseOrderItem is Received ---
@receiver(post_save, sender=PurchaseOrderItem)
def update_stock_on_purchase_order_item_save(sender, instance, created, **kwargs):
    """
    Updates product stock when a PurchaseOrderItem is saved (especially when quantity_received changes).
    Also updates the parent PurchaseOrder's status based on item receipt.
    """
    # Only proceed if this is an update to an existing item, or a new item with quantity_received > 0
    if instance.pk: # Check if it's an existing item being updated
        try:
            # Fetch the old instance from the database to compare quantity_received
            old_instance = sender.objects.get(pk=instance.pk)
            old_quantity_received = old_instance.quantity_received
        except sender.DoesNotExist:
            old_quantity_received = 0 # Assume 0 for new items or if old instance not found

        # Calculate the net change in received quantity
        net_received_change = instance.quantity_received - old_quantity_received

        if net_received_change > 0: # If more items were received
            product_variant = instance.product_variant
            if product_variant:
                product_variant.stock += net_received_change
                product_variant.save()
                print(f"Stock increased for {product_variant.product.name} ({product_variant.id}): +{net_received_change}, new stock = {product_variant.stock}")
                StockMovement.objects.create(
                    product=product_variant.product, # Use base product for StockMovement
                    product_variant=product_variant, # Optionally record variant
                    movement_type='IN',
                    quantity=net_received_change,
                    reason=f"PO Receipt: {instance.purchase_order.purchase_order_id}"
                )
        elif net_received_change < 0: # If quantity received was reduced (e.g., error correction)
            product_variant = instance.product_variant
            if product_variant:
                # Ensure stock doesn't go negative if correcting an error
                quantity_to_deduct = abs(net_received_change)
                product_variant.stock -= quantity_to_deduct
                product_variant.save()
                print(f"Stock decreased for {product_variant.product.name} ({product_variant.id}): -{quantity_to_deduct}, new stock = {product_variant.stock}")
                StockMovement.objects.create(
                    product=product_variant.product,
                    product_variant=product_variant,
                    movement_type='OUT',
                    quantity=quantity_to_deduct,
                    reason=f"PO Receipt Correction: {instance.purchase_order.purchase_order_id}"
                )
    elif created and instance.quantity_received > 0: # For new items that are already partially/fully received
        product_variant = instance.product_variant
        if product_variant:
            product_variant.stock += instance.quantity_received
            product_variant.save()
            print(f"Stock increased for {product_variant.product.name} ({product_variant.id}): +{instance.quantity_received}, new stock = {product_variant.stock}")
            StockMovement.objects.create(
                product=product_variant.product,
                product_variant=product_variant,
                movement_type='IN',
                quantity=instance.quantity_received,
                reason=f"PO Receipt (New Item): {instance.purchase_order.purchase_order_id}"
            )

    # Update parent PurchaseOrder status based on item receipt
    purchase_order = instance.purchase_order
    total_ordered = sum(item.quantity_ordered for item in purchase_order.items.all())
    total_received = sum(item.quantity_received for item in purchase_order.items.all())

    if total_received == total_ordered and total_ordered > 0:
        if purchase_order.status != purchase_order.STATUS_RECEIVED:
            purchase_order.status = purchase_order.STATUS_RECEIVED
            purchase_order.received_date = timezone.now().date() # Set received date on PO
            purchase_order.save(update_fields=['status', 'received_date'])
            print(f"PO {purchase_order.purchase_order_id} status updated to RECEIVED.")
    elif total_received > 0 and total_received < total_ordered:
        if purchase_order.status != purchase_order.STATUS_PARTIALLY_RECEIVED:
            purchase_order.status = purchase_order.STATUS_PARTIALLY_RECEIVED
            purchase_order.save(update_fields=['status'])
            print(f"PO {purchase_order.purchase_order_id} status updated to PARTIALLY RECEIVED.")
    elif total_received == 0 and purchase_order.status not in [purchase_order.STATUS_DRAFT, purchase_order.STATUS_PENDING, purchase_order.STATUS_CANCELLED]:
        # If all received items are removed, revert status to ordered/pending
        purchase_order.status = purchase_order.STATUS_ORDERED # Or STATUS_PENDING, depending on your workflow
        purchase_order.received_date = None
        purchase_order.save(update_fields=['status', 'received_date'])
        print(f"PO {purchase_order.purchase_order_id} status reverted to ORDERED/PENDING.")


# --- Signal for Recalculating PO Total (already handled by save/delete methods on item) ---
# This signal is less critical if calculate_total_cost is called in save/delete of PurchaseOrderItem
# @receiver(post_save, sender=PurchaseOrder)
# def recalculate_po_total_on_po_save(sender, instance, created, **kwargs):
#     if not created: # Only for updates
#         instance.calculate_total_cost()

# --- Signal for handling PO cancellation ---
@receiver(post_save, sender=PurchaseOrder)
def handle_po_cancellation(sender, instance, created, **kwargs):
    # This signal needs to run after the PO is saved, but only if status changed
    # to cancelled from a state where stock might have been received.
    # To get the old status safely, we need to fetch it or use a pre_save handler.
    
    # SAFE WAY to get old status in post_save:
    old_status = None
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            old_status = old_instance.status
        except sender.DoesNotExist:
            pass # Object was just created or deleted before this signal

    if old_status != instance.status: # Only if status actually changed
        if instance.status == instance.STATUS_CANCELLED:
            # If PO is cancelled, and it was previously received (partially or fully),
            # you might need to reverse stock movements. This is complex.
            # For simplicity, let's assume cancellation means no stock was received,
            # or stock reversal is handled manually.
            # If you want to reverse stock from 'received' status upon cancellation:
            if old_status in [instance.STATUS_RECEIVED, instance.STATUS_PARTIALLY_RECEIVED]:
                print(f"PO {instance.purchase_order_id} cancelled. Reversing received stock...")
                for item in instance.items.all():
                    if item.quantity_received > 0:
                        product_variant = item.product_variant
                        if product_variant:
                            product_variant.stock -= item.quantity_received
                            product_variant.save()
                            StockMovement.objects.create(
                                product=product_variant.product,
                                product_variant=product_variant,
                                movement_type='OUT',
                                quantity=item.quantity_received,
                                reason=f"PO Cancellation: {instance.purchase_order_id}"
                            )
                            item.quantity_received = 0 # Reset received quantity on item
                            item.save(update_fields=['quantity_received']) # Save item to reflect reset


# --- Connect signals in apps.py (or __init__.py) ---
# In apps/purchasing/apps.py:
# class PurchasingConfig(AppConfig):
#     name = 'apps.purchasing'
#     def ready(self):
#         import apps.purchasing.signals # noqa