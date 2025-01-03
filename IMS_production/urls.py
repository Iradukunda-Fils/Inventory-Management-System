from django.urls import path
from .views import ProductStockChartView


urlpatterns = [ 
    path('analytics/', ProductStockChartView.as_view(), name='analytics'),
]
