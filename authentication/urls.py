from django.urls import path
from .views import RegistrationView,AuthLoginView,UserUpdateView,UserDeleteView,LogoutView

urlpatterns = [
    path('',AuthLoginView.as_view(template_name='authentication/login.html'), name='login'),
    path('registration/',RegistrationView.as_view(),name='register'),
    path('user-update/<str:user>/', UserUpdateView.as_view(), name='update-user'),
    path('user-delete/<int:pk>/', UserDeleteView.as_view(), name='delete-user'),
]