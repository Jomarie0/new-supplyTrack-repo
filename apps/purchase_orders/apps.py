# apps/purchasing/apps.py
from django.apps import AppConfig

class PurchasingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.purchase_orders'

    def ready(self):
        import apps.purchase_orders.signals # noqa: F401