from django import forms
from IMS_production.models import Product, Category

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
        self.fields['category'].widget.attrs.update({'class': 'form-select'})  # Add Bootstrap styling
        
