from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Order
from .forms import OrderForm
from apps.inventory.models import Product
from apps.orders.models import Order
from apps.users.models import User

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import random
import string
from django.utils import timezone
from datetime import datetime

from django.utils.timezone import now
from django.db.models.functions import TruncMonth
from django.db.models import Sum
# from sklearn.linear_model import LinearRegression
# import pandas as pd
# import numpy as np
from datetime import timedelta
from django.db.models import F, Sum, ExpressionWrapper, FloatField ,DecimalField
from apps.inventory.models import DemandCheckLog
from django.contrib import messages
from .models import Order, OrderItem # Import OrderItem now
from .forms import OrderForm, CheckoutForm # Import CheckoutForm
from apps.inventory.models import Product, StockMovement # Import StockMovement
from apps.store.models import Cart, CartItem, ProductVariant # Import Cart and CartItem
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction # For atomic operations
from django.utils import timezone
from decimal import Decimal
from django.db.models import Prefetch # Import Prefetch for efficiency
from django.db.models import Q

from django.core.mail import send_mail
from django.conf import settings

def send_order_confirmation_email_to_customer(order):
    customer_email = order.customer.email if order.customer else None
    if not customer_email:
        print("No customer email found for order", order.order_id)
        return

    # Prepare items details as per your format
    items = order.items.all()  # Assuming related_name='items' on OrderItem FK

    items_details = "Items in Your Order:\n"
    overall_total = 0

    for item in items:
        product_name = item.product_variant.product.name if item.product_variant else "N/A"
        sku = item.product_variant.sku if item.product_variant else "N/A"
        qty = item.quantity
        unit_price = item.price_at_order
        line_total = qty * unit_price
        overall_total += line_total

        items_details += (
            f"{product_name} SKU: {sku}\n"
            f"₱ {unit_price:.2f} x {qty} = ₱{line_total:.2f}\n"
        )

    message = (
        f"Dear {order.customer.username},\n\n"
        f"Thank you for your order #{order.order_id}.\n"
        f"Order Date: {order.order_date.strftime('%Y-%m-%d %H:%M')}\n"
        f"Expected Delivery Date: {order.expected_delivery_date}\n"
        f"Payment Method: {order.payment_method}\n\n"
        f"{items_details}"
        f"Total: ₱{overall_total:.2f}\n\n"
        "We are processing your order and will notify you once it ships.\n\n"
        "Best regards,\n"
        "SupplyTrack Team"
    )

    send_mail(
        subject=f"Order Confirmation - {order.order_id}",
        message=message,
        from_email='SupplyTrack <danegela13@gmail.com>',  # Your working sender email here
        recipient_list=[customer_email],
        fail_silently=False,
    )

def generate_unique_order_id():
    from .models import Order
    while True:
        order_id = 'ORD' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Order.objects.filter(order_id=order_id).exists():
            return order_id

@login_required
def order_list(request):
    form = OrderForm()

    if request.method == 'POST':
        order_id_from_form = request.POST.get('order_id') # This is the string ID
        
        # Determine if it's an update or new creation based on the hidden-order-id
        if order_id_from_form: # If order_id_from_form is present, it's an update
            # Find the existing order using its order_id string
            existing_order = get_object_or_404(Order, order_id=order_id_from_form)
            form = OrderForm(request.POST, instance=existing_order)
        else: # Otherwise, it's a new order
            form = OrderForm(request.POST)

        if form.is_valid():
            order = form.save(commit=False)
            if not order.order_id:
                order.order_id = generate_unique_order_id() # Ensure a unique ID for new orders
            order.is_deleted = False # Ensure it's not marked as deleted upon creation/update
            order.save()
            messages.success(request, f"Order {order.order_id} successfully saved!")
            return redirect('orders:order_list')
        else:
            messages.error(request, "Error saving order. Please check the form.")
            # Print form errors to console for debugging
            print("Form errors:", form.errors)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            for error in form.non_field_errors():
                messages.error(request, f"Error: {error}")
    
    # --- Querysets with prefetching for display ---
    orders_queryset = Order.objects.filter(is_deleted=False) \
                                 .select_related('customer') \
                                 .prefetch_related(
                                     Prefetch('items', queryset=OrderItem.objects.select_related('product_variant__product'))
                                 ) \
                                 .order_by('-order_date')

    # Filter orders by status
    # Make sure 'Pending' matches your ORDER_STATUS_CHOICES key exactly
    pending_orders_queryset = orders_queryset.filter(status='Pending')
    shipped_orders_queryset = orders_queryset.filter(status='Shipped')
    canceled_orders_queryset = orders_queryset.filter(status='Canceled')
    processing_orders_queryset = orders_queryset.filter(status='Processing')
    completed_orders_queryset = orders_queryset.filter(status='Completed')
    returned_orders_queryset = orders_queryset.filter(status='Returned')

    # --- Calculate Counts for each status ---
    # .count() on a queryset executes a COUNT(*) query efficiently
    all_orders_count = orders_queryset.count()
    pending_count = pending_orders_queryset.count()
    shipped_count = shipped_orders_queryset.count()
    canceled_count = canceled_orders_queryset.count()
    processing_count = processing_orders_queryset.count()
    completed_count = completed_orders_queryset.count()
    returned_count = returned_orders_queryset.count()
    # --- End counts ---

    context = {
        'orders': orders_queryset, # All non-deleted orders
        'pending_orders': pending_orders_queryset,
        'shipped_orders': shipped_orders_queryset,
        'canceled_orders': canceled_orders_queryset,
        'processing_orders': processing_orders_queryset,
        'completed_orders': completed_orders_queryset,
        'returned_orders': returned_orders_queryset,
        'order_statuses_choices': Order.ORDER_STATUS_CHOICES, # Still needed for tab button names

        # --- Add counts to context ---
        'all_orders_count': all_orders_count,
        'pending_count': pending_count,
        'shipped_count': shipped_count,
        'canceled_count': canceled_count,
        'processing_count': processing_count,
        'completed_count': completed_count,
        'returned_count': returned_count,
        # --- End counts ---
        'form': form,
        'products': Product.objects.filter(is_deleted=False), # Assuming products are needed for the form
        'customers': User.objects.all() # Assuming customers are needed for the form choices
    }
    return render(request, 'orders/orders_list.html', context)


def archived_orders(request):
    archived = Order.objects.filter(is_deleted=True)
    return render(request, 'orders/archived_orders.html', {'archived_orders': archived})

# @csrf_exempt
# def delete_orders(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             order_ids_to_delete = data.get('ids', [])
#             Order.objects.filter(order_id__in=order_ids_to_delete).delete()
#             return JsonResponse({'success': True})
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': str(e)})
#     return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def delete_orders(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_ids_to_delete = data.get('ids', [])
            for order in Order.objects.filter(order_id__in=order_ids_to_delete):
                order.delete()  # calls soft delete
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def permanently_delete_orders(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_ids = data.get('ids', [])
            Order.objects.filter(order_id__in=order_ids, is_deleted=True).delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def restore_orders(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_ids = data.get('ids', [])
            for order in Order.objects.filter(order_id__in=order_ids, is_deleted=True):
                order.restore()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def get_or_create_cart(request):
    from apps.store.models import Cart
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        # If an anonymous cart exists with this session, merge it
        if request.session.session_key:
            try:
                anon_cart = Cart.objects.get(session_key=request.session.session_key, user__isnull=True)
                if anon_cart != cart: # Avoid merging cart with itself
                    for item in anon_cart.items.all():
                        existing_item = cart.items.filter(product_variant=item.product_variant).first()
                        if existing_item:
                            existing_item.quantity += item.quantity
                            existing_item.save()
                        else:
                            item.cart = cart
                            item.save()
                    anon_cart.delete() # Delete the old anonymous cart
                del request.session['session_key'] # Clear the session key after merging
            except Cart.DoesNotExist:
                pass # No anonymous cart to merge
    else:
        # For anonymous users, use session_key
        if not request.session.session_key:
            request.session.save() # Ensure a session key exists
        cart, created = Cart.objects.get_or_create(session_key=request.session.session_key, user__isnull=True)
    return cart


# --- NEW Checkout Views ---

from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required # Make sure this is imported if you uncomment @login_required

from .models import Order, OrderItem # Ensure Order and OrderItem are imported
from .forms import CheckoutForm # Ensure CheckoutForm is imported
# Assuming get_or_create_cart and StockMovement are also imported/defined

# @login_required # Uncomment this if checkout requires login
@transaction.atomic # Ensure all operations complete or none do
def checkout_view(request):
    cart = get_or_create_cart(request)
    
    print(f"DEBUG: Cart exists: {cart.id}")


    if request.method == 'POST':
        form = CheckoutForm(request.POST, request=request)
        print("DEBUG: Received POST request.")
        if form.is_valid():
            print("DEBUG: Form is VALID. Proceeding with order creation.")
            order = Order(
                customer=request.user if request.user.is_authenticated else None,
                payment_method=form.cleaned_data['payment_method'],
                expected_delivery_date=form.cleaned_data['expected_delivery_date'],
                status='Processing'
            )
            order.shipping_address = form.cleaned_data['shipping_address']
            order.billing_address = form.cleaned_data['billing_address']
            
            order.save() # Save the order to get its ID
            print(f"DEBUG: Order {order.order_id} saved with ID: {order.id}")

            # Transfer items from Cart to OrderItems
            cart_items_count = cart.items.count()
            print(f"DEBUG: Cart has {cart_items_count} items to transfer.")

            if cart_items_count > 0:
                for cart_item in cart.items.all():
                    print(f"DEBUG: Creating OrderItem for product variant: {cart_item.product_variant.id}, qty: {cart_item.quantity}")
                    # Ensure product_variant.price and product_variant.product.price exist and are Decimal
                    price_to_use = cart_item.product_variant.price
                    if not price_to_use:
                        price_to_use = cart_item.product_variant.product.price # Fallback to base product price
                    if not price_to_use: # Final fallback if both are missing
                        price_to_use = Decimal('0.00')
                    
                    print(f"DEBUG: Price for order item: {price_to_use}")

                    OrderItem.objects.create(
                        order=order,
                        product_variant=cart_item.product_variant,
                        quantity=cart_item.quantity,
                        price_at_order=price_to_use # Use the robustly checked price
                    )
                    print(f"DEBUG: OrderItem created for {cart_item.product_variant.product.name}.")

                    # Deduct stock immediately
                    product = cart_item.product_variant.product
                    product.stock_quantity -= cart_item.quantity
                    product.save()
                    print(f"DEBUG: Stock for {product.name} deducted. New stock: {product.stock_quantity}")
            else:
                print("DEBUG: No cart items found to create OrderItems from.")

            # Clear the cart after items are transferred
            cart.items.all().delete() # Clear related cart items
            cart.delete() # Delete the cart itself
            print("DEBUG: Cart cleared and deleted.")
            
            # After successfully saving order and clearing cart, send confirmation email
            send_order_confirmation_email_to_customer(order)

            messages.success(request, f"Your order #{order.order_id} has been placed successfully! Payment is Cash on Delivery.")
            return redirect('orders:order_confirmation', order_id=order.id)

        else:
            print("DEBUG: Form is NOT VALID. Errors:", form.errors)
            print("DEBUG: Form non-field errors:", form.non_field_errors())
            # Ensure your template displays these errors!

    else:
        form = CheckoutForm(request=request)

    context = {
        'cart': cart,
        'cart_total': cart.get_cart_total,
        'form': form,
        'page_title': 'Checkout',
    }
    return render(request, 'orders/checkout.html', context)

@login_required
def order_confirmation_view(request, order_id):
    # This lookup is correct for the integer ID passed in the URL
    order = get_object_or_404(Order, id=order_id)

    # Optional: Ensure the user can only see their own orders
    if order.customer and request.user.is_authenticated and order.customer != request.user:
        messages.error(request, "You do not have permission to view this order.")
        return redirect('orders:my_orders') # Or some other appropriate redirect

    context = {
        'order': order,
        'page_title': f"Order #{order.order_id} Confirmation",
    }
    return render(request, 'orders/order_confirmation.html', context)


@login_required
def my_orders_view(request):
    """
    Displays a list of orders for the currently logged-in user.
    """
    if request.user.is_authenticated:
        # Filter orders by the current authenticated user
        # ***CHANGE THIS LINE: Use order_date instead of created_at***
        orders = Order.objects.filter(customer=request.user).order_by('-order_date') 
    else:
        orders = Order.objects.none()

    context = {
        'orders': orders,
        'page_title': 'My Orders',
    }
    return render(request, 'orders/my_orders.html', context)





@csrf_exempt
def update_order_status(request, order_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        status = data.get('status')

        try:
            order = Order.objects.get(id=order_id)
            order.status = status
            order.save()
            return JsonResponse({'success': True})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Order not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})
