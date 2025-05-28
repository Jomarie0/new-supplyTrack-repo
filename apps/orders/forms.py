from django import forms
from .models import Order
from apps.inventory.models import Product
from apps.suppliers.models import Supplier

class OrderForm(forms.ModelForm):
    product = forms.ModelChoiceField(queryset=Product.objects.all(), empty_label="Select a product")
    quantity = forms.IntegerField(min_value=1)
    expected_delivery = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )

    class Meta:
        model = Order
        fields = ['product', 'quantity', 'unit_price', 'expected_delivery', 'status', 'order_date', 'customer']

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        quantity = cleaned_data.get("quantity")

        if product and quantity:
            if quantity > product.stock_quantity:
                raise forms.ValidationError(f"Only {product.stock_quantity} items in stock.")

        return cleaned_data


