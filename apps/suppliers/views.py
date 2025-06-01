from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderItem
from apps.suppliers.models import Supplier
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseNotAllowed
import json
from decimal import Decimal

from django.core.mail import send_mail
from django.conf import settings

def send_order_confirmed_email_to_admin(purchase_order):
    admin_email = getattr(settings, 'ADMIN_EMAIL', None)
    if not admin_email:
        print("Admin email not set in settings")
        return

    # Gather items info
    items = purchase_order.items.all()
    items_details = ""
    for item in items:
        product_name = item.product_variant.product.name if item.product_variant else item.product_name_text
        desc = item.description or "-"
        items_details += f"- {product_name} ({desc}), Qty: {item.quantity_ordered}, Unit Cost: {item.unit_cost:.2f}, Total: {item.total_price:.2f}\n"

    subject = f"Purchase Order {purchase_order.purchase_order_id} Confirmed by Supplier"
    message = (
        f"Purchase order {purchase_order.purchase_order_id} has been confirmed by supplier {purchase_order.supplier.name}.\n\n"
        f"Order Date: {purchase_order.order_date.strftime('%Y-%m-%d %H:%M')}\n"
        f"Total Cost: {purchase_order.total_cost:.2f}\n\n"
        f"Items:\n{items_details}\n"
        "Please review and process accordingly."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email='SupplyTrack <danegela13@gmail.com>',  # Your working from email
        recipient_list=[admin_email],
        fail_silently=False,
    )
    
def send_order_cancelled_email_to_admin(purchase_order):
    admin_email = getattr(settings, 'ADMIN_EMAIL', None)
    if not admin_email:
        print("Admin email not set in settings")
        return

    subject = f"Purchase Order {purchase_order.purchase_order_id} Cancelled by Supplier"
    message = (
        f"Purchase order {purchase_order.purchase_order_id} has been cancelled by supplier {purchase_order.supplier.name}.\n\n"
        f"Order Date: {purchase_order.order_date.strftime('%Y-%m-%d %H:%M')}\n"
        f"Total Cost: {purchase_order.total_cost:.2f}\n\n"
        "Please review and process accordingly."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email='SupplyTrack <danegela13@gmail.com>',  # Your working from email
        recipient_list=[admin_email],
        fail_silently=False,
    )



@login_required
def supplier_order_list(request):
    user_email = request.user.email
    try:
        supplier = Supplier.objects.get(email=user_email)
    except Supplier.DoesNotExist:
        messages.error(request, "No supplier profile linked to your account.")
        return redirect('users:dashboard')

    status_filter = request.GET.get('status', 'all').lower()

    purchase_orders = PurchaseOrder.objects.filter(
        supplier=supplier,
        is_deleted=False
    ).exclude(status=PurchaseOrder.STATUS_DRAFT)

    if status_filter != 'all':
        status_map = {
            'pending': PurchaseOrder.STATUS_PENDING,
            'accepted': PurchaseOrder.STATUS_ORDERED,
            'cancelled': PurchaseOrder.STATUS_CANCELLED,
        }
        filter_status = status_map.get(status_filter)
        if filter_status:
            purchase_orders = purchase_orders.filter(status=filter_status)
        else:
            status_filter = 'all'

    purchase_orders = purchase_orders.order_by('-order_date')

    if request.method == "POST":
        # Your POST logic here (accept/cancel/confirm)
        po_id = request.POST.get('purchase_order_id')
        action = request.POST.get('action')
        if request.POST.get('confirm_order') == 'true':
            if po_id:
                purchase_order = get_object_or_404(PurchaseOrder, purchase_order_id=po_id, supplier=supplier)
                purchase_order.status = PurchaseOrder.STATUS_ORDERED
                purchase_order.save()
                send_order_confirmed_email_to_admin(purchase_order)  # Send notification to admin
                messages.success(request, f"Purchase order {purchase_order.purchase_order_id} confirmed successfully.")
                return redirect('suppliers:supplier_order_list')

        if po_id and action in ['accept', 'cancel']:
            purchase_order = get_object_or_404(PurchaseOrder, purchase_order_id=po_id, supplier=supplier)
            
            if action == 'accept':
                purchase_order.status = PurchaseOrder.STATUS_ORDERED
                messages.success(request, f"Purchase order {po_id} accepted.")
            else:
                purchase_order.status = PurchaseOrder.STATUS_CANCELLED
                messages.info(request, f"Purchase order {po_id} cancelled.")
                # Send cancellation email
                send_order_cancelled_email_to_admin(purchase_order)
            
            purchase_order.save()
            return redirect(f"{request.path}?status={status_filter}")


        # If POST request doesn't match above, still return a redirect or response here to avoid None
        return redirect(f"{request.path}?status={status_filter}")

    # For GET requests, return render with context
    return render(request, 'suppliers/supplier_order_list.html', {
        'supplier': supplier,
        'purchase_orders': purchase_orders,
        'status_filter': status_filter,
    })



@login_required
def supplier_view_order(request, purchase_order_id):
    user_email = request.user.email
    try:
        supplier = Supplier.objects.get(email=user_email)
    except Supplier.DoesNotExist:
        messages.error(request, "No supplier profile linked to your account.")
        return redirect('users:dashboard')

    purchase_order = get_object_or_404(PurchaseOrder, purchase_order_id=purchase_order_id, supplier=supplier, is_deleted=False)

    if purchase_order.status != PurchaseOrder.STATUS_ORDERED:
        messages.error(request, "You can only view orders that you have accepted.")
        return redirect('suppliers:supplier_order_list')

    if request.method == "POST":
        if request.POST.get('confirm_order') == 'true':
            purchase_order.status = PurchaseOrder.STATUS_ORDERED  # Or new status if needed
            purchase_order.save()
            send_order_confirmed_email_to_admin(purchase_order)  # Send email here
            messages.success(request, f"Purchase order {purchase_order.purchase_order_id} confirmed successfully.")
            return redirect('suppliers:supplier_order_list')

        # Otherwise handle adding new order item
        product_name = request.POST.get('product_name', '').strip()
        description = request.POST.get('description', '').strip()
        quantity = request.POST.get('quantity')
        unit_cost = request.POST.get('unit_cost')

        if not product_name or not quantity or not unit_cost:
            messages.error(request, "Please fill all fields.")
            return redirect(request.path)

        try:
            quantity = int(quantity)
            unit_cost = Decimal(unit_cost)
            if quantity <= 0 or unit_cost <= 0:
                raise ValueError("Quantity and unit cost must be positive.")
        except Exception as e:
            messages.error(request, str(e))
            return redirect(request.path)

        PurchaseOrderItem.objects.create(
            purchase_order=purchase_order,
            product_variant=None,
            product_name_text=product_name,
            quantity_ordered=quantity,
            unit_cost=unit_cost,
            description=description,
        )

        purchase_order.calculate_total_cost()

        messages.success(request, "Item added successfully.")
        return redirect(request.path)

    else:
        items = purchase_order.items.select_related('product_variant__product').all()
        return render(request, 'suppliers/view_order.html', {
            'purchase_order': purchase_order,
            'items': items,
            'supplier': supplier,
        })

