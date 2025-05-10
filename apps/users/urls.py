from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView,
    CustomRefreshTokenView,
    logout as jwt_logout,  
    is_authenticated,
    login_view,
    register_view,
    logout_view,
    user_management,
    delete_users
)


app_name = "users"

urlpatterns = [
     # HTML Views
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout_view'),
    path('user-management/', user_management, name='user_management'),
    path('delete/', delete_users, name='delete_users'),

    # API Endpoints
    path('api/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/refresh/', CustomRefreshTokenView.as_view(), name='token_refresh'),
    path('api/logout/', jwt_logout, name='logout'),
    path('api/is-authenticated/', is_authenticated, name='is_authenticated'),

]
