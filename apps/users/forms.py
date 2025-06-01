from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import CustomerProfile, SupplierProfile

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class CustomerRegistrationForm(UserCreationForm):
    phone = forms.CharField(max_length=15, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    class Meta:
        model = User
        fields = ("username", "email", "phone", "address", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'customer'
        if commit:
            user.save()
            # Create or update CustomerProfile
            CustomerProfile.objects.update_or_create(
                user=user,
                defaults={
                    'phone': self.cleaned_data.get('phone', ''),
                    'address': self.cleaned_data.get('address', ''),
                }
            )
        return user


class SupplierRegistrationForm(UserCreationForm):
    phone = forms.CharField(max_length=15, required=True)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)
    company_name = forms.CharField(max_length=100, required=True)
    business_registration = forms.CharField(
        max_length=50,
        required=False,
        help_text="Business registration number (optional)"
    )

    class Meta:
        model = User
        fields = ("username", "email", "phone", "address", "company_name", "business_registration", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'supplier'
        user.is_approved = False  # Suppliers need approval
        if commit:
            user.save()
            SupplierProfile.objects.update_or_create(
                user=user,
                defaults={
                    'phone': self.cleaned_data.get('phone', ''),
                    'address': self.cleaned_data.get('address', ''),
                    'company_name': self.cleaned_data.get('company_name', ''),
                    'business_registration': self.cleaned_data.get('business_registration', ''),
                }
            )
        return user


class AdminUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            ('admin', 'Admin'),
            ('manager', 'Manager'),
            ('staff', 'Staff'),
            ('delivery', 'Delivery Confirmation'),
            ('customer', 'Customer'),
            ('supplier', 'Supplier'),
        ]
    )

    class Meta:
        model = User
        fields = ("username", "email", "role", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data.get('role')
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    pass
