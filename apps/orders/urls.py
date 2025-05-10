from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('order-list/', views.order_list, name='order_list'),
    path('delete/', views.delete_orders, name='delete_orders'),
]