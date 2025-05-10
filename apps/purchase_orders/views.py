from django.shortcuts import render, redirect, get_object_or_404
from .models import PurchaseOrder
from .forms import PurchaseOrderForm
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse

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

    purchase_orders = PurchaseOrder.objects.all()
    context = {
        'purchase_orders': purchase_orders,
        'form': form,
    }
    return render(request, 'purchase_orders/purchase_order_list.html', context)

@csrf_exempt
def delete_purchase_orders(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            po_ids_to_delete = data.get('ids', [])
            PurchaseOrder.objects.filter(purchase_order_id__in=po_ids_to_delete).delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})