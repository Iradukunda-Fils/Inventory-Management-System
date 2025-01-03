from django.contrib import messages
from django.views.generic import CreateView
from permission.login import LoginStaff
from IMS_production.models import Category, Sale, StockMovement
from django.urls import reverse_lazy
from django.contrib.auth.mixins import UserPassesTestMixin
from .forms import ProductForm, StockMovForm, SalesForm


#--------------------------------------------------<> Product <>--------------------------------------------#


class ProductCreateView(LoginStaff, UserPassesTestMixin, CreateView):
    form_class = ProductForm
    template_name = 'staff/products/product-create.html'  # Adjust if you have a custom template
    success_url = reverse_lazy('staff-product')  # Redirect after successful creation
    login_url = reverse_lazy('login')

    def form_valid(self, form):
        # Generate SKU before saving
        instance = form.save(commit=False)# Ensure SKU is only generated if it doesn't already exist
        if instance.quantity > 0:
            if instance.price > 0:
                instance.sku = instance.generate_sku()
                instance.save()  # Save the product instance
            else:
                form.add_error('price','The price must be greater than 0..')
                return self.form_invalid(form)
        else:
            form.add_error('quantity','The quantity must be greater than 0..')
            return self.form_invalid(form)
        super().form_valid(form)
        messages.success(
            self.request, f"Product '{self.object.name}' with category '{self.object.category.name}' was successfully created!"
        )
        return super().form_valid(form)

    def test_func(self):
        return not self.request.user.is_admin  # Example: Only allow staff to create products
    
    


#----------------------------------------------------------<> Category <>-----------------------------------------------------#

class CategoryCreateView(LoginStaff, UserPassesTestMixin, CreateView):
    model = Category
    fields = ['name', 'description']
    template_name = 'staff/categories/category_create.html'
    success_url = reverse_lazy('staff-category')
    login_url = reverse_lazy('login')
    
    
    def form_valid(self, form):
        # Add a success message after category creation
        response = super().form_valid(form)
        messages.success(
            self.request, f"Category '{self.object.name}' was successfully created!"
        )
        return response
    
    def test_func(self):
        return not self.request.user.is_admin             
    
#-----------------------------------------------<> Stock Movement <>----------------------------------------------#
    
class StockMovCreateView(LoginStaff, UserPassesTestMixin, CreateView):
    model = StockMovement
    form_class = StockMovForm
    template_name = 'staff/stock-movs/stock-mov-create.html'
    success_url = reverse_lazy('staff-stock-movement')
    login_url = reverse_lazy('login')

    def test_func(self):
        return not self.request.user.is_admin  # Only allow admin users to create stock movements

    def form_valid(self, form):
        product = form.cleaned_data['product']
        quantity = form.cleaned_data['quantity']
        movement_type = form.cleaned_data['movement_type']

        # Update stock in product table
        if movement_type == 'Addition':
            product.quantity += quantity
        elif movement_type == 'Subtraction':
            product.quantity -= quantity
        product.save()

        # Call parent form_valid and add success message
        messages.success(
            self.request, f"Stock Movement for '{product.name}' was successfully registered!"
        )
        return super().form_valid(form)
    
#-------------------------------------------------<> Sales Form <>-------------------------------------------------#
    
class SaleCreateView(LoginStaff, UserPassesTestMixin, CreateView):
    model = Sale
    form_class = SalesForm
    template_name = 'staff/sales/sale-create.html'
    success_url = reverse_lazy('staff-sales')
    login_url = reverse_lazy('login')

    def test_func(self):
        return not self.request.user.is_admin  # Only allow admin users to create stock movements

    def form_valid(self, form):
        # Access cleaned data
        quantity = form.cleaned_data['quantity']
        sales_price = form.cleaned_data['sale_price']
        product = form.cleaned_data['product']
    
        # update product quantity based on sale quantity
        if product.quantity >= quantity and quantity > 0:
            if product.price < sales_price and sales_price > 0:
                product.quantity -= quantity
                product.save()
            else:
                # Add error for invalid quantity
                form.add_error('sale_price', f'Price less than purchase: {product.price}')
                return self.form_invalid(form)
        else:
                # Add error for invalid quantity
                form.add_error('quantity', f'Quantity not found, available is: {product.quantity}')
                return self.form_invalid(form)
    
        return super().form_valid(form)