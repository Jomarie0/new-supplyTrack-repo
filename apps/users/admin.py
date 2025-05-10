from django.contrib import admin
from django.contrib.auth import get_user_model

User = get_user_model()

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "is_staff", "is_superuser")
    search_fields = ("username", "email")

# If using a custom User model, ensure it's in AUTH_USER_MODEL
