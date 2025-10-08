from django.contrib import admin
from .models import SMSTask, MessageTask, TaskExecutionLog

@admin.register(SMSTask)
class SMSTaskAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "send_type", "status",
        "execution_count", "success_count", "failed_count",
        "created_by", "created_at",
    )
    list_filter = ("status", "send_type", "created_at", "created_by")
    search_fields = ("name", "message", "created_by__username")
    readonly_fields = (
        "execution_count", "success_count", "failed_count",
        "created_at", "phone_list_display", "message_preview",
    )

    fieldsets = (
        ("Task Info", {
            "fields": ("name", "send_type", "status", "is_active", "sender")
        }),
        ("Content", {
            "fields": ("message_preview", "phone_list_display", "message"),
        }),
        ("Schedule", {
            "fields": ("periodic_task",),
            "classes": ("collapse",),
        }),
        ("Execution Stats", {
            "fields": ("execution_count", "success_count", "failed_count"),
        }),
        ("Meta", {
            "fields": ("created_by", "created_at"),
        }),
    )

    ordering = ("-created_at",)

    # Custom read-only display helpers
    def phone_list_display(self, obj):
        """Nicely formatted phone numbers"""
        return ", ".join(obj.get_phone_list())
    phone_list_display.short_description = "Phone Numbers"

    def message_preview(self, obj):
        """Show a short preview of the SMS message"""
        return obj.get_message_preview()
    message_preview.short_description = "Message Preview"




@admin.register(MessageTask)
class MessageTaskAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'recipient', 'status', 'scheduled_time', 
        'priority', 'retries', 'max_retries', 'started_at', 'completed_at'
    )
    list_filter = ('status', 'priority', 'scheduled_time', 'is_deleted')
    search_fields = ('recipient', 'message_body', 'error_message', 'celery_task_id')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'started_at', 'completed_at')
    fieldsets = (
        ('Task Info', {
            'fields': ('created_by', 'recipient', 'message_body', 'options', 'priority', 'scheduled_time')
        }),
        ('Status & Execution', {
            'fields': ('status', 'retries', 'max_retries', 'error_message', 'celery_task_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at', 'deleted_at')
        }),
        ('Soft Delete', {
            'fields': ('is_deleted',)
        }),
    )
    actions = ['soft_delete_tasks', 'retry_failed_tasks']

    def soft_delete_tasks(self, request, queryset):
        count = queryset.update(is_deleted=True, deleted_at=timezone.now())
        self.message_user(request, f"{count} task(s) soft-deleted.")
    soft_delete_tasks.short_description = "Soft delete selected tasks"

    def retry_failed_tasks(self, request, queryset):
        retried = 0
        for task in queryset:
            if task.can_retry():
                task.status = task.Status.RETRYING
                task.save(update_fields=['status', 'updated_at'])
                retried += 1
        self.message_user(request, f"{retried} task(s) marked for retry.")
    retry_failed_tasks.short_description = "Retry selected failed tasks"


@admin.register(TaskExecutionLog)
class TaskExecutionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'status', 'timestamp', 'execution_time_ms')
    list_filter = ('status',)
    search_fields = ('task__recipient', 'task__message_body')
    ordering = ('-timestamp',)
    readonly_fields = ('id', 'task', 'status', 'timestamp', 'execution_time_ms', 'error_details', 'metadata')
