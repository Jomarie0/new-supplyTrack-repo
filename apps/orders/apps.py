# apps/orders/apps.py

from django.apps import AppConfig

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.orders'

    def ready(self):
        # Simply importing the signals module is enough for @receiver decorators to work.
        # No need for explicit .connect() calls when using @receiver.
        import apps.orders.signals
        # This single import will trigger the execution of the signals.py module,
        # which in turn registers all functions decorated with @receiver.