# models.py
from django.db import models
from django_celery_beat.models import PeriodicTask
from django.core.validators import RegexValidator
from django.conf import settings

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
    phone_validator = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Invalid phone number format")
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