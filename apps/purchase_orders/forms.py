# apps/purchasing/forms.py

from django import forms
from .models import PurchaseOrder, PurchaseOrderItem # Import PurchaseOrderItem too
from apps.inventory.models import Product # Adjust import for ProductVariant
from apps.store.models import ProductVariant # Adjust import for ProductVariant
from apps.suppliers.models import Supplier

class PurchaseOrderForm(forms.ModelForm):
    # These fields are now direct attributes of PurchaseOrder
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all(), empty_label="Select a supplier")
    # No product, quantity, unit_price here anymore
    expected_delivery_date = forms.DateField( # Renamed from expected_delivery
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    
    class Meta:
        model = PurchaseOrder
        # Only include fields that are direct attributes of the PurchaseOrder model
        fields = ['supplier', 'expected_delivery_date', 'status', 'notes'] # Added notes field
        widgets = {
            'status': forms.Select(choices=PurchaseOrder.PO_STATUS_CHOICES),
            'order_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}), # If you want to manually set order_date
        }
        # If order_date is auto_now_add, you don't need it in fields for creation.
        # If it's just default=timezone.now, you might want it in fields for editing.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply styling to all fields
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

        # If this form is used for adding, hide received_date field if you add it to fields
        # if not self.instance.pk: # If it's a new instance
        #     if 'received_date' in self.fields:
        #         self.fields['received_date'].widget = forms.HiddenInput()

    # The clean method for product/quantity validation is no longer needed here
    # as those are on PurchaseOrderItem
    # def clean(self):
    #     cleaned_data = super().clean()
    #     # ... (removed product/quantity validation) ...
    #     return cleaned_data

# You will likely need a formset for PurchaseOrderItems if you manage them outside admin
# from django.forms import inlineformset_factory
# PurchaseOrderItemFormSet = inlineformset_factory(
#     PurchaseOrder, PurchaseOrderItem, fields=('product_variant', 'quantity_ordered', 'unit_cost'), extra=1
# )