# serializers.py
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import phonenumbers
from .models import MessageTask, TaskExecutionLog
from utils.whatsapp.helpers import generate_whatsapp_options


# =========================================================
# 🌐 Common Validators and Mixins
# =========================================================

class PhoneNumberValidatorMixin:
    """Reusable mixin for validating international phone numbers."""
    default_region = "RW"

    def validate_phone(self, number: str) -> str:
        try:
            phone_obj = phonenumbers.parse(number, self.default_region)
            if not phonenumbers.is_valid_number(phone_obj):
                raise ValueError
            return phonenumbers.format_number(phone_obj, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            raise ValidationError("Invalid phone number format. Use international format (+250...).")


class ScheduleValidationMixin:
    """Reusable mixin for schedule/time validations."""
    def validate_future_time(self, value):
        if value < timezone.now():
            raise ValidationError("Scheduled time must be in the future.")
        return value


# =========================================================
# 🧾 Task Execution Log Serializer
# =========================================================

class TaskExecutionLogSerializer(serializers.ModelSerializer):
    """Serializer for execution logs with metrics."""
    class Meta:
        model = TaskExecutionLog
        fields = [
            "id", "status", "timestamp", "execution_time_ms",
            "error_details", "metadata"
        ]
        read_only_fields = ["id", "timestamp"]


# =========================================================
# 📋 Message Task List / Detail Serializers
# =========================================================

class MessageTaskListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing message tasks."""
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.SerializerMethodField()
    time_until_scheduled = serializers.SerializerMethodField()

    class Meta:
        model = MessageTask
        fields = [
            "id", "recipient", "status", "status_display",
            "scheduled_time", "created_at", "updated_at",
            "priority", "retries", "max_retries",
            "is_overdue", "time_until_scheduled"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_is_overdue(self, obj):
        return obj.status in [MessageTask.Status.PENDING, MessageTask.Status.QUEUED] \
            and obj.scheduled_time < timezone.now()

    def get_time_until_scheduled(self, obj):
        return int((obj.scheduled_time - timezone.now()).total_seconds())


class MessageTaskDetailSerializer(serializers.ModelSerializer):
    """Detailed task serializer with logs and computed state."""
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    execution_logs = TaskExecutionLogSerializer(many=True, read_only=True)
    can_retry = serializers.BooleanField(read_only=True)

    class Meta:
        model = MessageTask
        fields = [
            "id", "recipient", "message_body", "status", "status_display",
            "scheduled_time", "created_at", "updated_at",
            "started_at", "completed_at", "retries", "max_retries",
            "error_message", "celery_task_id", "priority",
            "is_deleted", "deleted_at", "can_retry", "execution_logs"
        ]
        read_only_fields = [
            "id", "created_at", "updated_at", "started_at", "completed_at",
            "celery_task_id", "is_deleted", "deleted_at", "retries"
        ]


# =========================================================
# ✉️ Message Task Create / Update
# =========================================================


class MessageTaskCreateSerializer(
    PhoneNumberValidatorMixin, ScheduleValidationMixin, serializers.ModelSerializer
):
    """Serializer for creating message tasks with validated WhatsApp options."""

    options = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = MessageTask
        fields = [
            "recipient",
            "message_body",
            "scheduled_time",
            "priority",
            "max_retries",
            "options",
        ]

    # --- Field Validations ---

    def validate_recipient(self, value):
        return self.validate_phone(value)

    def validate_scheduled_time(self, value):
        return self.validate_future_time(value)

    def validate_priority(self, value):
        if not 0 <= value <= 9:
            raise serializers.ValidationError("Priority must be between 0 (highest) and 9 (lowest).")
        return value

    def validate_max_retries(self, value):
        if not 0 <= value <= 10:
            raise serializers.ValidationError("max_retries must be between 0 and 10.")
        return value

    def validate_message_body(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message body cannot be empty.")
        if len(value) > 4096:
            raise serializers.ValidationError("Message body exceeds 4096 characters.")
        return value

    def validate_options(self, value):
        """Validate and normalize WhatsApp message options."""
        message_body = self.initial_data.get("message_body", "")
        msg_type = (value or {}).get("type")

        # Default fallback: text message
        if not value or not msg_type:
            return generate_whatsapp_options(
                msg_type="text",
                message_body=message_body
            )

        try:
            match msg_type:
                case "text":
                    return generate_whatsapp_options(
                        msg_type="text",
                        message_body=message_body
                    )

                case "media":
                    return generate_whatsapp_options(
                        msg_type="media",
                        message_body=message_body,
                        media_url="https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                        media_type="document",
                        filename="information_management_system.pdf"
                    )

                case "template":
                    return generate_whatsapp_options(
                        msg_type="template",
                        preview_url=True,
                        message_body=message_body,
                        template_name="twara_user_progress_update",
                        body_params=["50", "fewer data, from, frontend, for demo", "whole templates is working"],
                        header_params=["Test from Inventory MS"],
                        language="rw_RW"
                    )

                case _:
                    raise serializers.ValidationError(f"Unsupported message type: {msg_type}")

        except Exception as e:
            raise serializers.ValidationError(str(e))

    # --- Object Creation ---
    def create(self, validated_data):
        """Create MessageTask atomically with validated WhatsApp options."""
        options = validated_data.pop("options", {})
        with transaction.atomic():
            task = MessageTask.objects.create(**validated_data)
            if hasattr(task, "options"):
                task.options = options or {}
                task.save(update_fields=["options"])
        return task



class MessageTaskUpdateSerializer(serializers.ModelSerializer):
    """Restricted updates for pending or failed tasks only."""
    class Meta:
        model = MessageTask
        fields = ["scheduled_time", "priority", "message_body", "max_retries"]

    def validate(self, attrs):
        instance = self.instance
        if instance.status not in [MessageTask.Status.PENDING, MessageTask.Status.FAILED]:
            raise ValidationError("Only pending or failed tasks can be updated.")
        return attrs

    def validate_scheduled_time(self, value):
        if value < timezone.now():
            raise ValidationError("Scheduled time must be in the future.")
        return value


# =========================================================
# 📦 Batch Operations
# =========================================================

class BatchMessageTaskCreateSerializer(ScheduleValidationMixin, serializers.Serializer):
    """Serializer for bulk creation of message tasks (optimized for Celery)."""
    recipients = serializers.ListField(
        child=serializers.CharField(max_length=20),
        min_length=1,
        max_length=500,
        help_text="List of international phone numbers."
    )
    message_body = serializers.CharField(max_length=4096)
    scheduled_time = serializers.DateTimeField()
    priority = serializers.IntegerField(default=5, min_value=0, max_value=9)
    max_retries = serializers.IntegerField(default=3, min_value=0, max_value=10)
    options = serializers.JSONField(required=False, allow_null=True)

    def validate_recipients(self, recipients):
        mixin = PhoneNumberValidatorMixin()
        normalized = []
        for num in recipients:
            normalized.append(mixin.validate_phone(num))
        return list(set(normalized))  # Remove duplicates

    def validate_scheduled_time(self, value):
        return self.validate_future_time(value)

    def create(self, validated_data):
        recipients = validated_data.pop("recipients")
        options = validated_data.pop("options", None)
        tasks = []
        with transaction.atomic():
            for phone in recipients:
                task = MessageTask.objects.create(recipient=phone, **validated_data)
                if options:
                    task.options = options
                    task.save(update_fields=["options"])
                tasks.append(task)
        return tasks


# =========================================================
# ⚙️ Status Management & Dashboard
# =========================================================

class TaskStatusUpdateSerializer(serializers.Serializer):
    """Enforces allowed status transitions (admin/supervisor use)."""
    status = serializers.ChoiceField(choices=MessageTask.Status.choices)
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        instance = self.instance
        new_status = attrs["status"]
        allowed = {
            MessageTask.Status.PENDING: [MessageTask.Status.CANCELLED],
            MessageTask.Status.QUEUED: [MessageTask.Status.CANCELLED],
            MessageTask.Status.FAILED: [MessageTask.Status.PENDING, MessageTask.Status.CANCELLED],
            MessageTask.Status.PROCESSING: [MessageTask.Status.FAILED],
        }.get(instance.status, [])

        if new_status not in allowed:
            raise ValidationError(f"Cannot transition from {instance.status} → {new_status}.")
        return attrs


class TaskStatisticsSerializer(serializers.Serializer):
    """Provides structured task statistics for dashboards."""
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    queued = serializers.IntegerField()
    processing = serializers.IntegerField()
    completed = serializers.IntegerField()
    failed = serializers.IntegerField()
    retrying = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    avg_execution_time_ms = serializers.FloatField(allow_null=True)
    success_rate = serializers.FloatField()
    total_retries = serializers.IntegerField()



