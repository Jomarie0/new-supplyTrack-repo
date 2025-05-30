from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import datetime
from apps.transactions.models import Transaction

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('delivery', 'Delivery Confirmation'),
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
        
    is_approved = models.BooleanField(default=True)
    date_requested = models.DateTimeField(auto_now_add=True)
    
    # Store the original role when the object is loaded/created
    _original_role = None 
    _original_is_approved = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set _original_role only if the instance is already in the database
        if self.pk:
            # We use self._loaded_values to get the value as it was loaded from the DB
            # This is more robust than self.role at this stage if save() is called directly.
            self._original_role = self.role 
            self._original_is_approved = self.is_approved # Capture original state


    # def save(self, *args, **kwargs):
    #     # Check if the role has changed and is being set to 'supplier'
    #     # The self.pk check ensures this only applies to existing users
    #     if self.pk and self._original_role != 'supplier' and self.role == 'supplier':
    #         self.is_approved = False
    #     # For new suppliers (not yet in DB), set is_approved to False
    #     elif not self.pk and self.role == 'supplier':
    #         self.is_approved = False
    #     # For all other roles, or if role changed from supplier to a non-supplier role
    #     elif self.role in ['admin', 'manager', 'staff', 'delivery', 'customer']:
    #         self.is_approved = True
    def save(self, *args, **kwargs):
        # Determine the approval status logic
        if self.pk and self._original_role != 'supplier' and self.role == 'supplier':
            self.is_approved = False
        elif not self.pk and self.role == 'supplier':
            self.is_approved = False
        elif self.role in ['admin', 'manager', 'staff', 'delivery', 'customer']:
            self.is_approved = True

        approval_status_changed = self.pk and self.is_approved != self._original_is_approved

        super().save(*args, **kwargs)
        if approval_status_changed and self.is_approved:
            # You'd need to know *who* approved it. This `save` method
            # doesn't inherently know the acting user. This is better handled
            # in the view/serializer that triggers the approval.
            # For a basic approach, you could log it as 'System' or assume
            # an admin did it.
            Transaction.objects.create(
                user=self, # The user whose status was changed (supplier)
                transaction_type='supplier_approval',
                description=f"Supplier '{self.username}' was approved.",
                # status='completed'
            )

        # Update _original_role after saving to reflect the current state
        self._original_role = self.role
        self._original_is_approved = self.is_approved


    def __str__(self):
        return f"{self.username} ({self.role})"


class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        expiration_time = timezone.now() - datetime.timedelta(minutes=3)
        return self.created_at < expiration_time
    

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return f"Customer: {self.user.username}"


class SupplierProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='supplier_profile')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    company_name = models.CharField(max_length=100, blank=True)
    business_registration = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Supplier: {self.company_name} ({self.user.username})"