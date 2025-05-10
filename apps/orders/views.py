from django.shortcuts import render, redirect
from .models import Order
from .forms import OrderForm
from apps.inventory.models import Product
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import random
import string

def generate_unique_order_id():
    from .models import Order
    while True:
        order_id = 'ORD' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Order.objects.filter(order_id=order_id).exists():
            return order_id

def order_list(request):
    form = OrderForm()

    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        if order_id:
            try:
                existing_order = Order.objects.get(order_id=order_id)
                form = OrderForm(request.POST, instance=existing_order)
            except Order.DoesNotExist:
                form = OrderForm(request.POST)
        else:
            form = OrderForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('orders:order_list')

    orders = Order.objects.all()
    context = {
        'orders': orders,
        'form': form,
        'products': Product.objects.all()
    }
    return render(request, 'orders/orders_list.html', context)


@csrf_exempt
def delete_orders(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_ids_to_delete = data.get('ids', [])
            Order.objects.filter(order_id__in=order_ids_to_delete).delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})




# Purchase Orders