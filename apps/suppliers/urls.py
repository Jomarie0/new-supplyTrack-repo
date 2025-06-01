from django.urls import path
from . import views

app_name = 'suppliers'

urlpatterns = [
    path('orders/', views.supplier_order_list, name='supplier_order_list'),
    path('orders/view/<str:purchase_order_id>/', views.supplier_view_order, name='view_order'),  # New URL
]
