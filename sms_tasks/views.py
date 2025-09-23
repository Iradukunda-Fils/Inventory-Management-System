from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from celery import current_app
from .models import SMSTask
from .forms import SMSTaskForm, SMSTaskFilterForm
from permission.login import LoginAdmin
import json

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
            result = send_sms.delay(task)
            
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
                send_sms.delay(task)
            tasks.update(status='running')
            messages.success(request, f'{count} tasks queued for execution!')
    
    return redirect('sms_tasks:dashboard')

# Statistics and Analytics View
@user_passes_test(is_admin)
def task_analytics(request):
    """Provide analytics data for dashboard charts"""
    from django.db.models import Count
    from datetime import datetime, timedelta
    
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