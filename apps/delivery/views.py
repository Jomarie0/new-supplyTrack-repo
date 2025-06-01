from django.shortcuts import render, get_object_or_404, redirect
from .models import Delivery
from apps.orders.models import Order, OrderItem # Make sure OrderItem is imported if you need to query it
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from django.db.models import Prefetch

# from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

def send_delivery_status_update_email(delivery):
    customer = delivery.order.customer
    if not customer or not customer.email:
        print(f"No email found for customer in Order {delivery.order.order_id}")
        return

    # Prepare order items details for plain text
    items_details = "Items in Your Order:\n"
    for item in delivery.order.items.all():
        product_name = item.product_variant.product.name if item.product_variant else "Unknown Product"
        sku = item.product_variant.sku if item.product_variant else "N/A"
        quantity = item.quantity
        unit_price = item.price_at_order
        subtotal = unit_price * quantity
        items_details += (
            f"{product_name} SKU: {sku}\n"
            f"₱{unit_price:.2f} x {quantity} = ₱{subtotal:.2f}\n\n"  # Extra newline for spacing
        )

    total_cost = delivery.order.get_total_cost()

    subject = f"Delivery Status Update for Order {delivery.order.order_id}"
    
    # Plain text content
    text_content = (
        f"Dear {customer.username},\n\n"
        f"The status of your delivery for Order #{delivery.order.order_id} has been updated to: {delivery.get_delivery_status_display()}.\n\n"
        f"Order Date: {delivery.order.order_date.strftime('%Y-%m-%d %H:%M')}\n"
        f"Current Delivery Status: {delivery.get_delivery_status_display()}\n\n"
        f"{items_details}"
        f"Total: ₱{total_cost:.2f}\n\n"
        "Thank you for choosing SupplyTrack.\n\n"
        "Best regards,\n"
        "SupplyTrack Team"
    )

    # HTML content
    html_content = f"""
    <p>Dear {customer.username},</p>
    <p>The status of your delivery for Order #{delivery.order.order_id} has been updated to: <strong>{delivery.get_delivery_status_display()}</strong>.</p>
    <p>Order Date: {delivery.order.order_date.strftime('%Y-%m-%d %H:%M')}</p>
    <p>Current Delivery Status: {delivery.get_delivery_status_display()}</p>
    <p><strong>Items in Your Order:</strong><br>
    {"<br>".join([
        f"{item.product_variant.product.name if item.product_variant else 'Unknown Product'} SKU: {item.product_variant.sku if item.product_variant else 'N/A'}<br>"
        f"₱{item.price_at_order:.2f} x {item.quantity} = ₱{item.price_at_order * item.quantity:.2f}<br><br>"
        for item in delivery.order.items.all()
    ])}</p>
    <p><strong>Total: ₱{total_cost:.2f}</strong></p>
    <p>Thank you for choosing SupplyTrack.</p>
    <p>Best regards,<br>SupplyTrack Team</p>
    """

    email = EmailMultiAlternatives(subject, text_content, 'SupplyTrack <danegela13@gmail.com>', [customer.email])
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


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
    deliveries_queryset = Delivery.objects.filter(is_archived=False) \
                                 .select_related('order__customer') \
                                 .prefetch_related(
                                     # Ensure product details are prefetched for JSON serialization
                                     Prefetch('order__items', queryset=OrderItem.objects.select_related('product_variant__product'))
                                 ) \
                                 .order_by('-delivered_at') # Or '-order__order_date'

    # Serialize the deliveries queryset to JSON
    # We need to manually construct the data because serialize('json') doesn't handle related objects
    # and custom methods (like get_total_cost) very well for complex nested structures.

    deliveries_data = []
    for delivery in deliveries_queryset:
        order_data = None
        if delivery.order:
            items_data = []
            for item in delivery.order.items.all():
                items_data.append({
                    'id': item.id,
                    'quantity': item.quantity,
                    'price_at_order': float(item.price_at_order),
                    'item_total': float(item.item_total),
                    'product_variant': {
                        'id': item.product_variant.id,
                        'size': item.product_variant.size,
                        'color': item.product_variant.color,
                        'product': {
                            'id': item.product_variant.product.id,
                            'name': item.product_variant.product.name,
                        } if item.product_variant.product else None,
                    } if item.product_variant else None,
                })
            order_data = {
                'id': delivery.order.id,
                'order_id': delivery.order.order_id,
                'customer': {
                    'id': delivery.order.customer.id,
                    'username': delivery.order.customer.username,
                } if delivery.order.customer else None,
                'total_cost': float(delivery.order.get_total_cost()), # Ensure this is a float
                'items': items_data,
            }

        deliveries_data.append({
            'id': delivery.id,
            'delivery_status': delivery.delivery_status,
            'delivered_at': delivery.delivered_at.isoformat() if delivery.delivered_at else None,
            'order': order_data,
        })

    # Convert the Python list of dicts to a JSON string
    deliveries_json = json.dumps(deliveries_data)

    all_orders = Order.objects.all().select_related('customer') # For the Add Delivery modal dropdown
    
    return render(request, 'delivery/delivery_list.html', {
        'deliveries': deliveries_queryset, # Still pass the queryset for potential direct Django use if needed elsewhere
        'all_orders': all_orders,
        'deliveries_json': deliveries_json, # Pass the JSON string to the template
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

@require_POST
@csrf_exempt # WARNING: For testing only! Remove in production and use proper CSRF handling.
def update_delivery_status_view(request, delivery_id):
    """
    Updates the status of a specific delivery.
    Expects a POST request with JSON body: {"status": "new_status_value"}
    """
    try:
        # 1. Parse the JSON request body
        data = json.loads(request.body)
        new_status = data.get('status')

        if not new_status:
            return JsonResponse({'success': False, 'error': 'New status not provided.'}, status=400)

        # 2. Retrieve the Delivery object
        delivery = get_object_or_404(Delivery, id=delivery_id)

        # 3. Validate the new status against allowed choices
        valid_statuses = [choice[0] for choice in Delivery.DELIVERY_STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': f'Invalid status provided: {new_status}'}, status=400)

        # 4. Update the delivery status
        delivery.delivery_status = new_status
        
        # The `save` method of your Delivery model now handles `delivered_at`
        # and the `delivery_confirmed` signal based on status change, which is great!
        delivery.save() 

        # Optional: You might want to update the related Order's status as well.
        # This can also be handled by a signal if preferred, or directly here.
        # Example: if delivery is delivered, mark order as completed.
        if new_status == Delivery.DELIVERED:
            order = delivery.order
            if order.status != 'completed': # Assuming 'completed' is a status in your Order model
                order.status = 'completed'
                order.save()
        # You could also have logic for other states, e.g., if delivery failed, update order status to 'failed_delivery'

        # Send email notification to customer on status update
        send_delivery_status_update_email(delivery)
        
        return JsonResponse({'success': True, 'message': 'Delivery status updated successfully.'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON in request body.'}, status=400)
    except Delivery.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Delivery not found.'}, status=404)
    except Exception as e:
        # Log the full error for debugging
        print(f"An unexpected error occurred in update_delivery_status_view: {e}")
        return JsonResponse({'success': False, 'error': f'An unexpected error occurred: {str(e)}'}, status=500)

