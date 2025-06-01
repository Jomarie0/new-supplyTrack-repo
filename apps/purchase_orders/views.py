# apps/purchasing/views.py

from django.shortcuts import render, redirect, get_object_or_404
from .models import PurchaseOrder, PurchaseOrderItem # Import PurchaseOrderItem
from .forms import PurchaseOrderForm # Your form for the modal
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Prefetch # For optimizing queries
from apps.suppliers.models import Supplier
from django.core.mail import send_mail
from django.conf import settings

from django.contrib.auth.decorators import login_required

def send_purchase_order_email(purchase_order):
    """
    Sends an email to the supplier with purchase order details
    when the status is set to 'pending'.
    """

    supplier_email = purchase_order.supplier.email
    if not supplier_email:
        print(f"No email found for supplier {purchase_order.supplier.name}")
        return

    subject = f"Purchase Order {purchase_order.purchase_order_id} - Pending Confirmation"
    
    # Compose message without prices, include notes field for product + quantity info
    message = (
        f"Dear {purchase_order.supplier.name},\n\n"
        f"You have a new purchase order pending confirmation.\n\n"
        f"Purchase Order ID: {purchase_order.purchase_order_id}\n"
        f"Order Date: {purchase_order.order_date.strftime('%Y-%m-%d %H:%M')}\n"
        f"Expected Delivery Date: {purchase_order.expected_delivery_date or 'Not specified'}\n"
        f"Notes (Products and Quantities):\n{purchase_order.notes or 'No details provided.'}\n\n"
        f"Please confirm the order at your earliest convenience.\n\n"
        f"Best regards,\nSupplyTrack Team"
    )
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,  # e.g. 'SupplyTrack <danegela13@gmail.com>'
        recipient_list=[supplier_email],
        fail_silently=False,
    )

@login_required
def purchase_order_details_api(request, purchase_order_id):
    purchase_order = get_object_or_404(PurchaseOrder, purchase_order_id=purchase_order_id)
    
    items = purchase_order.items.select_related('product_variant__product').all()
    items_list = []
    for item in items:
        items_list.append({
            'product_name': item.product_variant.product.name if item.product_variant else item.product_name_text,
            'description': item.description,
            'quantity_ordered': item.quantity_ordered,
            'unit_cost': str(item.unit_cost),
            'total_price': str(item.total_price),
        })

    data = {
        'purchase_order_id': purchase_order.purchase_order_id,
        'supplier_name': purchase_order.supplier.name,
        'order_date': purchase_order.order_date.strftime('%Y-%m-%d %H:%M'),
        'expected_delivery_date': purchase_order.expected_delivery_date.strftime('%Y-%m-%d') if purchase_order.expected_delivery_date else None,
        'notes': purchase_order.notes,
        'total_cost': str(purchase_order.total_cost),
        'items': items_list,
    }
    return JsonResponse(data)

# @csrf_exempt # Consider removing this if you implement proper CSRF in JS for the modal form
def purchase_order_list(request):
    purchase_orders = PurchaseOrder.objects.filter(is_deleted=False).order_by('-order_date')
    form = PurchaseOrderForm()

    if request.method == 'POST':
        purchase_order_id = request.POST.get('purchase_order_id')
        if purchase_order_id:
            instance = get_object_or_404(PurchaseOrder, purchase_order_id=purchase_order_id)
            old_status = instance.status
            form = PurchaseOrderForm(request.POST, instance=instance)
        else:
            form = PurchaseOrderForm(request.POST)
            old_status = None

        if form.is_valid():
            purchase_order = form.save(commit=False)
            new_status = form.cleaned_data.get('status')
            purchase_order.save()
            
            # Check if status changed to 'pending' from something else (or new PO)
            if new_status == PurchaseOrder.STATUS_PENDING and old_status != PurchaseOrder.STATUS_PENDING:
                send_purchase_order_email(purchase_order)
            
            messages.success(request, "Purchase Order saved successfully!")
            return redirect('PO:purchase_order_list')
        else:
            messages.error(request, "Error saving Purchase Order. Please check the form.")
            print("Form errors:", form.errors)

    context = {
        'purchase_orders': purchase_orders,
        'form': form,
    }
    return render(request, 'purchase_orders/purchase_order_list.html', context)



def archived_purchase_orders(request):
    archived_orders = PurchaseOrder.objects.filter(is_deleted=True)
    context = {
        'archived_orders': archived_orders,
        'page_title': 'Archived Purchase Orders',
    }
    return render(request, 'purchase_orders/archived_purchase_orders.html', context)

@csrf_exempt # WARNING: For testing only! Use proper CSRF handling in production.
def delete_purchase_orders(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            po_ids_to_delete = data.get('ids', [])
            orders = PurchaseOrder.objects.filter(purchase_order_id__in=po_ids_to_delete)
            for order in orders:
                order.delete()  # This uses your soft-delete logic
            return JsonResponse({'success': True, 'message': f"{orders.count()} POs soft-deleted."})
        except Exception as e:
            print(f"Error deleting POs: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt # WARNING: For testing only!
def restore_purchase_orders(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            restored_count = PurchaseOrder.objects.filter(purchase_order_id__in=ids).update(is_deleted=False, deleted_at=None)
            return JsonResponse({'success': True, 'message': f"{restored_count} POs restored."})
        except Exception as e:
            print(f"Error restoring POs: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt # WARNING: For testing only!
def permanently_delete_purchase_orders(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            deleted_count = PurchaseOrder.objects.filter(purchase_order_id__in=ids).delete()
            return JsonResponse({'success': True, 'message': f"{deleted_count[0]} POs permanently deleted."})
        except Exception as e:
            print(f"Error permanently deleting POs: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})