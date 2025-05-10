from django import forms
from .models import PurchaseOrder
from apps.inventory.models import Product
from apps.suppliers.models import Supplier
class PurchaseOrderForm(forms.ModelForm):
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all(), empty_label="Select a supplier")
    product = forms.ModelChoiceField(queryset=Product.objects.all(), empty_label="Select a product")
    quantity = forms.IntegerField(min_value=1)
    expected_delivery = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'product', 'quantity', 'expected_delivery', 'status']
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        quantity = cleaned_data.get("quantity")
        if product and quantity:
            # For purchase orders, generally no stock quantity limit to validate,
            # since you are adding stock, not taking from existing.
            pass
        return cleaned_data

