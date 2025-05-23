from django.urls import path
from .views import manager_dashboard, staff_dashboard, inventory_list,delete_products,dashboard

app_name = "inventory"

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),

    path("manager-dashboard/", manager_dashboard, name="manager_dashboard"),
    path("staff-dashboard/", staff_dashboard, name="staff_dashboard"),
    path("inventory-list/", inventory_list, name="inventory_list"),
    path('delete_products/',delete_products, name='delete_products'),


]
