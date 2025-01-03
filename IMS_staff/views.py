from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView, ListView
from permission.login import LoginStaff, LoginAuth
from IMS_production.models import Product, Category, Sale, SalesSummary, StockMovement
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from django.contrib.auth import logout
from django.contrib import messages
from django.db.models import Q
from django.utils.dateparse import parse_date

User = get_user_model()

# Create your views here.

class StaffDashboardView(LoginStaff, TemplateView):
    login_url = 'login'
    template_name = 'staff/home.html'
    success_url  = reverse_lazy('login')
    

class ProductView(LoginStaff, ListView):
    model = Product
    template_name = 'staff/product.html'
    context_object_name = 'products'
    success_url  = reverse_lazy('login')
    
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('category')
        
        # Get the search query from the GET parameters
        search_query = self.request.GET.get('q', '').strip()

        if search_query:
            try:
                # Try parsing the search query as a date (YYYY-MM-DD)
                search_date = parse_date(search_query)
                if search_date:
                    queryset = queryset.filter(Q(created_at=search_date) | Q(updated_at__date=search_date))
                else:
                    # Apply filters for other fields if not a valid date
                    queryset = queryset.filter(
                        Q(name__icontains=search_query) |
                        Q(sku__icontains=search_query) |
                        Q(category__name__icontains=search_query)
                    )
            except:
                return messages.error(self.request, 'Invalid date you must enter date in YYYY-MM-DD format')

        return queryset
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get('q', '')
        context['search_query'] = search_query
    
        # Add a message if the search query is empty
        if search_query == '':
            context['placeholder'] = "Search product, sku, category or date created or updated.. (YYYY-MM-DD)..."
    
        return context
    
class CategoryView(LoginStaff, ListView):
    model = Category
    template_name = 'staff/category.html'
    context_object_name = 'categories'
    success_url  = reverse_lazy('login')
    
    def get_queryset(self):
        queryset = super().get_queryset()

        # Get the search query from the GET parameters
        search_query = self.request.GET.get('q', '')

        if search_query:
            # Filter users based on username, email, or role
            queryset = queryset.filter(name__icontains=search_query)
        return queryset
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get('q', '')
        context['search_query'] = search_query
    
        # Add a message if the search query is empty
        if search_query == '':
            context['placeholder'] = "Search with category name...."
    
        return context
    
class SalesView(LoginStaff, ListView):
    model = Sale
    template_name = 'staff/sales.html'
    context_object_name = 'sales'
    success_url  = reverse_lazy('login')
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('product')
        
        # Get the search query from the GET parameters
        search_query = self.request.GET.get('q', '').strip()

        if search_query:
            try:
                # Try parsing the search query as a date (YYYY-MM-DD)
                search_date = parse_date(search_query)
                if search_date:
                    queryset = queryset.filter(Q(created_at__date=search_date) | Q(sale_date=search_date))
                else:
                    # Apply filters for other fields if not a valid date
                    queryset = queryset.filter(
                        Q(product__name__icontains=search_query) |
                        Q(quantity__icontains=search_query) |
                        Q(sale_price__icontains=search_query) |
                        Q(total_amount__icontains=search_query)
                    )
            except:
                return messages.error(self.request, 'Invalid date you must enter date in YYYY-MM-DD format')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Retrieve the current search query
        search_query = self.request.GET.get('q', '').strip()
        context['search_query'] = search_query
        
        # Add a placeholder for the search bar
        context['placeholder'] = (
            "Search product, price, quantity, total, created_at or date registered (YYYY-MM-DD)..."
        )
        
        return context
    
class SalesSummaryView(LoginStaff, ListView):
    model = SalesSummary
    template_name = 'staff/sales-summary.html'
    context_object_name = 'summaries'
    success_url  = reverse_lazy('login')
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('product')
        
        # Get the search query from the GET parameters
        search_query = self.request.GET.get('q', '').strip()

        if search_query:
            try:
                # Try parsing the search query as a date (YYYY-MM-DD)
                search_date = parse_date(search_query)
                if search_date:
                    queryset = queryset.filter(report_date__date=search_date)
                else:
                    # Apply filters for other fields if not a valid date
                    queryset = queryset.filter(
                        Q(product__name__icontains=search_query) |
                        Q(total_sold__icontains=search_query) |
                        Q(total_revenue__icontains=search_query)
                    )
            except:
                return messages.error(self.request, 'Invalid date you must enter date in YYYY-MM-DD format')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Retrieve the current search query
        search_query = self.request.GET.get('q', '').strip()
        context['search_query'] = search_query
        
        # Add a placeholder for the search bar
        context['placeholder'] = (
            "Search product, total sold, revenue or report date (YYYY-MM-DD)..."
        )
        
        return context
    
class StockMovementView(LoginStaff, ListView):
    model = StockMovement
    template_name = 'staff/stock-movement.html'
    context_object_name = 'movements'
    success_url  = reverse_lazy('login')
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('product')

        # Get the search query from the GET parameters
        search_query = self.request.GET.get('q', '')
        
        if search_query:
            try:
                # Try parsing the search query as a date (YYYY-MM-DD)
                search_date = parse_date(search_query)
                if search_date:
                    queryset = queryset.filter(created_at__date=search_date)
                else:
                    # Apply filters for other fields if not a valid date
                    queryset = queryset.filter(Q(product_name__icontains=search_query) |
                                       Q(movement_type=search_query) |
                                       Q(quantity=search_query)
                                       )
            except:
                return messages.error(self.request, 'Invalid date you must enter date in YYYY-MM-DD format')

        return queryset
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get('q', '')
        context['search_query'] = search_query
    
        # Add a message if the search query is empty
        if search_query == '':
            context['placeholder'] = "Search product, type, quantity or date (YYYY-MM-DD)..."
    
        return context


class LogoutView(LoginAuth, View):
    login_url = reverse_lazy('login')
    tempelate_name = 'logout.html'
    success_url  = reverse_lazy('login')
    
    def get(self, request):
        return render(request,self.tempelate_name)
    
    def post(self, request):
        logout(request)
        messages.success(request, "You have been successfully logged out.")
        return redirect(self.success_url)

    
    
    
    