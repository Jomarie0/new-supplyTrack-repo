from django.shortcuts import render, redirect
from .models import Product, Order
from .forms import OrderForm
from apps.inventory.models import Product
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import random
import string
from django.utils.timezone import now
from django.db.models.functions import TruncMonth
from django.db.models import Sum
from sklearn.linear_model import LinearRegression
import pandas as pd
import numpy as np


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
            order = form.save(commit=False)
            if not order.order_id:
                order.order_id = generate_unique_order_id()
            order.save()
            return redirect('orders:order_list')



    orders = Order.objects.filter(is_deleted=False)

    context = {
        'orders': orders,
        'form': form,
        'products': Product.objects.filter(is_deleted=False)

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



@csrf_exempt
def product_forecast_api(request):
    # Get product name from query parameters or POST data
    if request.method == 'GET':
        product_name = request.GET.get('product')
    else:  # POST
        data = json.loads(request.body) if request.body else {}
        product_name = data.get('product')
    
    if not product_name:
        return JsonResponse({'error': 'Product name is required'}, status=400)
    
    try:
        # Use icontains to find product (case-insensitive partial match)
        product = Product.objects.get(name__icontains=product_name)
    except Product.DoesNotExist:
        return JsonResponse({'error': f'{product_name} product not found'}, status=404)
    except Product.MultipleObjectsReturned:
        # If multiple products match, get the first one or be more specific
        product = Product.objects.filter(name__icontains=product_name).first()

    sales = (
        Order.objects
        .filter(product=product, is_deleted=False)
        .annotate(month=TruncMonth('order_date'))
        .values('month')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('month')
    )

    if not sales:
        return JsonResponse({'error': f'No sales data available for {product.name}'}, status=404)

    df = pd.DataFrame(sales)
    df['month'] = pd.to_datetime(df['month'])
    df = df.set_index('month').asfreq('MS').fillna(0)
    df['month_num'] = np.arange(len(df))

    # Forecast using Linear Regression
    model = LinearRegression()
    model.fit(df[['month_num']], df['total_quantity'])

    future_months = np.arange(len(df), len(df) + 2).reshape(-1, 1)
    future_dates = pd.date_range(start=df.index[-1] + pd.offsets.MonthBegin(), periods=2, freq='MS')
    predictions = model.predict(future_months)

    actual = [{"label": date.strftime("%Y-%m"), "value": int(val)} for date, val in df['total_quantity'].items()]
    forecast = [{"label": date.strftime("%Y-%m"), "value": int(val)} for date, val in zip(future_dates, predictions)]

    return JsonResponse({
        "actual": actual,
        "forecast": forecast,
        "product_name": product.name
    })

# Optional: Keep the original endpoint for backward compatibility
@csrf_exempt
def strepsils_forecast_api(request):
    # Redirect to the new dynamic endpoint with Strepsils as default
    request.GET = request.GET.copy()
    request.GET['product'] = 'Strepsils'
    return product_forecast_api(request)

