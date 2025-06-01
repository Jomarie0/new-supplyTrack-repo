# apps/purchasing/admin.py

from django.contrib import admin
from .models import PurchaseOrder, PurchaseOrderItem # Import all your new models
from django.utils.html import format_html
from django.urls import reverse
from apps.suppliers.models import Supplier
from datetime import timezone
# --- PurchaseOrderItem Inline Admin ---
# This allows you to add/edit items directly within the PurchaseOrder form
class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1 # Show 1 empty form by default
    fields = ('product_variant', 'quantity_ordered', 'quantity_received', 'unit_cost', 'total_price')
    readonly_fields = ('total_price',) # total_price is a calculated property
    # You might want to make unit_cost editable if it varies per PO
    # If quantity_received is updated manually, it should be editable
    # readonly_fields = ('total_price',)


# --- PurchaseOrder Admin ---
@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    inlines = [PurchaseOrderItemInline] # Link PurchaseOrderItems to PurchaseOrder admin

    list_display = (
        'purchase_order_id',
        'supplier_link', # Custom method to link to supplier
        'order_date',
        'expected_delivery_date',
        'status',
        'total_cost', # Display the calculated total cost
        'received_date',
        'is_deleted',
    )
    list_filter = (
        'status',
        'supplier', # Filter by supplier
        'order_date',
        'expected_delivery_date',
        'is_deleted',
    )
    search_fields = (
        'purchase_order_id',
        'supplier__name', # Search by supplier name
        'items__product_variant__product__name', # Search by product name in items
        'notes',
    )
    date_hierarchy = 'order_date' # Allows drilling down by date
    
    # Fields to display when adding/editing a PurchaseOrder
    fieldsets = (
        (None, {
            'fields': ('supplier', 'order_date', 'expected_delivery_date', 'status', 'notes')
        }),
        ('Receipt Information', {
            'fields': ('received_date',),
            'classes': ('collapse',), # Make this section collapsible
            'description': 'Fields related to the actual receipt of goods.'
        }),
        ('Deletion Information', {
            'fields': ('is_deleted', 'deleted_at'),
            'classes': ('collapse',),
            'description': 'These fields are for soft deletion management.'
        })
    )
    
    # Allow direct editing of status and is_deleted from the list view
    list_editable = ('status', 'is_deleted',)

    # Custom methods for list_display
    @admin.display(description='Supplier')
    def supplier_link(self, obj):
        if obj.supplier:
            link = reverse("admin:purchasing_supplier_change", args=[obj.supplier.id])
            return format_html('<a href="{}">{}</a>', link, obj.supplier.name)
        return "N/A"
    supplier_link.allow_tags = True

    # Override get_queryset to exclude soft-deleted items by default
    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)

    # You might want to add custom actions for status changes (e.g., Mark as Received)
    actions = ['mark_as_ordered', 'mark_as_received', 'mark_as_cancelled', 'soft_delete_pos', 'restore_pos']

    @admin.action(description='Mark selected POs as Ordered')
    def mark_as_ordered(self, request, queryset):
        queryset.update(status=self.model.STATUS_ORDERED)
        self.message_user(request, f"{queryset.count()} purchase orders marked as Ordered.")

    @admin.action(description='Mark selected POs as Received')
    def mark_as_received(self, request, queryset):
        # This action should trigger stock updates for all items in the PO
        # This will be handled by signals (next step)
        for po in queryset:
            # For simplicity, set received_date here, but a more complex system
            # might track individual item receipt dates.
            if po.status != self.model.STATUS_RECEIVED:
                po.status = self.model.STATUS_RECEIVED
                po.received_date = timezone.now().date() # Set date only
                po.save() # This save will trigger signals for stock update
        self.message_user(request, f"{queryset.count()} purchase orders marked as Received.")

    @admin.action(description='Mark selected POs as Cancelled')
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status=self.model.STATUS_CANCELLED)
        self.message_user(request, f"{queryset.count()} purchase orders marked as Cancelled.")
    
    @admin.action(description='Soft delete selected purchase orders')
    def soft_delete_pos(self, request, queryset):
        for po in queryset:
            po.delete() # Calls your custom soft_delete method on the model
        self.message_user(request, f"{queryset.count()} purchase orders soft-deleted.")

    @admin.action(description='Restore selected purchase orders')
    def restore_pos(self, request, queryset):
        for po in queryset:
            po.restore()
        self.message_user(request, f"{queryset.count()} purchase orders restored.")