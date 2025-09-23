from django.contrib import admin
from .models import SMSTask


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
