from django.urls import path
from .views import SendSMSView
from .listviews import (AdminView,ProductView,
                    UsersView,CategoryView,
                    SalesSummaryView,SalesView,
                    StockMovementView,LogoutView
                    )
from .converter import (
    CategoryUpdateView,CategoryDeleteView,
    ProductUpdateView,ProductDeleteView,StockMovDeleteView,
    SaleDeleteView,
)

urlpatterns = [
    path('', AdminView.as_view(), name='admin-dashboard'),
    path('list-users/', UsersView.as_view(), name='list-users'),
    path('category/', CategoryView.as_view(), name='admin-category'),
    path('products/', ProductView.as_view(), name='admin-product'),
    path('stock-movement/', StockMovementView.as_view(), name='admin-stock-movement'),
    path('sales/', SalesView.as_view(), name='admin-sales'),
    path('sales-summary/', SalesSummaryView.as_view(), name='admin-sales-summary'),
    path('logout/', LogoutView.as_view(), name='admin-logout'),
    path("send-sms/", SendSMSView.as_view(), name="send_sms"),
]


#--------------------------------<> Updates <>-------------------------------------#

urlpatterns += [
    path('update-category/<int:pk>/', CategoryUpdateView.as_view(), name='admin-update-category'),
    path('update-product/<str:sku>/', ProductUpdateView.as_view(), name='update-product'),
]

#----------------------------------<> Delete <>-------------------------------------#

urlpatterns += [
    path('remove-category/<int:pk>/', CategoryDeleteView.as_view(), name='admin-delete-category'),
    path('remove-product/<str:sku>/', ProductDeleteView.as_view(), name='admin-delete-product'),
    path('remove-stock-movement/<int:pk>/', StockMovDeleteView.as_view(), name='admin-delete-stock-movement'),
    path('remove-sale/<int:pk>/', SaleDeleteView.as_view(), name='admin-delete-sale'),
]

