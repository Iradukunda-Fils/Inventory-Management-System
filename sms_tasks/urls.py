from django.urls import path
from . import views

app_name = 'sms_tasks'

urlpatterns = [
    # Main dashboard and CRUD operations
    path('', views.SMSTaskListView.as_view(), name='dashboard'),
    path('create/', views.SMSTaskCreateView.as_view(), name='create_task'),
    path('<int:pk>/edit/', views.SMSTaskUpdateView.as_view(), name='edit_task'),
    path('<int:pk>/delete/', views.SMSTaskDeleteView.as_view(), name='delete_task'),
    
    # AJAX endpoints for dynamic interactions
    path('ajax/toggle/<int:pk>/', views.toggle_task_status, name='toggle_task'),
    path('ajax/run/<int:pk>/', views.run_task_now, name='run_task_now'),
    path('ajax/status/<int:pk>/', views.get_task_status, name='get_task_status'),
    path('ajax/analytics/', views.task_analytics, name='task_analytics'),
    
    # Bulk operations
    path('bulk-actions/', views.bulk_actions, name='bulk_actions'),
]