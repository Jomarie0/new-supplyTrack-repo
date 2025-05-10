from django.apps import AppConfig

class DeliveryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.delivery'

    def ready(self):
        import apps.delivery.signals
        from .models import Delivery  # Ensure the model is loaded