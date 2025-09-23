# forms.py
from django import forms
from django.core.exceptions import ValidationError
from django_celery_beat.models import IntervalSchedule, CrontabSchedule
from .models import SMSTask
import re

class SMSTaskForm(forms.ModelForm):
    SCHEDULE_TYPE_CHOICES = [
        ('immediate', 'Send Immediately'),
        ('interval', 'Repeat Every'),
        ('crontab', 'Custom Schedule (Cron)'),
    ]
    
    # Schedule fields
    schedule_type = forms.ChoiceField(
        choices=SCHEDULE_TYPE_CHOICES, 
        initial='immediate',
        widget=forms.RadioSelect(attrs={'class': 'schedule-type-radio'})
    )
    
    # Interval fields
    interval_period = forms.ChoiceField(
        choices=IntervalSchedule.PERIOD_CHOICES,
        initial=IntervalSchedule.MINUTES,
        required=False
    )
    interval_every = forms.IntegerField(
        min_value=1, 
        initial=10, 
        required=False,
        help_text="Run every X period(s)"
    )
    
    # Crontab fields
    cron_minute = forms.CharField(max_length=60, initial='0', required=False, help_text="0-59, *, */5")
    cron_hour = forms.CharField(max_length=60, initial='*', required=False, help_text="0-23, *, */2")
    cron_day_of_week = forms.CharField(max_length=60, initial='*', required=False, help_text="0-6 (0=Sun), *, mon")
    cron_day_of_month = forms.CharField(max_length=60, initial='*', required=False, help_text="1-31, *, */2")
    cron_month_of_year = forms.CharField(max_length=60, initial='*', required=False, help_text="1-12, *, jan")

    class Meta:
        model = SMSTask
        fields = ['name', 'phone_numbers', 'message', 'sender', 'send_type', 'retry_count', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter task name'
            }),
            'phone_numbers': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': '+1234567890, +0987654321, +1122334455'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Enter your SMS message here...',
                'maxlength': 1000
            }),
            'sender': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sender name or number'
            }),
            'send_type': forms.Select(attrs={'class': 'form-control send-type-select'}),
            'retry_count': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '0', 
                'max': '10'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        help_texts = {
            'phone_numbers': 'For single SMS: one number. For bulk SMS: comma-separated numbers.',
            'message': 'SMS message content (max 1000 characters)',
            'retry_count': 'Number of retry attempts on failure (0-10)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['created_by'] = forms.ModelChoiceField(
            queryset=None, widget=forms.HiddenInput(), required=False
        )

    def clean_phone_numbers(self):
        phone_numbers = self.cleaned_data.get('phone_numbers', '')
        if not phone_numbers:
            raise ValidationError("At least one phone number is required.")
        
        phone_pattern = re.compile(r'^\+?1?\d{9,15}$')
        phones = [phone.strip() for phone in phone_numbers.split(',')]
        
        invalid_phones = [phone for phone in phones if not phone_pattern.match(phone)]
        if invalid_phones:
            raise ValidationError(f"Invalid phone numbers: {', '.join(invalid_phones)}")
        
        return phone_numbers

    def clean_message(self):
        message = self.cleaned_data.get('message', '')
        if len(message.strip()) < 1:
            raise ValidationError("Message cannot be empty.")
        return message.strip()

    def clean_cron_minute(self):
        return self._validate_cron_field(self.cleaned_data.get('cron_minute', '0'), 'minute', 0, 59)

    def clean_cron_hour(self):
        return self._validate_cron_field(self.cleaned_data.get('cron_hour', '*'), 'hour', 0, 23)

    def _validate_cron_field(self, value, field_name, min_val, max_val):
        """Validate cron field format"""
        if not value or value == '*':
            return value
        
        # Basic validation for numbers and ranges
        if not re.match(r'^[\d,\-\*/]+$', value) and field_name != 'day_of_week':
            raise ValidationError(f"Invalid {field_name} format")
        
        return value

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            
            # Handle scheduling
            schedule_type = self.cleaned_data.get('schedule_type')
            if schedule_type != 'immediate':
                self._create_periodic_task(instance, schedule_type)
        
        return instance

    def _create_periodic_task(self, instance, schedule_type):
        """Create periodic task based on schedule type"""
        from django_celery_beat.models import PeriodicTask
        from sms_tasks.tasks import send_sms
        
        # Delete existing periodic task
        if instance.periodic_task:
            instance.periodic_task.delete()
        
        task_name = f"sms_task_{instance.id}_{instance.name}"
        
        if schedule_type == 'interval':
            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=self.cleaned_data['interval_every'],
                period=self.cleaned_data['interval_period']
            )
            periodic_task = PeriodicTask.objects.create(
                name=task_name,
                task='sms_tasks.tasks.send_sms',
                interval=schedule,
                args=f'[{instance.id}]',
                enabled=instance.is_active
            )
        elif schedule_type == 'crontab':
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=self.cleaned_data['cron_minute'],
                hour=self.cleaned_data['cron_hour'],
                day_of_week=self.cleaned_data['cron_day_of_week'],
                day_of_month=self.cleaned_data['cron_day_of_month'],
                month_of_year=self.cleaned_data['cron_month_of_year']
            )
            periodic_task = PeriodicTask.objects.create(
                name=task_name,
                task='sms_tasks.tasks.send_sms',
                crontab=schedule,
                args=f'[{instance.id}]',
                enabled=instance.is_active
            )
        
        instance.periodic_task = periodic_task
        instance.save()


class SMSTaskFilterForm(forms.Form):
    """Form for filtering and searching SMS tasks"""
    search = forms.CharField(
        max_length=200, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, phone, or message...'
        })
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + SMSTask.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    send_type = forms.ChoiceField(
        choices=[('', 'All Types')] + SMSTask.SEND_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )