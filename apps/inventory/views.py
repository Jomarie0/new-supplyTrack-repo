from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Product, DemandCheckLog, StockMovement
from .forms import ProductForm, StockMovementForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.db.models.functions import TruncMonth
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField

# IMPORTANT: Adjust these timezone imports
import datetime # <--- Keep this for datetime.datetime if you construct dates manually
from django.utils import timezone as django_timezone # <--- Alias Django's timezone module!

# Imports for forecasting
from sklearn.linear_model import LinearRegression
import pandas as pd
import numpy as np
from datetime import timedelta, timezone # Keep this as it's datetime.timedelta
from decimal import Decimal
from django.contrib import messages


from django.views.decorators.http import require_GET
from django.http import JsonResponse

from datetime import datetime

# Corrected Imports for Order and OrderItem
from apps.orders.models import Order, OrderItem

# Your existing dashboard views (manager_dashboard, staff_dashboard)
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
        product_id_input = request.POST.get('product_id') # Renamed to avoid conflict
        try:
            # Assuming product_id on Product model is the unique identifier you use
            product = Product.objects.get(product_id=product_id_input)
            form = ProductForm(request.POST, request.FILES, instance=product)
        except Product.DoesNotExist:
            form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(request, f"Product successfully added/updated!")
            return redirect('inventory:inventory_list')
        else:
            messages.error(request, "Error saving product. Please check the form.")
            print(form.errors) # For debugging in console
    else:
        form = ProductForm()

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

@login_required
def dashboard(request):
    """
    Main dashboard view with all necessary data for charts and statistics
    """
    # BASIC STATISTICS
    total_products = Product.objects.count()
    low_stock_count = DemandCheckLog.objects.filter(restock_needed=True, is_deleted=False).count()
    total_orders = Order.objects.filter(is_deleted=False).count()
    
    # Calculate current month's revenue (FIXED)
    current_month_start = django_timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_revenue = OrderItem.objects.filter(
        order__is_deleted=False, # Filter order itself
        order__status="Completed",
        order__order_date__gte=current_month_start
    ).aggregate(
        total=Sum(ExpressionWrapper(F('quantity') * F('price_at_order'), output_field=DecimalField()))
    )['total'] or Decimal('0.00') # Default to Decimal('0.00')

    # STOCK DATA
    products_for_chart = list(Product.objects.values_list('name', flat=True))
    stock_quantities_for_chart = list(Product.objects.values_list('stock_quantity', flat=True))
    product_names_distinct = Product.objects.values_list('name', flat=True).distinct()

    # SALES DATA - Monthly sales trend (FIXED)
    # Aggregate sales from OrderItem to get accurate totals
    sales_by_month_data = (
        OrderItem.objects
        .filter(
            order__is_deleted=False,
            order__status="Completed"
        )
        .annotate(month=TruncMonth('order__order_date')) # Truncate by order_date
        .values('month')
        .annotate(total_sales=Sum(ExpressionWrapper(F('quantity') * F('price_at_order'), output_field=DecimalField())))
        .order_by('month')
    )

    months = [entry['month'].strftime('%b %Y') for entry in sales_by_month_data]
    sales_totals = [float(entry['total_sales']) for entry in sales_by_month_data]


    # ORDER STATUS DATA
    order_status_counts = (
        Order.objects
        .filter(is_deleted=False)
        .values('status')
        .annotate(count=Count('id'))
    )
    status_labels = [entry['status'] for entry in order_status_counts]
    status_counts = [entry['count'] for entry in order_status_counts]

    # RECENT ORDERS
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
        'products_json': json.dumps(products_for_chart),
        'stock_quantities_json': json.dumps(stock_quantities_for_chart),
        'months_json': json.dumps(months),
        'sales_totals_json': json.dumps(sales_totals),
        'status_labels_json': json.dumps(status_labels),
        'status_counts_json': json.dumps(status_counts),
        
        # Raw data for template
        'product_names': product_names_distinct,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'inventory/admin/dashboards.html', context)


@csrf_exempt  
def product_forecast_api(request):
    """
    Forecasting API - Corrected to use OrderItem for product-specific sales data
    """
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
        product = Product.objects.filter(name__icontains=product_name).first() # Take the first if multiple found

    # FIXED: Query OrderItem to get sales quantity for a specific product
    sales_data = (
        OrderItem.objects
        .filter(
            product_variant__product=product, # Filter by the product linked via product_variant
            order__is_deleted=False, # Filter order itself
            order__status="Completed" # Only count completed sales
        )
        .annotate(month=TruncMonth('order__order_date')) # Aggregate by order date
        .values('month')
        .annotate(total_quantity=Sum('quantity')) # Sum quantities from OrderItem
        .order_by('month')
    )

    if not sales_data:
        return JsonResponse({'error': f'No sales data available for {product.name}'}, status=404)

    # --- Forecasting ---
    df = pd.DataFrame(sales_data)
    df['month'] = pd.to_datetime(df['month'])
    df = df.set_index('month').asfreq('MS').fillna(0) # Fill missing months with 0
    df['month_num'] = np.arange(len(df))

    # Check if there's enough data for regression (at least 2 points)
    if len(df) < 2:
        return JsonResponse({'error': f'Not enough sales data for {product.name} to forecast. Need at least 2 months of data.'}, status=400)

    model = LinearRegression()
    model.fit(df[['month_num']], df['total_quantity'])
    
    # Forecast for the next 5 months (adjust as needed)
    future_months_num = np.arange(len(df), len(df) + 5).reshape(-1, 1)
    predictions = model.predict(future_months_num)

    # Generate future dates for chart labels
    last_known_month = df.index[-1]
    future_dates = pd.date_range(start=last_known_month + pd.offsets.MonthBegin(), periods=5, freq='MS')

    # --- Demand Check ---
    forecast_qty = predictions[0]  # The forecast for the very next month
    if forecast_qty < 0: # Forecast should not be negative
        forecast_qty = 0

    current_stock = product.stock_quantity
    restock_needed = forecast_qty > current_stock

    # Try to find a recent existing log (within last 1 hour)
    recent_log = DemandCheckLog.objects.filter(
        product=product,
        is_deleted=False,
        checked_at__gte=django_timezone.now() - timedelta(hours=1)
    ).first()

    if recent_log:
        recent_log.forecasted_quantity = round(forecast_qty)
        recent_log.current_stock = current_stock
        recent_log.restock_needed = restock_needed
        recent_log.checked_at = django_timezone.now()
        recent_log.save()
    else:
        DemandCheckLog.objects.create(
            product=product,
            forecasted_quantity=round(forecast_qty),
            current_stock=current_stock,
            restock_needed=restock_needed
        )

    actual_sales_data = [{"label": date.strftime("%Y-%m"), "value": int(val)} for date, val in df['total_quantity'].items()]
    forecast_sales_data = [{"label": date.strftime("%Y-%m"), "value": int(val)} for date, val in zip(future_dates, predictions)]

    return JsonResponse({
        "actual": actual_sales_data,
        "forecast": forecast_sales_data,
        "product_name": product.name,
        "restock_needed": bool(restock_needed),
        "forecasted_quantity": int(round(forecast_qty)),
        "current_stock": int(current_stock)
    })


@csrf_exempt
def best_seller_api(request):
    """
    Enhanced API endpoint that returns best sellers with both quantity and revenue data
    Corrected to aggregate through OrderItem and ProductVariant
    """
    try:
        best_sellers = (
            OrderItem.objects
            .filter(
                order__is_deleted=False,
                order__status="Completed"
            )
            .values('product_variant__product__name') # Group by actual product name
            .annotate(
                # Sum quantity from OrderItem
                total_quantity=Sum('quantity'),
                # Sum (quantity * price_at_order) for revenue
                total_revenue=Sum(ExpressionWrapper(F('quantity') * F('price_at_order'), output_field=DecimalField())),
                product_name=F('product_variant__product__name') # Ensure product_name is available for grouping/selection
            )
            .order_by('-total_quantity')[:5] # Top 5 best sellers
        )
        
        best_sellers_list = []
        for item in best_sellers:
            best_sellers_list.append({
                'product_name': item['product_name'],
                'total_quantity': int(item['total_quantity'] or 0),
                'total_revenue': float(item['total_revenue'] or 0) # Convert Decimal to float for JSON serialization
            })
        
        return JsonResponse(best_sellers_list, safe=False)
        
    except Exception as e:
        print(f"Error in best_seller_api: {e}") # Log the actual error for debugging
        # Return dummy data if there's an error (like no data or unexpected issue)
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

@csrf_exempt
def deleted_notifications(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])

        if ids:
            for log in DemandCheckLog.objects.filter(id__in=ids, is_deleted=False):
                log.delete()
            return JsonResponse({'status': 'success', 'deleted_count': len(ids)})
        return JsonResponse({'status': 'no ids provided'}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

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

def deleted_notifications_view(request):
    logs = DemandCheckLog.objects.filter(is_deleted=True).order_by('-deleted_at')
    context = {'logs': logs}
    return render(request, 'inventory/notification/deleted_notifications.html', context)

def auto_dismiss_resolved_notifications():
    """
    Automatically soft-delete notifications that are no longer needed
    """
    dismissed_count = 0
    logs = DemandCheckLog.objects.filter(restock_needed=True, is_deleted=False)
    
    for log in logs:
        current_stock = log.product.stock_quantity
        # Check if current_stock is greater than or equal to forecasted_quantity AND if forecast_qty is not 0
        # If forecast_qty is 0, it means no demand, so it's effectively resolved if stock > 0
        if current_stock >= log.forecasted_quantity and log.forecasted_quantity > 0:
            log.delete()
            dismissed_count += 1
        elif log.forecasted_quantity == 0 and current_stock > 0: # If no demand and stock is available
            log.delete()
            dismissed_count += 1
    
    return dismissed_count



@require_GET
def demand_forecast(request):
    try:
        product_name = request.GET.get('product_name')
        if not product_name:
            return JsonResponse({'error': 'product_name parameter is required'}, status=400)

        sales_data = (
            OrderItem.objects.filter(product_variant__product__name=product_name)
            .values('order__order_date')
            .annotate(total_quantity=Sum('quantity'))
            .order_by('order__order_date')
        )

        if not sales_data:
            return JsonResponse({'error': 'No sales data found'}, status=404)

        df = pd.DataFrame(list(sales_data))
        df['order__order_date'] = pd.to_datetime(df['order__order_date']).dt.to_period('M')
        df = df.groupby('order__order_date').sum().reset_index()

        # Add time index for regression
        df['time_index'] = np.arange(len(df))

        X = df[['time_index']]
        y = df['total_quantity']

        model = LinearRegression()
        model.fit(X, y)

        # Forecast next 6 months
        future_index = np.arange(len(df), len(df) + 6).reshape(-1, 1)
        forecast = model.predict(future_index)

        forecast_data = []
        last_date = df['order__order_date'].iloc[-1].to_timestamp()

        for i, qty in enumerate(forecast):
            forecast_month = (last_date + pd.DateOffset(months=i+1)).strftime('%Y-%m')
            forecast_data.append({'label': forecast_month, 'value': max(0, round(qty))})

        # Prepare actual sales data for chart
        actual_data = []
        for _, row in df.iterrows():
            actual_data.append({'label': row['order__order_date'].strftime('%Y-%m'), 'value': int(row['total_quantity'])})

        # Calculate total forecasted quantity
        total_forecasted_qty = sum(item['value'] for item in forecast_data)

        # Get current stock from StockMovement for the product
        stock_agg = (
            StockMovement.objects.filter(product__name=product_name)
            .aggregate(
                stock_in=Sum('quantity', filter=Q(movement_type='IN')),
                stock_out=Sum('quantity', filter=Q(movement_type='OUT'))
            )
        )
        current_stock = (stock_agg['stock_in'] or 0) - (stock_agg['stock_out'] or 0)

        # Determine if restock is needed (forecast > current stock)
        restock_needed = total_forecasted_qty > current_stock

        return JsonResponse({
            'product_name': product_name,
            'current_stock': current_stock,
            'forecasted_quantity': total_forecasted_qty,
            'restock_needed': restock_needed,
            'actual': actual_data,
            'forecast': forecast_data,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

from django.db.models import Sum, F, Q
from decimal import Decimal
from apps.inventory.models import StockMovement, Product
from apps.orders.models import OrderItem

def get_sales_and_stock_analytics_by_name():
    # Total sales quantity per product (grouped by product name)
    total_sales_per_product = (
        OrderItem.objects
        .values(product_name=F('product_variant__product__name'))
        .annotate(total_quantity_sold=Sum('quantity'))
        .order_by('-total_quantity_sold')
    )
    
    # Total revenue per product
    total_revenue_per_product = (
        OrderItem.objects
        .values(product_name=F('product_variant__product__name'))
        .annotate(total_revenue=Sum(F('price_at_order') * F('quantity')))
        .order_by('-total_revenue')
    )
    
    # Current stock per product from StockMovement (grouped by product name)
    stock_aggregation = (
        StockMovement.objects
        .values(product_name=F('product__name'))
        .annotate(
            stock_in=Sum('quantity', filter=Q(movement_type='IN')),
            stock_out=Sum('quantity', filter=Q(movement_type='OUT'))
        )
        .annotate(current_stock=F('stock_in') - F('stock_out'))
        .order_by('-current_stock')
    )
    
    # Convert QuerySets to dicts for easy lookup
    sales_dict = {item['product_name']: item['total_quantity_sold'] for item in total_sales_per_product}
    revenue_dict = {item['product_name']: item['total_revenue'] for item in total_revenue_per_product}
    stock_dict = {item['product_name']: item['current_stock'] or 0 for item in stock_aggregation}
    
    # Get all unique product names
    all_product_names = set(sales_dict.keys()) | set(revenue_dict.keys()) | set(stock_dict.keys())
    
    # Fetch products by name for additional info if needed (optional)
    products = Product.objects.filter(name__in=all_product_names)
    product_names = {p.name for p in products}
    
    analytics = []
    for name in all_product_names:
        analytics.append({
            'product_name': name,
            'total_quantity_sold': sales_dict.get(name, 0),
            'total_revenue': revenue_dict.get(name, 0),
            'current_stock': stock_dict.get(name, 0),
        })
    
    return analytics
from django.http import JsonResponse

def sales_stock_analytics_view(request):
    analytics = get_sales_and_stock_analytics_by_name()
    return JsonResponse({'analytics': analytics})
