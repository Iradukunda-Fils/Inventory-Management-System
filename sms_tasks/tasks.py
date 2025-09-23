import httpx
import logging
from celery import shared_task
from django.conf import settings
from sms_tasks.models import SMSTask
from typing import Union

logger = logging.getLogger(__name__)


def normalize_number(number: str) -> str:
    number = str(number).strip().replace(" ", "")
    if number.startswith("0"):
        return f"+25{number}"
    if not number.startswith("+"):
        return f"+25{number}"
    return number




@shared_task(bind=True, max_retries=3)
def send_sms(self, obj_or_number: Union[str, SMSTask], message: str = None, sender: str = None): 
    """
    Send SMS via API.
    - Accepts a single number or SMSTask instance.
    - Retries on failure with exponential backoff.
    """
    # Extract task metadata
    if isinstance(obj_or_number, SMSTask):
        task = obj_or_number
        numbers = [n.strip() for n in task.get_phone_list()]
        message = message or task.message
        sender = sender or task.sender
        task.status = "running"
        task.execution_count += 1
        task.save(update_fields=["status", "execution_count", "updated_at"])
        
    else:
        numbers = [str(obj_or_number)]
        task = None


    sender = sender or getattr(settings, "SMS_SENDER", "TWARA")

    # Check configuration
    if not getattr(settings, "SMS_API_KEY", None) or not getattr(settings, "SMS_API", None):
        logger.error("❌ SMS configuration missing.")
        raise ValueError("SMS configuration missing!")

    # Normalize numbers
    recipients = [normalize_number(num) for num in numbers]

    headers = {
        "Authorization": f"Bearer {settings.SMS_API_KEY}",
        "Content-Type": "application/json",
    }

    results, success, failed = [], 0, 0

    try:
        with httpx.Client(timeout=10.0) as client:
            for phone in recipients:
                payload = {"to": phone, "text": message, "sender": sender}
                try:
                    response = client.post(settings.SMS_API, json=payload, headers=headers)
                    response.raise_for_status()
                    results.append(response.json())
                    logger.info(f"✅ SMS sent to {phone}")
                    success += 1
                except httpx.HTTPStatusError as e:
                    logger.error(f"❌ SMS failed [{e.response.status_code}] to {phone}: {e.response.text}")
                    failed += 1
                except httpx.RequestError as e:
                    logger.error(f"❌ SMS network error to {phone}: {e}")
                    raise self.retry(exc=e, countdown=2 ** self.request.retries)

        # Update DB if task object exists
        if task:
            task.success_count += success
            task.failed_count += failed
            task.status = "success" if failed == 0 else "failed"
            task.save(update_fields=["status", "success_count", "failed_count", "updated_at"])

        return {"success": success, "failed": failed, "results": results}

    except Exception as e:
        logger.exception("Unexpected error in SMS sending")
        if task:
            task.status = "failed"
            task.failed_count += len(recipients)
            task.save(update_fields=["status", "failed_count", "updated_at"])
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

