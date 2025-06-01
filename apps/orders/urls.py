# apps/orders/urls.py

from django.urls import path
from .views import (
    order_list,
    delete_orders,
    archived_orders,
    permanently_delete_orders,
    restore_orders,
    checkout_view,
    order_confirmation_view,
    my_orders_view,
    update_order_status,
)

app_name = 'orders'

urlpatterns = [
    path('order-list/', order_list, name='order_list'),
    path('delete/', delete_orders, name='delete_orders'),
    path('archive/', archived_orders, name='archived_orders'),
    path('permanent-delete/', permanently_delete_orders, name='permanent_delete_orders'),
    path('restore/', restore_orders, name='restore_orders'),

    # NEW Checkout Paths
    path('checkout/', checkout_view, name='checkout'),
    path('confirmation/<int:order_id>/', order_confirmation_view, name='order_confirmation'),

    path('my-orders/', my_orders_view, name='my_orders'),
     # AJAX endpoint for updating individual order status
    # path('update_status/<uuid:order_id>/', update_order_status, name='update_order_status'),
    # ^ Use <int:order_id> if your Order IDs are integers (AutoField)
    # ^ Use <uuid:order_id> if your Order IDs are UUIDField
    # urls.py
    path('orders/update-status/<int:order_id>/', update_order_status, name='update_order_status'),

]