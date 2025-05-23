from django.urls import path
from . import views
app_name = 'PO'
urlpatterns = [
    # existing paths...
    path('purchase-order-list/', views.purchase_order_list, name='purchase_order_list'),
    path('delete/', views.delete_purchase_orders, name='delete_purchase_orders'),
    path('archive/', views.archived_purchase_orders, name='archived_purchase_orders'),
    path('restore/', views.restore_purchase_orders, name='restore_purchase_orders'),
    path('permanently-delete/', views.permanently_delete_purchase_orders, name='permanently_delete_purchase_orders'),

]
