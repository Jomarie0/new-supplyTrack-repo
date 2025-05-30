# apps/inventory/admin.py

from django.contrib import admin
from .models import Product, Category, StockMovement, DemandCheckLog, RestockLog # Ensure all models are imported

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_id', 'category', 'stock_quantity', 'price', 'is_deleted', 'supplier')
    list_filter = ('category', 'is_deleted', 'supplier')
    search_fields = ('name', 'product_id', 'description')
    
    # This is the crucial line for auto-populating slug in admin
    prepopulated_fields = {'slug': ('name',)} 
    
    # You might also want to add fields here for the form in admin
    fieldsets = (
        (None, {
            'fields': ('product_id', 'name', 'slug', 'description', 'category', 'supplier', 'unit')
        }),
        ('Pricing', {
            'fields': ('price', 'cost_price', 'last_purchase_price')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'reorder_level')
        }),
        ('Sales Data', {
            'fields': ('total_sales', 'total_revenue')
        }),
        ('Status', {
            'fields': ('is_deleted', 'deleted_at')
        }),
    )
    readonly_fields = ('product_id', 'created_at', 'updated_at', 'deleted_at') # Make these read-only


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity', 'timestamp')
    list_filter = ('movement_type', 'timestamp')
    search_fields = ('product__name',) # Search by product name

@admin.register(DemandCheckLog)
class DemandCheckLogAdmin(admin.ModelAdmin):
    list_display = ('product', 'forecasted_quantity', 'current_stock', 'restock_needed', 'checked_at', 'is_deleted')
    list_filter = ('restock_needed', 'is_deleted', 'checked_at')
    search_fields = ('product__name',)

@admin.register(RestockLog)
class RestockLogAdmin(admin.ModelAdmin):
    list_display = ('product', 'forecasted_quantity', 'current_stock', 'is_handled', 'checked_at')
    list_filter = ('is_handled', 'checked_at')
    search_fields = ('product__name',)

# Admin for Category model
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_active', 'created_at')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)} # Auto-populate slug from name
    ordering = ('name',)