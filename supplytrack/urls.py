
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponseRedirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: HttpResponseRedirect('/users/login/')),

    path('users/', include('apps.users.urls')),
    # path('users/', include('apps.users.urls')),
    path("inventory/", include("apps.inventory.urls")),
    path("orders/", include("apps.orders.urls")), 
    path('purchase_orders/', include("apps.purchase_orders.urls")), 
    path('delivery/', include('apps.delivery.urls')), # Include delivery app URLs
 


    
]
