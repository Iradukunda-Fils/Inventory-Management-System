
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.shortcuts import render,redirect
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from .models import SMSTask
from .forms import SMSTaskForm, SMSTaskFilterForm
from permission.login import LoginAdmin
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from .models import MessageTask, TaskExecutionLog
from .serializers import (
    MessageTaskListSerializer,
    MessageTaskDetailSerializer,
    MessageTaskCreateSerializer,
    MessageTaskUpdateSerializer,
    BatchMessageTaskCreateSerializer,
    TaskExecutionLogSerializer,
    TaskStatusUpdateSerializer,
    TaskStatisticsSerializer
)

# Utility functions
def is_admin(user):
    return user.is_authenticated and user.is_admin

class AdminRequiredMixin(LoginAdmin, UserPassesTestMixin):
    def test_func(self):
        return is_admin(self.request.user)

# Main Dashboard View
class SMSTaskListView(AdminRequiredMixin, ListView):
    model = SMSTask
    template_name = 'sms_tasks/dashboard.html'
    context_object_name = 'tasks'
    paginate_by = 20

    def get_queryset(self):
        queryset = SMSTask.objects.select_related('periodic_task', 'created_by').all()
        
        # Apply filters
        form = SMSTaskFilterForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            status = form.cleaned_data.get('status')
            send_type = form.cleaned_data.get('send_type')
            is_active = form.cleaned_data.get('is_active')
            
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(phone_numbers__icontains=search) |
                    Q(message__icontains=search) |
                    Q(sender__icontains=search)
                )
            
            if status:
                queryset = queryset.filter(status=status)
            
            if send_type:
                queryset = queryset.filter(send_type=send_type)
            
            if is_active:
                queryset = queryset.filter(is_active=(is_active == 'true'))
        
        # Apply sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        valid_sorts = ['name', '-name', 'status', '-status', 'created_at', '-created_at', 
                      'last_execution', '-last_execution', 'execution_count', '-execution_count']
        if sort_by in valid_sorts:
            queryset = queryset.order_by(sort_by)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = SMSTaskFilterForm(self.request.GET)
        context['total_tasks'] = SMSTask.objects.count()
        context['active_tasks'] = SMSTask.objects.filter(is_active=True).count()
        context['pending_tasks'] = SMSTask.objects.filter(status='pending').count()
        return context

# Create Task View
class SMSTaskCreateView(AdminRequiredMixin, CreateView):
    model = SMSTask
    form_class = SMSTaskForm
    template_name = 'sms_tasks/task_form.html'
    success_url = reverse_lazy('sms_tasks:dashboard')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)

        
        # Handle immediate sending
        if form.cleaned_data.get('schedule_type') == 'immediate':
            self._send_immediate_sms(form.instance)
        
        messages.success(
            self.request, 
            f'SMS Task "{form.instance.name}" created successfully!'
        )
        return response


    def _send_immediate_sms(self, task_instance):
        """Send SMS immediately using Celery task"""
        from sms_tasks.tasks import send_sms
        send_sms.delay(task_instance.id)

# Update Task View
class SMSTaskUpdateView(AdminRequiredMixin, UpdateView):
    model = SMSTask
    form_class = SMSTaskForm
    template_name = 'sms_tasks/task_form.html'
    success_url = reverse_lazy('sms_tasks:dashboard')

    def get_initial(self):
        initial = super().get_initial()
        
        # Set schedule type based on existing periodic task
        if self.object.periodic_task:
            if self.object.periodic_task.interval:
                initial['schedule_type'] = 'interval'
                initial['interval_every'] = self.object.periodic_task.interval.every
                initial['interval_period'] = self.object.periodic_task.interval.period
            elif self.object.periodic_task.crontab:
                initial['schedule_type'] = 'crontab'
                cron = self.object.periodic_task.crontab
                initial.update({
                    'cron_minute': cron.minute,
                    'cron_hour': cron.hour,
                    'cron_day_of_week': cron.day_of_week,
                    'cron_day_of_month': cron.day_of_month,
                    'cron_month_of_year': cron.month_of_year,
                })
        else:
            initial['schedule_type'] = 'immediate'
        
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'SMS Task "{form.instance.name}" updated successfully!'
        )
        return response

# Delete Task View
class SMSTaskDeleteView(AdminRequiredMixin, DeleteView):
    model = SMSTask
    template_name = 'sms_tasks/task_confirm_delete.html'
    success_url = reverse_lazy('sms_tasks:dashboard')

    def delete(self, request, *args, **kwargs):
        task = self.get_object()
        task_name = task.name
        
        # Delete associated periodic task
        if task.periodic_task:
            task.periodic_task.delete()
        
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'SMS Task "{task_name}" deleted successfully!')
        return response

# AJAX Views for dynamic interactions
@user_passes_test(is_admin)
def toggle_task_status(request, pk):
    """Toggle task active/inactive status via AJAX"""
    if request.method == 'POST':
        task = get_object_or_404(SMSTask, pk=pk)
        is_active = task.toggle_active()
        
        return JsonResponse({
            'success': True,
            'is_active': is_active,
            'message': f'Task {"activated" if is_active else "deactivated"} successfully!'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@user_passes_test(is_admin)
def run_task_now(request, pk):
    """Run task immediately via AJAX"""
    if request.method == 'POST':
        task = get_object_or_404(SMSTask, pk=pk)
        
        try:
            from sms_tasks.tasks import send_sms
            result = send_sms.delay(task.id)
            
            # Update task status
            task.status = 'running'
            task.save()
            
            return JsonResponse({
                'success': True,
                'task_id': result.id,
                'message': f'Task "{task.name}" started successfully!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Failed to start task: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@user_passes_test(is_admin)
def get_task_status(request, pk):
    """Get current task status via AJAX"""
    task = get_object_or_404(SMSTask, pk=pk)
    
    return JsonResponse({
        'status': task.status,
        'execution_count': task.execution_count,
        'success_count': task.success_count,
        'failed_count': task.failed_count,
        'last_execution': task.last_execution.isoformat() if task.last_execution else None,
        'is_active': task.is_active
    })

@user_passes_test(is_admin)
def bulk_actions(request):
    """Handle bulk actions for multiple tasks"""
    if request.method == 'POST':
        action = request.POST.get('action')
        task_ids = request.POST.getlist('selected_tasks')
        
        if not task_ids:
            messages.error(request, 'No tasks selected.')
            return redirect('sms_tasks:dashboard')
        
        tasks = SMSTask.objects.filter(id__in=task_ids)
        count = tasks.count()
        
        if action == 'activate':
            tasks.update(is_active=True)
            # Update periodic tasks
            for task in tasks:
                if task.periodic_task:
                    task.periodic_task.enabled = True
                    task.periodic_task.save()
            messages.success(request, f'{count} tasks activated successfully!')
            
        elif action == 'deactivate':
            tasks.update(is_active=False)
            # Update periodic tasks
            for task in tasks:
                if task.periodic_task:
                    task.periodic_task.enabled = False
                    task.periodic_task.save()
            messages.success(request, f'{count} tasks deactivated successfully!')
            
        elif action == 'delete':
            # Delete periodic tasks first
            for task in tasks:
                if task.periodic_task:
                    task.periodic_task.delete()
            tasks.delete()
            messages.success(request, f'{count} tasks deleted successfully!')
            
        elif action == 'run_now':
            from sms_tasks.tasks import send_sms
            for task in tasks:
                send_sms.delay(task.id)
            tasks.update(status='running')
            messages.success(request, f'{count} tasks queued for execution!')
    
    return redirect('sms_tasks:dashboard')

# Statistics and Analytics View
@user_passes_test(is_admin)
def task_analytics(request):
    """Provide analytics data for dashboard charts"""
    from django.db.models import Count
    from datetime import timedelta
    
    # Status distribution
    status_data = list(SMSTask.objects.values('status').annotate(count=Count('id')))
    
    # Tasks created over time (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_tasks = SMSTask.objects.filter(
        created_at__gte=thirty_days_ago
    ).extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(count=Count('id')).order_by('day')
    
    # Execution statistics
    total_executions = sum(task.execution_count for task in SMSTask.objects.all())
    total_success = sum(task.success_count for task in SMSTask.objects.all())
    total_failed = sum(task.failed_count for task in SMSTask.objects.all())
    
    return JsonResponse({
        'status_distribution': status_data,
        'daily_tasks': list(daily_tasks),
        'execution_stats': {
            'total_executions': total_executions,
            'total_success': total_success,
            'total_failed': total_failed,
            'success_rate': round((total_success / total_executions * 100) if total_executions > 0 else 0, 2)
        }
    })


from .tasks import send_whatsapp
import logging

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination configuration."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500

from .tasks import send_whatsapp
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


class MessageTaskViewSet(viewsets.ModelViewSet):
    """
    Advanced task management with Celery, WebSocket notifications,
    and optional scheduled/recurring sending.
    """

    queryset = MessageTask.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'status': ['exact', 'in'],
        'priority': ['exact', 'gte', 'lte'],
        'scheduled_time': ['gte', 'lte'],
        'created_at': ['gte', 'lte'],
        'recipient': ['exact', 'icontains'],
    }
    search_fields = ['recipient', 'message_body', 'error_message']
    ordering_fields = ['created_at', 'scheduled_time', 'priority', 'updated_at', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return MessageTaskListSerializer
        elif self.action == 'create':
            return MessageTaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MessageTaskUpdateSerializer
        return MessageTaskDetailSerializer

    def get_queryset(self):
        """Optimize queryset with prefetch for detail views."""
        queryset = super().get_queryset()
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('execution_logs')
        return queryset

    # -------------------------------------------------------------------------
    # 🧩 Helper methods
    # -------------------------------------------------------------------------
    def enqueue_task(self, task):
        """
        Enqueue the Celery task and send a WebSocket notification.
        """
        try:
            priority = max(0, min(9, task.priority))
            send_whatsapp.apply_async(args=[str(task.id)], priority=priority)

            task.status = MessageTask.Status.QUEUED
            task.save(update_fields=['status', 'updated_at'])

            self.broadcast_status(task, "queued")
            logger.info(f"Enqueued task {task.id} with priority {priority}")
            return True
        except Exception as e:
            logger.exception(f"Failed to enqueue task {task.id}: {e}")
            return False

    def broadcast_status(self, task, event_type):
        """
        Notify WebSocket groups about status updates.
        """
        pass
        # channel_layer = get_channel_layer()
        # payload = {
        #     "type": "progress.update",
        #     "data": {
        #         "task_id": str(task.id),
        #         "status": task.status,
        #         "recipient": task.recipient,
        #         "progress": getattr(task, "progress", None),
        #         "message_body": task.message_body,
        #     }
        # }
        # groups = [f"user_{task.created_by_id}", "admin_group"]
        # for group in groups:
        #     try:
        #         async_to_sync(channel_layer.group_send)(group, payload)
        #     except Exception as e:
        #         logger.warning(f"Failed to send WebSocket update for {task.id}: {e}")

    # -------------------------------------------------------------------------
    # 🧩 Core operations
    # -------------------------------------------------------------------------
    def perform_create(self, serializer):
        """
        Create a task. 
        If scheduled_time is in the future, delay execution using Celery.
        Otherwise, enqueue immediately.
        """
        task = serializer.save(created_by=self.request.user)
        now = timezone.now()

        # 🕒 Future scheduled task
        if task.scheduled_time > now:
            try:
                priority = max(0, min(9, task.priority))
                send_whatsapp.apply_async(
                    args=[str(task.id)],
                    priority=priority,
                    eta=task.scheduled_time  # schedule execution at this time
                )
                task.status = MessageTask.Status.PENDING
                task.save(update_fields=['status', 'updated_at'])
                self.broadcast_status(task, "scheduled")
                logger.info(
                    f"Scheduled task {task.id} for {task.scheduled_time} (priority {priority})"
                )
            except Exception as e:
                logger.exception(f"Failed to schedule future task {task.id}: {e}")
                task.status = MessageTask.Status.FAILED
                task.error_message = str(e)
                task.save(update_fields=['status', 'error_message', 'updated_at'])
                self.broadcast_status(task, "failed")

        # 🚀 Immediate execution (scheduled_time <= now)
        else:
            self.enqueue_task(task)

        logger.info(f"Created task {task.id} for {task.recipient}")

    def perform_destroy(self, instance):
        """Soft delete instead of hard delete."""
        instance.soft_delete()
        self.broadcast_status(instance, "deleted")
        logger.info(f"Soft deleted task {instance.id}")

    @action(detail=False, methods=['post'])
    def batch(self, request):
        """Batch create multiple tasks."""
        serializer = BatchMessageTaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tasks = serializer.save()

        now = timezone.now()
        enqueued_count = 0
        for task in tasks:
            if task.scheduled_time <= now and self.enqueue_task(task):
                enqueued_count += 1

        return Response({
            'created': len(tasks),
            'enqueued': enqueued_count,
            'task_ids': [str(t.id) for t in tasks]
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending or queued task."""
        task = self.get_object()

        if task.status not in [MessageTask.Status.PENDING, MessageTask.Status.QUEUED]:
            return Response(
                {'error': f'Cannot cancel task with status: {task.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            task.status = MessageTask.Status.CANCELLED
            task.save(update_fields=['status', 'updated_at'])

        self.broadcast_status(task, "cancelled")
        logger.info(f"Cancelled MessageTask {task.id}")
        return Response({'status': 'cancelled', 'task_id': str(task.id)})

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed task."""
        task = self.get_object()

        if not task.can_retry():
            return Response(
                {'error': 'Task is not eligible for retry'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            task.status = MessageTask.Status.PENDING
            task.error_message = None
            task.scheduled_time = timezone.now()
            task.save(update_fields=['status', 'error_message', 'scheduled_time', 'updated_at'])

        if self.enqueue_task(task):
            self.broadcast_status(task, "retrying")
            return Response({'status': 'queued', 'task_id': str(task.id)})
        else:
            return Response({'error': 'Failed to enqueue task'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get dashboard statistics."""
        queryset = self.filter_queryset(self.get_queryset())
        status_counts = queryset.values('status').annotate(count=Count('id'))

        stats = {s: 0 for s in ['pending', 'queued', 'processing', 'completed', 'failed', 'retrying', 'cancelled']}
        stats['total'] = queryset.count()
        for item in status_counts:
            stats[item['status']] = item['count']

        total_finished = stats['completed'] + stats['failed']
        stats['success_rate'] = round((stats['completed'] / total_finished) * 100, 2) if total_finished else 0.0

        avg_time = TaskExecutionLog.objects.filter(task__in=queryset).aggregate(avg=Avg('execution_time_ms'))
        stats['avg_execution_time_ms'] = round(avg_time['avg'], 2) if avg_time['avg'] else None
        stats['total_retries'] = queryset.aggregate(Sum('retries'))['retries__sum'] or 0

        serializer = TaskStatisticsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Manually update task status."""
        task = self.get_object()
        serializer = TaskStatusUpdateSerializer(instance=task, data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        reason = serializer.validated_data.get('reason', '')

        with transaction.atomic():
            task.status = new_status
            if reason:
                task.error_message = f"Manual update: {reason}"
            task.save(update_fields=['status', 'error_message', 'updated_at'])

        self.broadcast_status(task, "manual_update")
        logger.info(f"Manually updated MessageTask {task.id} to {new_status}")
        return Response(MessageTaskDetailSerializer(task).data)



class TaskExecutionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for execution logs.
    
    Endpoints:
    - GET /api/logs/ - List all logs with filtering
    - GET /api/logs/{id}/ - Retrieve specific log
    """
    
    queryset = TaskExecutionLog.objects.all()
    serializer_class = TaskExecutionLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    
    filterset_fields = {
        'task': ['exact'],
        'status': ['exact', 'in'],
        'timestamp': ['gte', 'lte'],
        'execution_time_ms': ['gte', 'lte']
    }
    
    ordering_fields = ['timestamp', 'execution_time_ms']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """Optimize query with select_related."""
        return super().get_queryset().select_related('task')
    
    @action(detail=False, methods=['get'])
    def by_task(self, request):
        """
        Get logs for a specific task.
        
        GET /api/logs/by_task/?task_id={uuid}
        """
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response(
                {'error': 'task_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logs = self.get_queryset().filter(task_id=task_id)
        page = self.paginate_queryset(logs)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)


def whatsapp_view(request):
    return render(request, "whatsapp/index.html")