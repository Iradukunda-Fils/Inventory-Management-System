from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json
from sms_tasks.tasks import send_sms
from django.conf import settings

from .forms import SendSMSForm


class SendSMSView(View):
    template_name = "admin/send_sms.html"

    def get(self, request):
        form = SendSMSForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = SendSMSForm(request.POST)
        if form.is_valid():
            phone_number = str(form.cleaned_data["phone_number"])
            message_content = form.cleaned_data["message"]
            sender = form.cleaned_data.get("sender") or getattr(settings, "SMS_SENDER", "TWARA")
            schedule_type = form.cleaned_data["schedule_type"]

            if schedule_type == "now":
                send_sms.delay(phone_number, message_content, sender)
                messages.success(request, f"SMS to {phone_number} queued successfully.")

            elif schedule_type == "interval":
                every = form.cleaned_data.get("every", 1)
                period = form.cleaned_data.get("period", "minutes")

                schedule, _ = IntervalSchedule.objects.get_or_create(
                    every=every,
                    period=period,
                )
                PeriodicTask.objects.create(
                    interval=schedule,
                    name=f"Send SMS to {phone_number} - {message_content[:20]}",
                    task="sms_tasks.tasks.send_sms",
                    args=json.dumps([phone_number, message_content, sender]),
                )
                messages.success(request, f"Periodic SMS every {every} {period} created.")

            elif schedule_type == "crontab":
                schedule, _ = CrontabSchedule.objects.get_or_create(
                    minute=form.cleaned_data.get("minute", "*"),
                    hour=form.cleaned_data.get("hour", "*"),
                    day_of_week=form.cleaned_data.get("day_of_week", "*"),
                    day_of_month=form.cleaned_data.get("day_of_month", "*"),
                    month_of_year=form.cleaned_data.get("month_of_year", "*"),
                )
                PeriodicTask.objects.create(
                    crontab=schedule,
                    name=f"Cron SMS to {phone_number} - {message_content[:20]}",
                    task="sms_tasks.tasks.send_sms",
                    args=json.dumps([phone_number, message_content, sender]),
                )
                messages.success(request, "Cron-based SMS schedule created successfully.")

            return redirect("send_sms")

        # If form is invalid
        return render(request, self.template_name, {"form": form})
