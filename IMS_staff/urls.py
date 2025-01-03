from django.urls import path
from .views import (StaffDashboardView,ProductView,CategoryView,
                    SalesSummaryView,SalesView,
                    StockMovementView,LogoutView)
from .converter import (
    CategoryCreateView,
    ProductCreateView,
    StockMovCreateView,
    SaleCreateView
)

urlpatterns = [
    path('', StaffDashboardView.as_view(), name='staff-dashboard'),
    path('category/', CategoryView.as_view(), name='staff-category'),
    path('products/', ProductView.as_view(), name='staff-product'),
    path('stock-movement/', StockMovementView.as_view(), name='staff-stock-movement'),
    path('sales/', SalesView.as_view(), name='staff-sales'),
    path('sales-summary/', SalesSummaryView.as_view(), name='staff-sales-summary'),
    path('logout/', LogoutView.as_view(), name='staff-logout'),
]

#-------------------------------------<> Create <>-------------------------------------#

urlpatterns +=[
    path('create-category/', CategoryCreateView.as_view(), name='staff-create-category'),
    path('add-product/', ProductCreateView.as_view(), name='staff-create-product'),
    path('add-stock-movement/', StockMovCreateView.as_view(), name='staff-add-stock-movement'),
    path('add-sale/', SaleCreateView.as_view(), name='staff-add-sale'),
]