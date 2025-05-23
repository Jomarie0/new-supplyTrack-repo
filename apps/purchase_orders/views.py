from django.shortcuts import render, redirect, get_object_or_404
from .models import PurchaseOrder
from .forms import PurchaseOrderForm
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from django.utils.timezone import now

def purchase_order_list(request):
    form = PurchaseOrderForm()

    if request.method == 'POST':
        purchase_order_id = request.POST.get('purchase_order_id')

        if purchase_order_id:
            # Update existing purchase order
            instance = get_object_or_404(PurchaseOrder, purchase_order_id=purchase_order_id)
            form = PurchaseOrderForm(request.POST, instance=instance)
        else:
            # Create new purchase order
            form = PurchaseOrderForm(request.POST)

        if form.is_valid():
            # Check if it's an update and the status has changed
            if purchase_order_id:
                previous_status = PurchaseOrder.objects.get(purchase_order_id=purchase_order_id).status
                current_status = form.cleaned_data.get('status')

                if previous_status != current_status:
                    # Trigger the signal for stock update when the status changes
                    form.save()
                    return redirect('PO:purchase_order_list')
                else:
                    # If it's an update but the status hasn't changed, just save
                    form.save()
                    return redirect('PO:purchase_order_list')
            else:
                # For a new purchase order, just save it
                form.save()
                return redirect('PO:purchase_order_list')

    purchase_orders = PurchaseOrder.objects.filter(is_deleted=False)

    context = {
        'purchase_orders': purchase_orders,
        'form': form,
    }
    return render(request, 'purchase_orders/purchase_order_list.html', context)

def archived_purchase_orders(request):
    archived_orders = PurchaseOrder.objects.filter(is_deleted=True)
    return render(request, 'purchase_orders/archived_purchase_orders.html', {'archived_orders': archived_orders})

# @csrf_exempt
# def delete_purchase_orders(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             po_ids_to_delete = data.get('ids', [])
#             PurchaseOrder.objects.filter(purchase_order_id__in=po_ids_to_delete).delete()
#             return JsonResponse({'success': True})
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': str(e)})
#     return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def delete_purchase_orders(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            po_ids_to_delete = data.get('ids', [])
            orders = PurchaseOrder.objects.filter(purchase_order_id__in=po_ids_to_delete)
            for order in orders:
                order.delete()  # This uses your soft-delete logic
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def restore_purchase_orders(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])
        PurchaseOrder.objects.filter(purchase_order_id__in=ids).update(is_deleted=False, deleted_at=None)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@csrf_exempt
def permanently_delete_purchase_orders(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])
        PurchaseOrder.objects.filter(purchase_order_id__in=ids).delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})