from django.urls import path
from . views import (
    order_list,
    delete_orders,
    archived_orders,
    permanently_delete_orders,
    restore_orders,

    # restock_notifications_api,
)

app_name = 'orders'

urlpatterns = [
    path('order-list/', order_list, name='order_list'),
    path('delete/', delete_orders, name='delete_orders'),
    path('archive/', archived_orders, name='archived_orders'),
    path('permanent-delete/', permanently_delete_orders, name='permanent_delete_orders'),
    path('restore/', restore_orders, name='restore_orders'),

    # path('api/restock-notifications/', restock_notifications_api, name='restock_notifications_api'),



]
