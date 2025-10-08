from typing import Any, Dict, Optional
from celery import shared_task, Task
from celery.exceptions import MaxRetriesExceededError
from django.conf import settings
from django.db.models import F
from django.utils import timezone
from sms_tasks.models import SMSTask
from typing import Union
from django.db import transaction
import traceback
import httpx
import logging
import time
from .models import MessageTask, TaskExecutionLog

from .services import WhatsAppService  # adapter (see whatsapp_service.py)
# Optional: from .realtime import broadcast_task_update  # your Channels integration

logger = logging.getLogger(__name__)


# Configuration defaults (override in settings.py if needed)
MESSAGE_TASK_BATCH_SIZE = getattr(settings, "MESSAGE_TASK_BATCH_SIZE", 200)
MESSAGE_TASK_RATE_LIMIT = getattr(settings, "MESSAGE_TASK_RATE_LIMIT", None)  # e.g. "100/m"


def _normalize_number(number: str, default_country_code="+25") -> str:
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

    recipients = [_normalize_number(num, default_country_code) for num in numbers]

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


# ----------------------------
# Helpers
# ----------------------------
def _broadcast_status_update(task: MessageTask) -> None:
    """
    Hook for real-time updates. Replace with your Channels/SSE implementation.
    Keep it non-blocking (fire & forget).
    """
    try:
        # Example:
        # from channels.layers import get_channel_layer
        # layer = get_channel_layer()
        # async_to_sync(layer.group_send)(f"task_{task.id}", {...})
        pass
    except Exception:
        logger.exception("Failed to broadcast task update")

def _log_execution(task: MessageTask,
                   status: str,
                   execution_time_ms: Optional[int] = None,
                   metadata: Optional[Dict[str, Any]] = None,
                   error_details: Optional[Dict[str, Any]] = None) -> TaskExecutionLog:
    """Create an execution log entry. Centralizes logging schema."""
    return TaskExecutionLog.objects.create(
        task=task,
        status=status,
        execution_time_ms=execution_time_ms,
        metadata=metadata or {},
        error_details=error_details or {}
    )

# ----------------------------
# Core send_whatsapp task (by MessageTask.id)
# ----------------------------
@shared_task(
    bind=True,
    max_retries=5,                 # global Celery max retry count
    default_retry_delay=60,        # base delay (seconds)
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(),              # we call self.retry() explicitly to control metadata
)
def send_whatsapp(self: Task, object_id: str) -> Dict[str, Any]:
    """
    Process a MessageTask record and deliver via WhatsApp.

    - Idempotent: safe to call multiple times.
    - Transactional: state transitions use select_for_update + atomic.
    - Observable: writes TaskExecutionLog entries and calls broadcast hook.
    - Resilient: uses retries with exponential backoff via self.retry.
    """
    start = time.time()
    wa = WhatsAppService()
    task_obj: Optional[MessageTask] = None

    try:
        # 1) Lock row and claim it
        with transaction.atomic():
            task_obj = MessageTask.objects.select_for_update(nowait=False).get(
                id=object_id, is_deleted=False
            )

            # If already completed, short-circuit (idempotency)
            if task_obj.status == MessageTask.Status.COMPLETED:
                logger.info("send_whatsapp: task %s already completed", object_id)
                return {"status": "already_completed", "task_id": str(object_id)}

            # Claim this worker
            task_obj.celery_task_id = self.request.id
            task_obj.mark_processing()

        _broadcast_status_update(task_obj)

        # 2) Build payload: allow advanced configurations via options stored on MessageTask
        #    options can contain keys like: {"type": "template", "template_name": "...", "media_id": "..."}
        payload = wa.build_payload_from_task(task_obj)

        logger.debug("send_whatsapp: payload for task %s: %s", object_id, payload)

        # 3) Send message (adapter returns dict with success boolean, message_id, full response)
        response = wa.send_raw(payload)

        elapsed_ms = int((time.time() - start) * 1000)

        # 4) On success -> mark completed and log
        if response.get("success", False):
            with transaction.atomic():
                task_obj.mark_completed()
                _log_execution(
                    task_obj,
                    status=MessageTask.Status.COMPLETED,
                    execution_time_ms=elapsed_ms,
                    metadata={
                        "whatsapp_message_id": response.get("message_id"),
                        "celery_task_id": self.request.id,
                        "retries": self.request.retries,
                        "raw_response_summary": wa.summarize_response(response)
                    }
                )
            _broadcast_status_update(task_obj)
            print(response)
            logger.info("send_whatsapp: task %s completed in %dms", object_id, elapsed_ms)
            return {
                "status": "success",
                "task_id": str(object_id),
                "message_id": response.get("message_id"),
                "execution_time_ms": elapsed_ms
            }

        # 5) If response indicates temporary failure, trigger retry logic
        #    Determine whether to retry based on response and task limits
        raise RuntimeError(f"WhatsApp send failed: {response.get('error') or response}")

    except MessageTask.DoesNotExist:
        logger.warning("send_whatsapp: message task %s does not exist", object_id)
        return {"status": "error", "error": "task_not_found", "task_id": str(object_id)}

    except Exception as exc:
        # Best-effort update of DB status (retrying or final failure)
        elapsed_ms = int((time.time() - start) * 1000)
        tb = traceback.format_exc()
        logger.exception("send_whatsapp: exception for task %s: %s", object_id, exc)

        if task_obj is None:
            # Could not load task to update; return error (no retries)
            return {"status": "error", "error": str(exc), "traceback": tb}

        try:
            with transaction.atomic():
                # Refresh the row
                task = MessageTask.objects.select_for_update().get(id=task_obj.id, is_deleted=False)

                will_retry = (task.retries < task.max_retries) and (self.request.retries < self.max_retries)
                # Update retry state or final failure
                if will_retry:
                    task.status = MessageTask.Status.RETRYING
                    task.error_message = str(exc)
                    task.retries += 1
                    task.save(update_fields=['status', 'error_message', 'retries', 'updated_at'])

                    _log_execution(
                        task,
                        status=MessageTask.Status.RETRYING,
                        execution_time_ms=elapsed_ms,
                        error_details={
                            "error": str(exc),
                            "type": type(exc).__name__,
                            "traceback": tb,
                            "retry_count": task.retries
                        }
                    )

                    _broadcast_status_update(task)

                    # re-raise using Celery retry (honors backoff/jitter)
                    raise self.retry(exc=exc)

                else:
                    # final failure
                    task.mark_failed(str(exc))
                    _log_execution(
                        task,
                        status=MessageTask.Status.FAILED,
                        execution_time_ms=elapsed_ms,
                        error_details={
                            "error": str(exc),
                            "type": type(exc).__name__,
                            "traceback": tb,
                            "final_retry_count": task.retries
                        }
                    )
                    _broadcast_status_update(task)
                    return {"status": "failed", "task_id": str(task.id), "error": str(exc)}
        except MaxRetriesExceededError:
            logger.error("send_whatsapp: max retries exceeded for %s", object_id)
            raise

# ----------------------------
# Generic payload task (for WhatsAppMessage.apply_async_send_task)
# ----------------------------
@shared_task(bind=True, acks_late=True, reject_on_worker_lost=True)
def send_whatsapp_payload(self: Task, payload: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Send a pre-built WhatsApp payload (produced by WhatsAppMessage.build_payload).
    Context is a JSON-serializable dict and can include:
      - message_task_id: to tie this send to an existing MessageTask
      - callback_id: a string identifying callbacks to run after success/failure (resolve on worker)
      - options: extra send-time options
    """
    start = time.time()
    wa = WhatsAppService()
    context = context or {}
    message_task_id = context.get("message_task_id")

    try:
        response = wa.send_raw(payload)
        elapsed_ms = int((time.time() - start) * 1000)

        # If tied to a MessageTask, update it
        if message_task_id:
            try:
                with transaction.atomic():
                    mt = MessageTask.objects.select_for_update().get(id=message_task_id)
                    if response.get("success", False):
                        mt.mark_completed()
                        _log_execution(mt, status=MessageTask.Status.COMPLETED, execution_time_ms=elapsed_ms,
                                       metadata={"payload": payload, "response_summary": wa.summarize_response(response)})
                    else:
                        # mark failed and leave retry decision to schedule or manual process
                        mt.mark_failed(str(response.get("error", "unknown")))
                        _log_execution(mt, status=MessageTask.Status.FAILED, execution_time_ms=elapsed_ms,
                                       error_details={"response": response})
                    _broadcast_status_update(mt)
            except MessageTask.DoesNotExist:
                logger.warning("send_whatsapp_payload: message_task %s not found", message_task_id)

        return {"status": "success" if response.get("success", False) else "failed", "raw": response}

    except Exception as exc:
        elapsed_ms = int((time.time() - start) * 1000)
        logger.exception("send_whatsapp_payload: error sending payload: %s", exc)
        if message_task_id:
            try:
                with transaction.atomic():
                    mt = MessageTask.objects.select_for_update().get(id=message_task_id)
                    mt.mark_failed(str(exc))
                    _log_execution(mt, status=MessageTask.Status.FAILED, execution_time_ms=elapsed_ms,
                                   error_details={"error": str(exc)})
                    _broadcast_status_update(mt)
            except MessageTask.DoesNotExist:
                pass
        # re-raise to let Celery handle retries if configured by caller
        raise

# ----------------------------
# Scheduler: pick pending tasks and enqueue them (run by Celery Beat)
# ----------------------------
@shared_task(bind=True)
def schedule_pending_tasks(self: Task) -> Dict[str, int]:
    """
    Periodic job to find scheduled MessageTask instances and enqueue them.
    - Uses select_for_update(skip_locked=True) to allow concurrent schedulers.
    - Batches to MESSAGE_TASK_BATCH_SIZE.
    """
    now = timezone.now()
    batch_size = MESSAGE_TASK_BATCH_SIZE
    queued = 0
    candidates = []

    # Select and mark QUEUED in one transaction to avoid racing.
    with transaction.atomic():
        qs = (MessageTask.objects
              .select_for_update(skip_locked=True)
              .filter(status=MessageTask.Status.PENDING, scheduled_time__lte=now, is_deleted=False)
              .order_by('priority', 'scheduled_time')[:batch_size])
        candidates = list(qs)
        for t in candidates:
            t.status = MessageTask.Status.QUEUED
            t.celery_task_id = None
            t.save(update_fields=['status', 'updated_at'])

    for t in candidates:
        try:
            # Respect priority mapping (celery priorities are 0-9)
            priority = max(0, min(9, t.priority if isinstance(t.priority, int) else 5))
            send_whatsapp.apply_async(args=[str(t.id)], priority=priority)
            queued += 1
        except Exception:
            logger.exception("schedule_pending_tasks: failed to queue %s", t.id)
            # revert the status so it can be retried next run
            try:
                with transaction.atomic():
                    t.status = MessageTask.Status.PENDING
                    t.save(update_fields=['status', 'updated_at'])
            except Exception:
                pass

    logger.info("schedule_pending_tasks: queued %d tasks", queued)
    return {"queued": queued}

# ----------------------------
# Cleanup old logs
# ----------------------------
@shared_task
def cleanup_old_logs(days: int = 90, dry_run: bool = False) -> Dict[str, int]:
    cutoff = timezone.now() - timezone.timedelta(days=days)
    qs = TaskExecutionLog.objects.filter(timestamp__lt=cutoff)
    count = qs.count()
    if dry_run:
        logger.info("cleanup_old_logs: dry_run true; would delete %d logs", count)
        return {"deleted": 0, "would_delete": count}
    deleted, _ = qs.delete()
    logger.info("cleanup_old_logs: deleted %d logs", deleted)
    return {"deleted": deleted}


__all__ = (
    "send_sms",
    "send_whatsapp",
    "send_whatsapp_payload",
    "schedule_pending_tasks",

)
