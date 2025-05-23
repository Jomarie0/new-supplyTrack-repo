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
    delete_users,
    verify_email_view,
    resend_verification_code_view,
    forgot_password_view,
    verify_reset_code_view,
    resend_reset_code_view,
    reset_password_view
)


app_name = "users"

urlpatterns = [
     # HTML Views
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout_view'),
    path('user-management/', user_management, name='user_management'),
    path('delete/', delete_users, name='delete_users'),
    path('verify/', verify_email_view, name='verify_email'),
    path('resend-code/', resend_verification_code_view, name='resend_code'),
    path('forgot-password/', forgot_password_view, name='forgot_password'),
    path('verify-reset-code/', verify_reset_code_view, name='verify_reset_code'),
    path('resend-reset-code/', resend_reset_code_view, name='resend_reset_code'),
    path('reset-password/', reset_password_view, name='reset_password'),

    # API Endpoints
    path('api/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/refresh/', CustomRefreshTokenView.as_view(), name='token_refresh'),
    path('api/logout/', jwt_logout, name='logout'),
    path('api/is-authenticated/', is_authenticated, name='is_authenticated'),

]
