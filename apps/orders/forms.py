# apps/orders/forms.py

from django import forms
from .models import Order # Ensure Order and OrderItem are imported
from apps.inventory.models import Product
from apps.suppliers.models import Supplier
from apps.store.models import ProductVariant # <-- Ensure this is imported for OrderItem context

from django.core.exceptions import ValidationError

# --- IMPORTANT: Re-evaluate the purpose of this OrderForm ---
# Your original OrderForm was for single-item orders on the Order model.
# Now that Order is a container for multiple OrderItems, this form is no longer suitable
# for directly creating a customer's order.
# If this form is for an ADMIN/INTERNAL purpose (e.g., adding a single product to an order manually),
# it would need to create an Order *and then* an OrderItem.
# For simplicity and to fix the error, we'll strip it down to fields that are now on Order.
# Or, if this form is solely for creating *new* orders that are populated by a single product,
# you'd need to create both an Order and an OrderItem from it.

# Assuming this OrderForm is used for administrative editing of the *Order header*
# or for a very simple, single-product administrative purchase.
# If it's truly for existing orders, its fields should reflect the new Order model.
class OrderForm(forms.ModelForm):
    # These fields reflect the new Order model's attributes
    # product and quantity are NO LONGER direct fields on Order
    # unit_price is also NO LONGER a direct field on Order
    
    # We'll include fields relevant to the Order header, not its individual items.
    
    # If this form is used for ADMIN/BACKEND manual order creation,
    # you might need to add a way to select products and quantities,
    # which would then be used to create OrderItems in the view.
    # For now, let's just make it compatible with the new Order model directly.
    
    # The fields should be what's left on the Order model that an admin might edit
    # like status, expected_delivery_date, customer, shipping/billing address
    # You might consider creating a separate form for "Order Header" and another for "Order Item".
    
    # Example for an OrderHeader form (for backend/admin use)
    # product = forms.ModelChoiceField(queryset=Product.objects.all(), empty_label="Select a product", required=False)
    # quantity = forms.IntegerField(min_value=1, required=False)

    expected_delivery_date = forms.DateField( # Renamed from expected_delivery
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )

    class Meta:
        model = Order
        # ONLY include fields that are direct attributes of the NEW Order model
        fields = [
            'customer',
            'shipping_address',
            'billing_address',
            'payment_method',
            'status',
            'order_date',
            'expected_delivery_date',
        ]
        # Remove product, quantity, unit_price as they are no longer on the Order model
        # 'product', 'quantity', 'unit_price' were the fields causing the FieldError

    # The clean method will need to be updated if you keep logic related to product/quantity
    # For now, removing the old product/quantity validation
    # def clean(self):
    #     cleaned_data = super().clean()
    #     product = cleaned_data.get("product")
    #     quantity = cleaned_data.get("quantity")
    #     if product and quantity:
    #         if quantity > product.stock_quantity:
    #             raise forms.ValidationError(f"Only {product.stock_quantity} items in stock.")
    #     return cleaned_data


# --- CheckoutForm (as provided previously) ---
class CheckoutForm(forms.ModelForm):
    full_name = forms.CharField(max_length=255, required=True, help_text="Recipient's full name")
    email = forms.EmailField(required=True, help_text="Email for order updates")
    phone_number = forms.CharField(max_length=20, required=True, help_text="Contact phone number")
    street_address = forms.CharField(max_length=255, required=True)
    city = forms.CharField(max_length=100, required=True)
    province = forms.CharField(max_length=100, required=True)
    zip_code = forms.CharField(max_length=10, required=True)

    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHODS,
        widget=forms.RadioSelect,
        initial='COD',
        help_text="Choose your payment method."
    )
    
    # Add expected_delivery_date to the form explicitly for the user to input
    expected_delivery_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        help_text="Optional: Preferred delivery date"
    )


    class Meta:
        model = Order
        # These are the *model fields* that will be populated by the form's clean method
        # The form's individual fields (full_name, street_address, etc.) will build these.
        fields = [
            'shipping_address',
            'billing_address', # Can be derived from shipping if not separate
            'payment_method',
            'expected_delivery_date', # Now explicitly part of the Meta fields
        ]
        
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request and self.request.user.is_authenticated:
            user = self.request.user
            # Assuming you have a CustomerProfile linked to User for addresses/phone
            # For demonstration, let's use direct User fields if they exist
            self.fields['full_name'].initial = user.get_full_name() or user.username
            self.fields['email'].initial = user.email
            
            # If you have a CustomerProfile model with these fields:
            # try:
            #     customer_profile = user.customerprofile
            #     self.fields['phone_number'].initial = customer_profile.phone_number
            #     self.fields['street_address'].initial = customer_profile.address_line1
            #     self.fields['city'].initial = customer_profile.city
            #     self.fields['province'].initial = customer_profile.province
            #     self.fields['zip_code'].initial = customer_profile.zip_code
            # except User.customerprofile.RelatedObjectDoesNotExist:
            #     pass
            
    def clean(self):
        cleaned_data = super().clean()
        
        full_name = cleaned_data.get('full_name')
        email = cleaned_data.get('email')
        phone_number = cleaned_data.get('phone_number')
        street_address = cleaned_data.get('street_address')
        city = cleaned_data.get('city')
        province = cleaned_data.get('province')
        zip_code = cleaned_data.get('zip_code')

        shipping_address_combined = (
            f"Name: {full_name}\n"
            f"Email: {email}\n"
            f"Phone: {phone_number}\n"
            f"Address: {street_address}, {city}, {province}, {zip_code}"
        )
        cleaned_data['shipping_address'] = shipping_address_combined
        # For COD, typically billing address is same as shipping for simplicity unless specified
        cleaned_data['billing_address'] = shipping_address_combined 
        
        return cleaned_data