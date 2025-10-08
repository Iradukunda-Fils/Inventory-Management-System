from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MessageTaskViewSet, TaskExecutionLogViewSet
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


# Create router and register viewsets
router = DefaultRouter()
router.register(r'tasks', MessageTaskViewSet, basename='messagetask')
router.register(r'logs', TaskExecutionLogViewSet, basename='executionlog')

# URL patterns
urlpatterns += [
    path('whats/', views.whatsapp_view, name="whatsapp"),
    path('whats/', include(router.urls)),
]

# This generates the following endpoints:
# 
# Message Tasks:
# GET    /api/tasks/                      - List all tasks
# POST   /api/tasks/                      - Create new task
# GET    /api/tasks/{id}/                 - Retrieve task details
# PUT    /api/tasks/{id}/                 - Update task
# PATCH  /api/tasks/{id}/                 - Partial update
# DELETE /api/tasks/{id}/                 - Soft delete task
# POST   /api/tasks/batch/                - Batch create tasks
# POST   /api/tasks/{id}/cancel/          - Cancel task
# POST   /api/tasks/{id}/retry/           - Retry failed task
# GET    /api/tasks/statistics/           - Get statistics
# POST   /api/tasks/{id}/update_status/   - Manual status update
#
# Execution Logs:
# GET    /api/logs/                       - List all logs
# GET    /api/logs/{id}/                  - Retrieve log details
# GET    /api/logs/by_task/               - Get logs by task_id



# # routing.py
# from django.urls import re_path
# from .consumers import ProgressConsumer

# websocket_urlpatterns = [
#     re_path(r"ws/progress/(?P<group_name>\w+)/$", ProgressConsumer.as_asgi()),
# ]
