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
from django.contrib import messages

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
            messages.success(request, "Product{'product_id'} successfully added!")
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
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta, datetime
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# Import your models here
# from .models import Product, Order, DemandCheckLog

def dashboard(request):
    """
    Main dashboard view with all necessary data for charts and statistics
    """
    # BASIC STATISTICS
    total_products = Product.objects.count()
    low_stock_count = DemandCheckLog.objects.filter(restock_needed=True, is_deleted=False).count()

    # low_stock_count = Product.objects.filter(stock_quantity__lt=10).count()  # Adjust threshold as needed
    total_orders = Order.objects.filter(is_deleted=False).count()
    
    # Calculate current month's revenue
    current_month = timezone.now().replace(day=1)
    monthly_revenue = Order.objects.filter(
        is_deleted=False,
        status="Completed",
        order_date__gte=current_month
    ).aggregate(total=Sum('total_price'))['total'] or 0

    # STOCK DATA
    products = list(Product.objects.values_list('name', flat=True))
    stock_quantities = list(Product.objects.values_list('stock_quantity', flat=True))
    product_names = Product.objects.values_list('name', flat=True).distinct()

    # SALES DATA - Monthly sales trend
    sales_by_month = (
        Order.objects
        .filter(is_deleted=False, status="Completed")
        .annotate(month=TruncMonth('order_date'))
        .values('month')
        .annotate(total_sales=Sum('total_price'))
        .order_by('month')
    )

    months = [entry['month'].strftime('%b %Y') for entry in sales_by_month]
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

    # RECENT ORDERS (optional - for additional dashboard info)
    recent_orders = Order.objects.filter(
        is_deleted=False
    ).order_by('-order_date')[:5]

    context = {
        # Statistics
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'total_orders': total_orders,
        'monthly_revenue': round(monthly_revenue, 2),
        
        # Chart data (JSON serialized for JavaScript)
        'products_json': json.dumps(products),
        'stock_quantities_json': json.dumps(stock_quantities),
        'months_json': json.dumps(months),
        'sales_totals_json': json.dumps(sales_totals),
        'status_labels_json': json.dumps(status_labels),
        'status_counts_json': json.dumps(status_counts),
        
        # Raw data for template
        'product_names': product_names,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'inventory/admin/dashboards.html', context)


# Your existing product_forecast_api function should remain unchanged since it's already working
# I'm just providing the dashboard view to work with your existing setup

@csrf_exempt  
def product_forecast_api(request):
    """
    Your existing forecast API - keeping it exactly as it was working
    """
    global forecast, forecast_qty, current_stock
    
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


# Additional helper views you might want to add

def get_dashboard_stats_api(request):
    """
    API endpoint to get real-time dashboard statistics
    """
    stats = {
        'total_products': Product.objects.count(),
        'low_stock_count': Product.objects.filter(stock_quantity__lt=10).count(),
        'total_orders': Order.objects.filter(is_deleted=False).count(),
        'pending_orders': Order.objects.filter(is_deleted=False, status='Pending').count(),
    }
    return JsonResponse(stats)


def get_recent_activities_api(request):
    """
    API endpoint to get recent activities for dashboard
    """
    recent_orders = Order.objects.filter(
        is_deleted=False
    ).order_by('-order_date')[:10].values(
        'id', 'total_price', 'status', 'order_date', 'product__name'
    )
    
    return JsonResponse({
        'recent_orders': list(recent_orders)
    }, default=str)  # default=str to handle datetime serialization

# def best_seller_api(request):
#     """
#     Enhanced API endpoint that returns best sellers with both quantity and revenue data
#     """
#     try:
#         # Get best sellers with both quantity and revenue metrics
#         best_sellers = (
#             Order.objects
#             .filter(is_deleted=False, status="Completed")
#             .values('product__name')
#             .annotate(
#                 total_quantity=Sum('quantity'),
#                 total_revenue=Sum('total_price'),
#                 product_name=F('product__name')
#             )
#             .order_by('-total_quantity')[:10]  # Top 10 best sellers
#         )
        
#         # Convert to list and ensure we have both metrics
#         best_sellers_list = []
#         for item in best_sellers:
#             best_sellers_list.append({
#                 'product_name': item['product_name'],
#                 'total_quantity': int(item['total_quantity'] or 0),
#                 'total_revenue': float(item['total_revenue'] or 0)
#             })
        
#         return JsonResponse(best_sellers_list, safe=False)
        
#     except Exception as e:
#         # Return dummy data if there's an error (like no Order model)
#         dummy_data = [
#             {'product_name': 'Product A', 'total_quantity': 150, 'total_revenue': 1500.00},
#             {'product_name': 'Product B', 'total_quantity': 120, 'total_revenue': 2400.00},
#             {'product_name': 'Product C', 'total_quantity': 100, 'total_revenue': 1000.00},
#             {'product_name': 'Product D', 'total_quantity': 80, 'total_revenue': 1600.00},
#             {'product_name': 'Product E', 'total_quantity': 75, 'total_revenue': 750.00},
#         ]
#         return JsonResponse(dummy_data, safe=False)

from django.db.models import Sum, F
from django.http import JsonResponse

def best_seller_api(request):
    try:
        best_sellers = (
            Order.objects
            .filter(is_deleted=False, status="Completed")
            .values('product__name')
            .annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum('total_price'),
                product_name=F('product__name')
            )
            .order_by('-total_quantity')[:5]
        )

        best_sellers_list = [
            {
                'product_name': item['product_name'],
                'total_quantity': int(item['total_quantity'] or 0),
                'total_revenue': float(item['total_revenue'] or 0),
            }
            for item in best_sellers
        ]

        return JsonResponse(best_sellers_list, safe=False)

    except Exception as e:
        # Log the error if you want (optional)
        # logger.error(f"Error in best_seller_api: {e}", exc_info=True)

        # Return dummy data on error
        dummy_data = [
            {'product_name': 'Product A', 'total_quantity': 150, 'total_revenue': 1500.00},
            {'product_name': 'Product B', 'total_quantity': 120, 'total_revenue': 2400.00},
            {'product_name': 'Product C', 'total_quantity': 100, 'total_revenue': 1000.00},
            {'product_name': 'Product D', 'total_quantity': 80, 'total_revenue': 1600.00},
            {'product_name': 'Product E', 'total_quantity': 75, 'total_revenue': 750.00},
        ]
        return JsonResponse(dummy_data, safe=False)



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

