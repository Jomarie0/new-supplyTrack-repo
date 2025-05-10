from django.apps import AppConfig
from django.db.models.signals import post_save
from django.dispatch import receiver

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.orders'

    def ready(self):
        from .models import Order
        from .signals import update_inventory_on_order_change, order_delivery_confirmed
        from apps.delivery.signals import delivery_confirmed
        from apps.delivery.models import Delivery  # Import the sender model

        post_save.connect(update_inventory_on_order_change, sender=Order)
        # Explicitly import and connect the receiver
        from .signals import order_delivery_confirmed
        delivery_confirmed.connect(order_delivery_confirmed, sender=Delivery)