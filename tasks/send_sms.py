import httpx
import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(httpx.RequestError, httpx.HTTPStatusError),
    retry_backoff=True,
    max_retries=3
)
def send_sms(self, phone_number: str, message: str, sender: None = None):
    """
    Send SMS via external provider API.

    Args:
        phone_number (str): Local phone number (e.g. "0783071229").
        message (str): SMS content.
        sender (str): Sender ID, defaults to 'TWARA'.
    """
    if sender is None:
        sender = settings.SMS_SENDER
    if not settings.SMS_API_KEY or not settings.SMS_API:
        logger.error("SMS configuration missing (API key or endpoint).")
        raise ValueError("SMS configuration missing!")

    # Construct international format (Rwanda example)
    if phone_number.startswith("0"):
        phone_number = "+25" + phone_number
    elif not phone_number.startswith("+"):
        phone_number = "+25" + phone_number  # fallback

    payload = {
        "to": phone_number,
        "text": message,
        "sender": sender,
    }

    headers = {
        "Authorization": f"Bearer {settings.SMS_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(settings.SMS_API, json=payload, headers=headers)

        response.raise_for_status()
        logger.info(f"✅ SMS sent to {phone_number}: {message}")
        return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ SMS failed [{e.response.status_code}]: {e.response.text}")
        raise self.retry(exc=e)

    except httpx.RequestError as e:
        logger.error(f"❌ SMS network error: {e}")
        raise self.retry(exc=e)
