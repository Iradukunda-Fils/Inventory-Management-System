import httpx
import logging
from celery import shared_task
from django.conf import settings
from django.db.models import F
from django.utils import timezone
from sms_tasks.models import SMSTask
from typing import Union

logger = logging.getLogger(__name__)


def normalize_number(number: str, default_country_code="+25") -> str:
    """Normalize phone numbers with country code"""
    number = str(number).strip().replace(" ", "")
    
    if not number.startswith("+"):
        number = f"{default_country_code}{number}"
    return number


@shared_task(bind=True, autoretry_for=(httpx.RequestError,), retry_backoff=True)
def send_sms(self, id_or_number: Union[str, int], message: str = None, sender: str = None):
    """
    Send SMS via API.
    - Accepts a single phone number (string) or SMSTask ID (int).
    - Tracks execution stats in SMSTask model.
    - Retries on network errors with exponential backoff.
    """
    sender = sender or getattr(settings, "SMS_SENDER", "TWARA")
    default_country_code = getattr(settings, "SMS_DEFAULT_COUNTRY_CODE", "+25")

    sms_api = getattr(settings, "SMS_API", None)
    sms_key = getattr(settings, "SMS_API_KEY", None)
    if not sms_api or not sms_key:
        logger.error("❌ SMS configuration missing!")
        raise ValueError("SMS API configuration missing")

    task = None
    if isinstance(id_or_number, int):
        task = SMSTask.objects.filter(pk=id_or_number).first()
        if not task:
            logger.error(f"❌ SMSTask {id_or_number} not found")
            return {"success": 0, "failed": 0, "results": [], "error": "Task not found"}

        numbers = task.get_phone_list()
        message = message or task.message
        sender = sender or task.sender

        SMSTask.objects.filter(pk=task.pk).update(
            status="running",
            execution_count=F("execution_count") + 1,
            last_execution=timezone.now()
        )
        task.refresh_from_db()
    else:
        numbers = [str(id_or_number)]

    # Validation
    if not message:
        logger.warning("⚠️ Empty message, aborting.")
        return {"success": 0, "failed": len(numbers), "results": [], "error": "Empty message"}
    if not numbers:
        logger.warning("⚠️ No recipients found.")
        return {"success": 0, "failed": 0, "results": [], "error": "No recipients"}

    recipients = [normalize_number(num, default_country_code) for num in numbers]

    headers = {"Authorization": f"Bearer {sms_key}", "Content-Type": "application/json"}

    results, success, failed = [], 0, 0
    retry_limit = task.retry_count if task else 3

    try:
        with httpx.Client(timeout=10.0) as client:
            for phone in recipients:
                payload = {"to": phone, "text": message, "sender": sender, **(task.options if task else {})}
                try:
                    response = client.post(sms_api, json=payload, headers=headers)
                    response.raise_for_status()
                    results.append({"phone": phone, "response": response.json()})
                    logger.info(f"✅ SMS sent to {phone}")
                    success += 1
                except httpx.HTTPStatusError as e:
                    logger.error(f"❌ API error [{e.response.status_code}] to {phone}: {e.response.text}")
                    results.append({"phone": phone, "error": str(e)})
                    failed += 1
                except httpx.RequestError as e:
                    logger.error(f"❌ Network error to {phone}: {e}")
                    raise self.retry(exc=e, countdown=2 ** self.request.retries, max_retries=retry_limit)

        if task:
            new_status = "success" if failed == 0 else "failed"
            SMSTask.objects.filter(pk=task.pk).update(
                status=new_status,
                success_count=F("success_count") + success,
                failed_count=F("failed_count") + failed,
                updated_at=timezone.now()
            )

        return {"success": success, "failed": failed, "results": results}

    except Exception as e:
        logger.exception("Unexpected error during SMS sending")
        if task:
            SMSTask.objects.filter(pk=task.pk).update(
                status="failed",
                failed_count=F("failed_count") + len(recipients),
                updated_at=timezone.now()
            )
        raise self.retry(exc=e, countdown=2 ** self.request.retries, max_retries=retry_limit)
