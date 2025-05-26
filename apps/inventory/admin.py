from django.contrib import admin
from .models import Product, StockMovement, DemandCheckLog

admin.site.register(Product)
admin.site.register(StockMovement)
admin.site.register(DemandCheckLog)

