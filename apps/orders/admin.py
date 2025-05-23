from django.contrib import admin
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'product', 'quantity', 'expected_delivery', 'status', 'order_date', 'total_price')
    
    # Only allow editing of status and expected_delivery inline in list view
    list_editable = ('status', 'expected_delivery')
    
    list_filter = ('status', 'expected_delivery', 'order_date')
    
    search_fields = ('order_id', 'product__name', 'customer__username')
