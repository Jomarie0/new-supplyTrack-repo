from django.urls import path
from .views import (
    manager_dashboard, # Consider adding path if used
    staff_dashboard,   # Consider adding path if used
    inventory_list,
    delete_products,
    dashboard,
    archive_list,
    permanently_delete_products,
    restore_products,
    restock_notifications_api,
    restock_notifications_view,
    deleted_notifications,
    restore_notifications,
    deleted_notifications_view,
    # product_forecast_api, # This is the generic one we fixed
    best_seller_api,
    demand_forecast,
    sales_stock_analytics_view,

    # get_dashboard_stats_api,
    # get_recent_activities_api # Remove if not used
)

app_name = "inventory"

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'), # Your main dashboard view
    path('inventory-list/', inventory_list, name='inventory_list'),
    path('archive-list/', archive_list, name='archive_list'),
    path('delete-products/', delete_products, name='delete_products'),
    path('permanently-delete-products/', permanently_delete_products, name='permanently_delete_products'),
    path('restore-products/', restore_products, name='restore_products'),

    # Product Forecast API (Generic)
    path('api/demand_forecast/', demand_forecast, name='demand_forecast'),
    path('sales-stock-analytics/', sales_stock_analytics_view, name='sales_stock_analytics'),

    # path('api/dashboard-stats/', get_dashboard_stats_api, name='get_dashboard_stats_api'),

    # Best Sellers API
    path('api/best-sellers/', best_seller_api, name='best_seller_api'),

    # Notification Views
    path('notifications/', restock_notifications_view, name='restock_notifications_view'),
    path('notifications/deleted/', deleted_notifications_view, name='deleted_notifications_view'),
    path('notifications/delete/', deleted_notifications, name='deleted_notifications'),
    path('notifications/restore/', restore_notifications, name='restore_notifications'),

    # Restock Notifications API (if your frontend needs this specific API)
    path('api/restock-notifications/', restock_notifications_api, name='restock_notifications_api'),
]