from django.contrib import admin
from .models import Delivery

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('order', 'delivery_status', 'delivered_at')
    list_filter = ('delivery_status',)
    search_fields = ('order__order_id',)
    readonly_fields = ('delivered_at',)