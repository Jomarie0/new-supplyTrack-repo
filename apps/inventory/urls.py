from django.urls import path
from .views import (manager_dashboard, 
                    staff_dashboard, 
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
                    # strepsils_forecast_api, 
                    product_forecast_api,
                    best_seller_api,
                    get_dashboard_stats_api,
                    # get_recent_activities_api

                    )
app_name = "inventory"

urlpatterns = [
      path('dashboard/', dashboard, name='dashboard'), # Your main dashboard view
    path('inventory-list/', inventory_list, name='inventory_list'),
    path('archive-list/', archive_list, name='archive_list'),
    path('delete-products/', delete_products, name='delete_products'),
    path('permanently-delete-products/', permanently_delete_products, name='permanently_delete_products'),
    path('restore-products/', restore_products, name='restore_products'),

    # Moved and updated Product Forecast API
    path('api/forecast/product/', product_forecast_api, name='product_forecast_api'),
    path('api/dashboard-stats/', get_dashboard_stats_api, name='get_dashboard_stats_api'),
    # path('api/recent-acts/', get_recent_activities_api, name='get_recent_activities_api'),

    # path('api/forecast/strepsils/', strepsils_forecast_api, name='strepsils_forecast_api'), # Keep for compatibility

    # Best Sellers API
    path('api/best-sellers/', best_seller_api, name='best_seller_api'),
    # path('reports/best-sellers/', best_seller_page, name='best_seller_page'),

    # Notification Views
    path('notifications/', restock_notifications_view, name='restock_notifications_view'),
    path('notifications/deleted/', deleted_notifications_view, name='deleted_notifications_view'),
    path('notifications/delete/', deleted_notifications, name='deleted_notifications'), # For soft-deleting
    path('notifications/restore/', restore_notifications, name='restore_notifications'), # For restoring

    # No need for restock_notifications_api as a direct API endpoint if we handle toasts differently
    # But if your frontend relies on it, you can keep it as is.
    path('api/restock-notifications/', restock_notifications_api, name='restock_notifications_api'),

]
