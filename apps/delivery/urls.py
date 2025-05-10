from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    path('list/', views.delivery_list, name='delivery_list'),
    path('confirm/<int:delivery_id>/', views.confirm_delivery, name='confirm_delivery'),
    path('add/', views.add_delivery, name='add_delivery'),  # New URL
]