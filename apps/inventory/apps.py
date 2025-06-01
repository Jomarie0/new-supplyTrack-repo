from django.apps import AppConfig

class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory'  # Adjust based on your app structure
    
    def ready(self):
        import apps.inventory.signals  # Import signals when app is ready