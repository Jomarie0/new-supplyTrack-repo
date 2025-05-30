from django.shortcuts import render, get_object_or_404, redirect
from .models import Delivery
from apps.orders.models import Order, OrderItem # Make sure OrderItem is imported if you need to query it
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


# @staff_member_required
# def delivery_list(request):
#     deliveries = Delivery.objects.all().select_related('order', 'order__product')
#     all_orders = Order.objects.all()  # Fetch all orders for the dropdown
#     context = {
#         'deliveries': deliveries,
#         'all_orders': all_orders,
#     }
#     return render(request, 'delivery/delivery_list.html', context)

def delivery_list(request):
    deliveries = Delivery.objects.filter(is_archived=False) \
                                 .select_related('order', 'order__customer') \
                                 .prefetch_related('order__items__product_variant__product')
    # Explanation:
    # .select_related('order'): Gets the related Order object in the same query.
    # .select_related('order__customer'): Gets the related Customer (User) for that Order.
    # .prefetch_related('order__items__product_variant__product'):
    #   - 'order__items': Prefetches all OrderItems for each Order.
    #   - '__product_variant': Then prefetches the ProductVariant for each OrderItem.
    #   - '__product': And finally, prefetches the Product for each ProductVariant.
    # This efficiently fetches all necessary data for rendering order items.

    all_orders = Order.objects.all().select_related('customer') # Pre-fetch customer for order dropdown if needed
    
    return render(request, 'delivery/delivery_list.html', {
        'deliveries': deliveries,
        'all_orders': all_orders,
    })

def archive_list(request):
    deliveries = Delivery.objects.filter(is_archived=True) \
                                 .select_related('order', 'order__customer') \
                                 .prefetch_related('order__items__product_variant__product')
    return render(request, 'delivery/archive_list.html', {'deliveries': deliveries})


@csrf_exempt
@require_POST
def archive_deliveries(request):
    data = json.loads(request.body)
    ids = data.get('ids', [])
    Delivery.objects.filter(id__in=ids).update(is_archived=True)
    return JsonResponse({'success': True})

@csrf_exempt
@require_POST
def restore_deliveries(request):
    data = json.loads(request.body)
    ids = data.get('ids', [])
    Delivery.objects.filter(id__in=ids).update(is_archived=False)
    return JsonResponse({'success': True})

@csrf_exempt
@require_POST
def permanently_delete_deliveries(request):
    data = json.loads(request.body)
    ids = data.get('ids', [])
    Delivery.objects.filter(id__in=ids).delete()
    return JsonResponse({'success': True})

# @staff_member_required
@require_POST
def add_delivery(request):
    order_id = request.POST.get('order')
    delivery_status = request.POST.get('delivery_status')

    if order_id and delivery_status:
        try:
            order = Order.objects.get(pk=order_id)
            # You might want to prevent creating multiple deliveries for the same order
            if Delivery.objects.filter(order=order).exists():
                 messages.warning(request, f"Delivery already exists for Order {order.order_id}.")
            else:
                Delivery.objects.create(order=order, delivery_status=delivery_status)
                messages.success(request, f"Delivery created for Order {order.order_id}.")
            return redirect('delivery:delivery_list')
        except Order.DoesNotExist:
            messages.error(request, "Invalid Order selected.")
    else:
        messages.error(request, "Please select an Order and Delivery Status.")

    return redirect('delivery:delivery_list')

# @staff_member_required
def confirm_delivery(request, delivery_id):
    delivery = get_object_or_404(Delivery, pk=delivery_id)
    if delivery.delivery_status != 'delivered':
        delivery.delivery_status = 'delivered'
        delivery.save()
        messages.success(request, f"Delivery for Order {delivery.order.order_id} has been confirmed.")
    else:
        messages.info(request, f"Delivery for Order {delivery.order.order_id} was already confirmed.")
    return redirect('delivery:delivery_list')

