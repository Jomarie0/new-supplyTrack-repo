from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Product,DemandCheckLog
from .forms import ProductForm, StockMovementForm
from django.http import JsonResponse
from apps.orders.models import Order  # adjust if needed
from django.views.decorators.csrf import csrf_exempt
import json
from django.db.models.functions import TruncMonth
from django.db.models import Sum, Count
from django.utils.timezone import now
from django.utils import timezone

from django.utils.timezone import now
from django.db.models.functions import TruncMonth
from django.db.models import Sum
from sklearn.linear_model import LinearRegression
import pandas as pd
import numpy as np
from datetime import timedelta
from django.db.models import F, Sum, ExpressionWrapper, FloatField
from apps.inventory.models import DemandCheckLog
# from .utils.forecasting import forecast_stock_demand_from_orders



# @login_required
# def admin_dashboard(request):
#     return render(request, "inventory/admin/admin_dashboard.html")

@login_required
def manager_dashboard(request):
    return render(request, "inventory/manager/manager_dashboard.html")

@login_required
def staff_dashboard(request):
    return render(request, "inventory/admin/admin_dashboard.html")


@login_required
def inventory_list(request):
    products = Product.objects.filter(is_deleted=False)

    movement_form = StockMovementForm()

    if request.method == 'POST':
        product_id = request.POST.get('product_id')  # This is the custom product ID

        # Check if a product exists with that custom product_id
        try:
            product = Product.objects.get(product_id=product_id)
            form = ProductForm(request.POST, instance=product)  # Update
        except Product.DoesNotExist:
            form = ProductForm(request.POST)  # Create new

        if form.is_valid():
            form.save()
            return redirect('inventory:inventory_list')
    else:
        form = ProductForm()  # Empty form for GET

    context = {
        'products': products,
        'form': form,
        'movement_form': movement_form,
    }
    return render(request, 'inventory/inventory_list/inventory_list.html', context)

@login_required
def archive_list(request):
    archived_products = Product.objects.filter(is_deleted=True)
    return render(request, 'inventory/inventory_list/archive_list.html', {'products': archived_products})

@csrf_exempt
def delete_products(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])

        if ids:
            for product in Product.objects.filter(id__in=ids):
                product.delete()  # Triggers the custom delete (soft delete)
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'no ids provided'}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

@csrf_exempt
def permanently_delete_products(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])

        if ids:
            Product.objects.filter(id__in=ids, is_deleted=True).delete()
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'no ids provided'}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

@csrf_exempt
def restore_products(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])

        if ids:
            for product in Product.objects.filter(id__in=ids, is_deleted=True):
                product.restore()
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'no ids provided'}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)


# ---------------------- D A S H  B O A R D ------------------------- #

def dashboard(request):
    # STOCK DATA
    products = list(Product.objects.values_list('name', flat=True))
    stock_quantities = list(Product.objects.values_list('stock_quantity', flat=True))
    product_names = Product.objects.values_list('name', flat=True).distinct()

    # SALES DATA
    sales_by_month = (
        Order.objects
        .filter(is_deleted=False, status="Completed")
        .annotate(month=TruncMonth('order_date'))
        .values('month')
        .annotate(total_sales=Sum('total_price'))
        .order_by('month')
    )

    months = [entry['month'].strftime('%b') for entry in sales_by_month]
    sales_totals = [float(entry['total_sales']) for entry in sales_by_month]

    # ORDER STATUS DATA
    order_status_counts = (
        Order.objects
        .filter(is_deleted=False)
        .values('status')
        .annotate(count=Count('id'))
    )
    status_labels = [entry['status'] for entry in order_status_counts]
    status_counts = [entry['count'] for entry in order_status_counts]

    context = {
        'products_json': json.dumps(products),
        'stock_quantities_json': json.dumps(stock_quantities),
        'months_json': json.dumps(months),
        'sales_totals_json': json.dumps(sales_totals),
        'status_labels_json': json.dumps(status_labels),
        'status_counts_json': json.dumps(status_counts),
        'product_names': product_names
    }
    return render(request, 'inventory/admin/admin_dashboard.html', context)
# forecasting area dine


@csrf_exempt
def product_forecast_api(request):
    global forecast,forecast_qty, current_stock
    # Get product name from query parameters or POST data
    if request.method == 'GET':
        product_name = request.GET.get('product')
    else:  # POST
        data = json.loads(request.body) if request.body else {}
        product_name = data.get('product')

    if not product_name:
        return JsonResponse({'error': 'Product name is required'}, status=400)

    try:
        product = Product.objects.get(name__icontains=product_name)
    except Product.DoesNotExist:
        return JsonResponse({'error': f'{product_name} product not found'}, status=404)
    except Product.MultipleObjectsReturned:
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

    # --- Forecasting ---
    df = pd.DataFrame(sales)
    df['month'] = pd.to_datetime(df['month'])
    df = df.set_index('month').asfreq('MS').fillna(0)
    df['month_num'] = np.arange(len(df))

    model = LinearRegression()
    model.fit(df[['month_num']], df['total_quantity'])
    future_months = np.arange(len(df), len(df) + 2).reshape(-1, 1)

    future_months_df = pd.DataFrame(future_months, columns=['month_num'])
    predictions = model.predict(future_months_df)

    future_dates = pd.date_range(start=df.index[-1] + pd.offsets.MonthBegin(), periods=2, freq='MS')

    # --- Demand Check ---
    forecast_qty = predictions[0]  # The new accurate forecast
    current_stock = product.stock_quantity
    restock_needed = forecast_qty > current_stock

    # Try to find a recent existing log
    recent_log = DemandCheckLog.objects.filter(
        product=product,
        is_deleted=False,
        checked_at__gte=timezone.now() - timedelta(hours=1)  # within 1 hour
    ).first()

    if recent_log:
        # ✅ Update existing log with the newest forecast
        recent_log.forecasted_quantity = round(forecast_qty)
        recent_log.current_stock = current_stock
        recent_log.restock_needed = restock_needed
        recent_log.checked_at = timezone.now()
        recent_log.save()
    else:
        # ✅ Or create a new one if none found
        DemandCheckLog.objects.create(
            product=product,
            forecasted_quantity=round(forecast_qty),
            current_stock=current_stock,
            restock_needed=restock_needed
        )





    actual = [{"label": date.strftime("%Y-%m"), "value": int(val)} for date, val in df['total_quantity'].items()]
    forecast = [{"label": date.strftime("%Y-%m"), "value": int(val)} for date, val in zip(future_dates, predictions)]

    return JsonResponse({
        "actual": actual,
        "forecast": forecast,
        "product_name": product.name,
        "restock_needed": bool(restock_needed),
        "forecasted_quantity": int(round(forecast_qty)),
        "current_stock": int(current_stock)
    })



# Optional: Keep the original endpoint for backward compatibility
@csrf_exempt
def strepsils_forecast_api(request):
    # Redirect to the new dynamic endpoint with Strepsils as default
    request.GET = request.GET.copy()
    request.GET['product'] = 'Strepsils'
    return product_forecast_api(request)

def best_seller_api(request):
    metric = request.GET.get('metric', 'quantity')
    
    if metric not in ['quantity', 'revenue']:
        return JsonResponse({'error': 'Invalid metric type'}, status=400)

    # Add debugging
    print(f"Fetching best sellers for metric: {metric}")
    
    orders = Order.objects.filter(is_deleted=False)
    print(f"Total orders found: {orders.count()}")

    if metric == 'quantity':
        best_sellers = (
            orders.values('product__name')
            .annotate(value=Sum('quantity'))
            .order_by('-value')[:5]
        )
    else:
        revenue_expr = ExpressionWrapper(F('quantity') * F('unit_price'), output_field=FloatField())
        best_sellers = (
            orders.values('product__name')
            .annotate(revenue=Sum(revenue_expr))
            .order_by('-revenue')[:5]
        )
    
    result = []
    for entry in best_sellers:
        if metric == 'quantity':
            result.append({
                'product': entry['product__name'], 
                'value': float(entry['value']) if entry['value'] else 0
            })
        else:
            result.append({
                'product': entry['product__name'], 
                'value': float(entry['revenue']) if entry['revenue'] else 0
            })
    
    print(f"Result: {result}")
    return JsonResponse(result, safe=False)



def restock_notifications_api(request):
    product_name = request.GET.get('product')
    logs = DemandCheckLog.objects.filter(restock_needed=True, is_deleted=False)

    if product_name:
        logs = logs.filter(product__name__icontains=product_name)

    data = []
    for log in logs:
        data.append({
            'id': log.id,
            'product_name': log.product.name,
            'forecasted_quantity': round(log.forecasted_quantity),
            'current_stock': log.current_stock,
            'restock_needed': log.restock_needed,
            'checked_at': log.checked_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    return JsonResponse(data, safe=False)



def restock_notifications_view(request):
    logs = DemandCheckLog.objects.filter(
        restock_needed=True,
        is_deleted=False
    ).order_by('-checked_at')
    context = {'logs': logs}
    return render(request, 'inventory/notification/notification_list.html', context)

# New view to handle soft deleting notifications
@csrf_exempt
def deleted_notifications(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])

        if ids:
            for log in DemandCheckLog.objects.filter(id__in=ids, is_deleted=False):
                log.delete()  # This will trigger soft delete
            return JsonResponse({'status': 'success', 'deleted_count': len(ids)})
        return JsonResponse({'status': 'no ids provided'}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

# View to restore soft-deleted notifications
@csrf_exempt
def restore_notifications(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])

        if ids:
            for log in DemandCheckLog.objects.filter(id__in=ids, is_deleted=True):
                log.restore()
            return JsonResponse({'status': 'success', 'restored_count': len(ids)})
        return JsonResponse({'status': 'no ids provided'}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

# View to see deleted notifications
def deleted_notifications_view(request):
    logs = DemandCheckLog.objects.filter(is_deleted=True).order_by('-deleted_at')
    context = {'logs': logs}
    return render(request, 'inventory/notification/deleted_notifications.html', context)

# Auto-dismiss resolved notifications (soft delete them)
def auto_dismiss_resolved_notifications():
    """
    Automatically soft-delete notifications that are no longer needed
    """
    dismissed_count = 0
    logs = DemandCheckLog.objects.filter(restock_needed=True, is_deleted=False)
    
    for log in logs:
        current_stock = log.product.stock_quantity
        if current_stock >= log.forecasted_quantity:
            log.delete()  # Soft delete
            dismissed_count += 1
    
    return dismissed_count

