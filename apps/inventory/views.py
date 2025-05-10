from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Product
from .forms import ProductForm, StockMovementForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@login_required
def admin_dashboard(request):
    return render(request, "inventory/admin/admin_dashboard.html")

@login_required
def manager_dashboard(request):
    return render(request, "inventory/manager/manager_dashboard.html")

@login_required
def staff_dashboard(request):
    return render(request, "inventory/staff/staff_dashboard.html")


@login_required
def inventory_list(request):
    products = Product.objects.all()
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

@csrf_exempt
def delete_products(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])
        
        if ids:
            Product.objects.filter(id__in=ids).delete()
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'no ids provided'}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)