from django.shortcuts import render, get_object_or_404, redirect
from .models import Delivery
from apps.orders.models import Order  # Import the Order model
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.views.decorators.http import require_POST

# @staff_member_required
def delivery_list(request):
    deliveries = Delivery.objects.all().select_related('order', 'order__product')
    all_orders = Order.objects.all()  # Fetch all orders for the dropdown
    context = {
        'deliveries': deliveries,
        'all_orders': all_orders,
    }
    return render(request, 'delivery/delivery_list.html', context)

# @staff_member_required
@require_POST
def add_delivery(request):
    order_id = request.POST.get('order')
    delivery_status = request.POST.get('delivery_status')

    if order_id and delivery_status:
        try:
            order = Order.objects.get(pk=order_id)
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