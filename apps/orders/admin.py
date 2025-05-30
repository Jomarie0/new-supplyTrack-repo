# apps/orders/admin.py

from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.utils import timezone
from .models import Order, OrderItem

# --- OrderItem Inline Admin ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ['product_variant', 'quantity', 'price_at_order']
    readonly_fields = ['price_at_order']

# --- Order Admin ---
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]

    list_display = (
        'order_id',
        'customer_display',
        'get_total_cost',
        'payment_method',
        'status',
        'order_date',
        'expected_delivery_date',
        'is_deleted_display',
    )

    # Only include actual model fields that are editable
    list_editable = ('status',)  # Removed expected_delivery_date if it's auto-generated

    list_filter = ('status', 'payment_method', 'order_date', 'expected_delivery_date', 'is_deleted')

    search_fields = ('order_id', 'customer__username', 'customer__email', 'shipping_address')

    fieldsets = (
        (None, {
            'fields': ('customer', 'payment_method', 'status', 'order_date', 'expected_delivery_date')
        }),
        ('Address Information', {
            'fields': ('shipping_address', 'billing_address'),
            'classes': ('collapse',)
        }),
        ('Deletion Information', {
            'fields': ('is_deleted', 'deleted_at'),
            'classes': ('collapse',),
            'description': 'These fields are for soft deletion management.'
        })
    )

    # --- Custom Methods for list_display ---
    @admin.display(description='Customer')
    def customer_display(self, obj):
        return obj.customer.username if obj.customer else 'Guest'
    
    @admin.display(description='Total Price')
    def get_total_cost(self, obj):
        # Make sure your Order model has this method
        try:
            return f"₱{obj.get_total_cost():.2f}"
        except AttributeError:
            # Fallback if method doesn't exist
            total = sum(item.quantity * item.price_at_order for item in obj.orderitem_set.all())
            return f"₱{total:.2f}"
    
    @admin.display(boolean=True, description='Deleted?')
    def is_deleted_display(self, obj):
        return obj.is_deleted

    # Actions for soft delete and restore
    actions = ['soft_delete_orders', 'restore_orders']

    @admin.action(description='Mark selected orders as deleted (soft delete)')
    def soft_delete_orders(self, request, queryset):
        count = 0
        for order in queryset:
            if hasattr(order, 'soft_delete'):
                order.soft_delete()
                count += 1
            else:
                # Fallback manual soft delete
                order.is_deleted = True
                order.deleted_at = timezone.now()
                order.save()
                count += 1
        self.message_user(request, f"{count} orders soft-deleted.")

    @admin.action(description='Restore selected deleted orders')
    def restore_orders(self, request, queryset):
        count = 0
        for order in queryset:
            if hasattr(order, 'restore'):
                order.restore()
                count += 1
            else:
                # Fallback manual restore
                order.is_deleted = False
                order.deleted_at = None
                order.save()
                count += 1
        self.message_user(request, f"{count} orders restored.")

    # Override get_queryset to exclude soft-deleted items by default
    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)

    # Add custom URLs
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('archived/', self.admin_site.admin_view(self.archived_orders_view), name='orders_order_archived'),
        ]
        return custom_urls + urls

    def archived_orders_view(self, request):
        queryset = self.model.objects.filter(is_deleted=True)
        context = {
            'title': 'Archived Orders',
            'queryset': queryset,
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
            'has_view_permission': self.has_view_permission(request),
        }
        return render(request, 'admin/orders/archived_orders.html', context)