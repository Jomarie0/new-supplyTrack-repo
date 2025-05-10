from django.urls import path
from . import views
app_name = 'PO'
urlpatterns = [
    # existing paths...
    path('purchase-order-list/', views.purchase_order_list, name='purchase_order_list'),
    path('delete/', views.delete_purchase_orders, name='delete_purchase_orders'),
]
