# apps/inventory/models.py

from django.db import models
from apps.suppliers.models import Supplier # Make sure this import is correct
import uuid
from django.utils import timezone
from django.utils.text import slugify # Import slugify

# --- Category Model ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # ADDED: slug field
    slug = models.SlugField(max_length=100, unique=True, blank=True,
                            help_text="A URL-friendly identifier for the category.")
    # ADDED: parent field for hierarchical categories
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='children', help_text="Parent category for hierarchical organization.")

    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name'] # Add ordering for consistency

    def save(self, *args, **kwargs):
        # Auto-generate slug if it's not set or if the name changes
        if not self.slug or (self.pk and not self.slug == slugify(self.name)):
            self.slug = slugify(self.name)
            # Ensure slug uniqueness
            original_slug = self.slug
            count = 1
            while Category.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1
        super().save(*args, **kwargs)

    def __str__(self):
        full_path = [self.name]
        k = self.parent
        while k is not None:
            full_path.append(k.name)
            k = k.parent
        return ' -> '.join(full_path[::-1]) # Display full path: Parent -> Child -> Grandchild


# --- END: Moved Category model ---

class Product(models.Model):
    product_id = models.CharField(max_length=10, unique=True, blank=False, null=False)
    name = models.CharField(max_length=255)

    # NEW: Add a slug field for user-friendly URLs in the store
    slug = models.SlugField(max_length=255, unique=True, blank=True,
                             help_text="A URL-friendly identifier for the product.")
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)

    description = models.TextField(blank=True, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, null=True, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    stock_quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    unit = models.CharField(max_length=50, default=0)

    # CHANGE: category now directly references Category defined in this file
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='inventory_products') # Added related_name for clarity

    total_sales = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True, help_text="Designates whether this product should be visible in the store.")

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    def save(self, *args, **kwargs):
        if not self.pk and not self.product_id:
            self.product_id = uuid.uuid4().hex[:10].upper()

        # NEW: Auto-generate slug if it's not set
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure slug uniqueness if names can clash
            original_slug = self.slug
            count = 1
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
# ... (StockMovement, DemandCheckLog, RestockLog models remain the same) ...


class StockMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    movement_type = models.CharField(
        max_length=10,
        choices=[("IN", "Stock In"), ("OUT", "Stock Out")],
    )
    quantity = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.movement_type} - {self.product.name} ({self.quantity})"

class DemandCheckLog(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    forecasted_quantity = models.IntegerField()
    current_stock = models.IntegerField()
    restock_needed = models.BooleanField()
    checked_at = models.DateTimeField(auto_now_add=True)

    # Soft delete fields
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Optional: Track who deleted it if you have user authentication
    # deleted_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)

    def delete(self, using=None, keep_parents=False):
        """Soft delete: mark as deleted instead of actual deletion"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """Restore a soft-deleted notification"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    def hard_delete(self):
        """Permanently delete the record"""
        super().delete()

    def __str__(self):
        return f"{self.product.name} - {self.checked_at.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-checked_at']

class RestockLog(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    forecasted_quantity = models.IntegerField()
    current_stock = models.IntegerField()
    checked_at = models.DateTimeField(auto_now_add=True)
    is_handled = models.BooleanField(default=False)
