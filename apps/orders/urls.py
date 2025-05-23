from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('order-list/', views.order_list, name='order_list'),
    path('delete/', views.delete_orders, name='delete_orders'),
    path('archive/', views.archived_orders, name='archived_orders'),
    path('permanent-delete/', views.permanently_delete_orders, name='permanent_delete_orders'),
    path('restore/', views.restore_orders, name='restore_orders'),
    path('api/forecast/strepsils/', views.strepsils_forecast_api, name='strepsils_forecast_api'),
    path('api/forecast/product/', views.product_forecast_api, name='product_forecast_api'),


]
