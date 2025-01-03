from django.shortcuts import render
from IMS_production.models import Product
from django.views.generic import ListView
from permission.login import LoginAdmin

# Create your views here.
#-----------------------------------------------------------------<> analytics  <>---------------------------------------------#


class ProductStockChartView(LoginAdmin, ListView):
    model = Product
    template_name = 'analytics.html'
    context_object_name = 'products'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Include data for the chart
        products = Product.objects.all().order_by('-updated_at') 
        context['chart_data'] = {
            'labels': [product.name for product in products],
            'data': [product.quantity for product in products],
            'categories': [product.category.name for product in products],
        }
        return context