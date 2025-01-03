from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.views.generic import UpdateView, DeleteView
from permission.login import LoginAdmin
from IMS_production.models import Category, Product, StockMovement, Sale
from django.urls import reverse_lazy
from django.contrib.auth.mixins import UserPassesTestMixin
from .forms import ProductForm

#------------------------------------------------<> Category <>---------------------------------------------#

class CategoryUpdateView(LoginAdmin, UserPassesTestMixin, UpdateView):
    model = Category
    fields = ['name', 'description',]
    template_name = 'admin/categories/category_update.html'
    success_url = reverse_lazy('admin-category')
    login_url = reverse_lazy('login')

    def test_func(self):
        return self.request.user.is_admin
    
    def post(self, request, *args, **kwargs):
        category = self.get_object()
        messages.success(self.request, f"Category '{category.name}' was successfully Updated.")
        return super().post(request, *args, **kwargs)


    
class CategoryDeleteView(LoginAdmin, UserPassesTestMixin, DeleteView):
    model = Category
    fields = ['name', 'description',]
    template_name = 'admin/categories/category_delete.html'
    success_url = reverse_lazy('admin-category')
    login_url = reverse_lazy('login')
    
    def test_func(self):
        return self.request.user.is_admin
    
    def post(self, request, *args, **kwargs):
        category = self.get_object()
        messages.success(self.request, f"Category '{category.name}' was successfully removed.")
        return super().post(request, *args, **kwargs)
    

    
    
#----------------------------------------------<> Product <>---------------------------------------------#

    
class ProductUpdateView(LoginAdmin, UserPassesTestMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'admin/products/product-update.html'
    success_url = reverse_lazy('admin-product')
    login_url = reverse_lazy('login')
    
    def get_object(self, queryset=None):
        # Fetch the product instance based on SKU
        sku = self.kwargs.get('sku')
        return get_object_or_404(Product, sku=sku)
    
    def get_form(self, form_class=None):
        # Fetch the instance based on the SKU from the URL
        sku = self.kwargs.get('sku')
        product_instance = get_object_or_404(Product, sku=sku)
        
        # Pass the instance to the form
        form = super().get_form(form_class)
        form.instance = product_instance
        return form
    
    def form_valid(self, form):
        # Before saving, check if the quantity or price is greater than 0
        instance = form.save(commit=False)
        
        # Validate quantity
        if instance.quantity <= 0:
            form.add_error('quantity', 'The quantity must be greater than 0.')
            return self.form_invalid(form)
        
        # Validate price
        if instance.price <= 0:
            form.add_error('price', 'The price must be greater than 0.')
            return self.form_invalid(form)
        
        messages.success(self.request, f"Product '{instance.name}' is successful updated..!")
        # Proceed if everything is valid
        return super().form_valid(form)

    def test_func(self):
        return self.request.user.is_admin
    
class ProductDeleteView(LoginAdmin, UserPassesTestMixin, DeleteView):
    model = Product
    template_name = 'admin/products/product-delete.html'
    success_url = reverse_lazy('admin-product')
    context_object_name = 'product'
    login_url = reverse_lazy('login')
    
    def get_object(self, queryset=None):
        # Fetch the product instance based on SKU
        sku = self.kwargs.get('sku')
        return get_object_or_404(Product, sku=sku)
    
    def post(self, request, *args, **kwargs):
        # Add a success message before deleting the product
        product = self.get_object()
        messages.success(self.request, f"Product '{product.name}' was successfully removed.")
        return super().post(request, *args, **kwargs)
    
    def test_func(self):
        return self.request.user.is_admin
    
    
#-------------------------------------------------<> Stock Movement <>------------------------------------------------#



    

    
class StockMovDeleteView(LoginAdmin, UserPassesTestMixin, DeleteView):
    model = StockMovement
    template_name = 'admin/stock-movs/stock-mov-delete.html'
    success_url = reverse_lazy('admin-stock-movement')
    context_object_name = 'move'
    login_url = reverse_lazy('login')

    def test_func(self):
        return self.request.user.is_admin
    
    def post(self, request, *args, **kwargs):
        # Add a success message after deletion
        stock_movement = self.get_object()
        messages.success(
            self.request,
            f"Stock movement of {stock_movement.quantity} for product '{stock_movement.product.name}' was successfully removed..!"
        )
        return super().post(request, *args, **kwargs)
    
    
#------------------------------------------------------<> Sales Views <>-----------------------------------------------------#

class SaleDeleteView(LoginAdmin, UserPassesTestMixin, DeleteView):
    model = Sale
    template_name = 'admin/sales/sales-delete.html'
    success_url = reverse_lazy('admin-sales')
    context_object_name = 'sale'
    login_url = reverse_lazy('login')

    def test_func(self):
        return self.request.user.is_admin
    
    def post(self, request, *args, **kwargs):
        # Add a success message after deletion
        sale = self.get_object()
        messages.success(
            self.request,
            f"The sale record for product '{sale.product.name}' was successfully removed..!"
        )
        return super().post(request, *args, **kwargs)

