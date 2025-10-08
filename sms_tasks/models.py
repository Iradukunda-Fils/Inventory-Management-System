# models.py
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django_celery_beat.models import PeriodicTask
from django.core.validators import RegexValidator
from django.conf import settings
import uuid
from django.utils import timezone

class SMSTask(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('disabled', 'Disabled'),
    ]
    
    SEND_TYPE_CHOICES = [
        ('immediate', 'Immediate'),
        ('single', 'Single SMS'),
        ('bulk', 'Bulk SMS'),
    ]

    name = models.CharField(max_length=200, unique=True)
    phone_numbers = models.TextField(help_text="Comma-separated phone numbers for bulk SMS")
    message = models.TextField(max_length=1000)
    sender = models.CharField(max_length=100, default="System")
    send_type = models.CharField(max_length=10, choices=SEND_TYPE_CHOICES, default='single')
    
    # Task scheduling
    periodic_task = models.OneToOneField(PeriodicTask, on_delete=models.CASCADE, null=True, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    last_execution = models.DateTimeField(null=True, blank=True)
    execution_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(getattr(settings, "AUTH_USER_MODEL"), on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    
    # Additional options
    retry_count = models.PositiveIntegerField(default=3)
    options = models.JSONField(default=dict, blank=True)  # Store additional SMS options

    class Meta:
        db_table = 'sms_tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_send_type_display()})"

    def get_phone_list(self):
        """Return list of phone numbers"""
        return [phone.strip() for phone in self.phone_numbers.split(',') if phone.strip()]

    def get_message_preview(self):
        """Return truncated message for display"""
        return self.message[:50] + "..." if len(self.message) > 50 else self.message

    @property
    def schedule_info(self):
        """Get schedule information"""
        if not self.periodic_task:
            return "Immediate"
        
        task = self.periodic_task
        if task.interval:
            return f"Every {task.interval}"
        elif task.crontab:
            return f"Cron: {task.crontab}"
        return "Custom Schedule"

    def toggle_active(self):
        """Toggle task active status and sync with periodic task"""
        self.is_active = not self.is_active
        if self.periodic_task:
            self.periodic_task.enabled = self.is_active
            self.periodic_task.save()
        self.save()
        return self.is_active



class MessageTask(models.Model):
    """
    Core model for WhatsApp message scheduling and tracking.
    
    Design Decisions:
    - UUID primary key: Prevents enumeration attacks, supports distributed systems
    - Indexed status field: Optimizes queries for task filtering
    - Atomic status transitions: Ensures data consistency
    - Soft deletes: Maintains audit trail
    - Options JSONField: Supports template, media, interactive messages
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        QUEUED = 'queued', 'Queued'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        RETRYING = 'retrying', 'Retrying'
        CANCELLED = 'cancelled', 'Cancelled'
    
    # Primary identification
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    
    # Message details
    recipient = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Enter a valid phone number'
            )
        ],
        db_index=True  # Optimize recipient lookup queries
    )
    message_body = models.TextField(max_length=4096)
    
    # Advanced message options (template, media, interactive)
    options = models.JSONField(
        default=dict,
        blank=True,
        help_text='Advanced message options: type, template_name, media_id, buttons, etc.'
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True  # Critical for filtering by status
    )
    
    # Timing fields
    scheduled_time = models.DateTimeField(
        db_index=True  # Essential for scheduled task queries
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Retry and error handling
    retries = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    error_message = models.TextField(blank=True, null=True)
    
    # Task metadata
    celery_task_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        db_index=True  # Quick lookup by Celery task ID
    )
    
    # Priority queue support (lower number = higher priority)
    priority = models.IntegerField(default=5, db_index=True)
    
    # Soft delete support
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # User tracking (optional - add if you need user association)
    created_by = models.ForeignKey(getattr(settings, "AUTH_USER_MODEL"), blank=True, null=True, on_delete=models.SET_NULL)
    
    class Meta:
        db_table = 'message_tasks'
        ordering = ['-created_at']
        indexes = [
            # Composite index for scheduled task retrieval
            models.Index(
                fields=['status', 'scheduled_time', 'priority'],
                name='idx_scheduled_tasks'
            ),
            # Index for active task monitoring
            models.Index(
                fields=['status', 'updated_at'],
                name='idx_active_tasks'
            ),
            # Index for recipient history
            models.Index(
                fields=['recipient', '-created_at'],
                name='idx_recipient_history'
            ),
        ]
        verbose_name = 'Message Task'
        verbose_name_plural = 'Message Tasks'
    
    def __str__(self):
        return f"MessageTask {self.id} - {self.recipient} ({self.status})"
    
    def can_retry(self):
        """Check if task is eligible for retry"""
        return (
            self.status == self.Status.FAILED and 
            self.retries < self.max_retries
        )
    
    def mark_processing(self):
        """Atomic transition to processing state"""
        self.status = self.Status.PROCESSING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])
    
    def mark_completed(self):
        """Atomic transition to completed state"""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])
    
    def mark_failed(self, error_message):
        """Atomic transition to failed state with error tracking"""
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.retries += 1
        self.save(update_fields=['status', 'error_message', 'retries', 'updated_at'])
    
    def soft_delete(self):
        """Soft delete for audit trail maintenance"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.status in [self.Status.PENDING, self.Status.QUEUED]:
            return self.scheduled_time < timezone.now()
        return False
    
    @property
    def execution_duration(self):
        """Calculate execution duration in milliseconds"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None


class TaskExecutionLog(models.Model):
    """
    Detailed execution history for debugging and analytics.
    
    Design Decision: Separate table to prevent MessageTask bloat
    and enable efficient time-series queries.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        MessageTask, 
        on_delete=models.CASCADE, 
        related_name='execution_logs'
    )
    
    status = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    execution_time_ms = models.IntegerField(null=True)  # Performance tracking
    error_details = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'task_execution_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['task', '-timestamp'], name='idx_task_logs'),
            models.Index(fields=['status', '-timestamp'], name='idx_status_logs'),
        ]
        verbose_name = 'Task Execution Log'
        verbose_name_plural = 'Task Execution Logs'
    
    def __str__(self):
        return f"Log {self.id} - Task {self.task.id} - {self.status}"


class MessageTaskQuerySet(models.QuerySet):
    """Custom QuerySet for MessageTask with common filters"""
    
    def active(self):
        """Get non-deleted tasks"""
        return self.filter(is_deleted=False)
    
    def pending(self):
        """Get pending tasks"""
        return self.active().filter(status=MessageTask.Status.PENDING)
    
    def scheduled_for_now(self):
        """Get tasks scheduled for now or earlier"""
        return self.pending().filter(scheduled_time__lte=timezone.now())
    
    def failed(self):
        """Get failed tasks"""
        return self.active().filter(status=MessageTask.Status.FAILED)
    
    def retryable(self):
        """Get tasks that can be retried"""
        return self.failed().filter(retries__lt=models.F('max_retries'))
    
    def overdue(self):
        """Get overdue pending tasks"""
        return self.filter(
            status__in=[MessageTask.Status.PENDING, MessageTask.Status.QUEUED],
            scheduled_time__lt=timezone.now(),
            is_deleted=False
        )
    
    def by_priority(self):
        """Order by priority (ascending) and scheduled time"""
        return self.order_by('priority', 'scheduled_time')


# Attach custom manager safely
MessageTask.add_to_class('objects', MessageTaskQuerySet.as_manager())
