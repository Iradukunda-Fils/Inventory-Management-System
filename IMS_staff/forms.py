from django import forms
from IMS_production.models import Product, Category,StockMovement,Sale
from django.db.models import F
from django.core.exceptions import ValidationError

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'price', 'quantity', ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize the 'category' field to show options from the Category table
        category = Category.objects.all()
        self.fields['category'].queryset = category
        self.fields['category'].label_from_instance = lambda obj: f"{obj.name}"
        
class StockMovForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'movement_type', 'quantity', 'reason']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter and annotate products for the dropdown
        products = Product.objects.annotate(category_name=F('category__name')).order_by('-created_at', '-updated_at')
        self.fields['product'].queryset = products
        self.fields['product'].label_from_instance = lambda obj: f"{obj.name} ({obj.category_name})"

        # # Apply Bootstrap classes
        # self.fields['product'].widget.attrs.update({'class': 'form-select'})
        # self.fields['movement_type'].widget.attrs.update({'class': 'form-select'})
        # self.fields['quantity'].widget.attrs.update({'class': 'form-control'})
        # self.fields['reason'].widget.attrs.update({'class': 'form-control'})
        
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        movement_type = cleaned_data.get('movement_type')

        # Validate quantity
        if quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be greater than 0.'})

        # Validate stock subtraction
        if movement_type == 'Subtraction' and product and product.quantity < quantity:
            raise ValidationError({'quantity': f"Not enough stock available. Current stock: {product.quantity}"})

        return cleaned_data
    
    
        
class SalesForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ('product', 'quantity', 'sale_price', 'total_revenue', 'sale_date')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter and annotate products for the dropdown
        products = Product.objects.select_related('category').annotate(category_name=F('category__name')).order_by('-created_at', '-updated_at')
        self.fields['product'].queryset = products
        self.fields['product'].label_from_instance = lambda obj: f"{obj.name} ({obj.category_name})"
    
        


