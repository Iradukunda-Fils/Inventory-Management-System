from celery import shared_task

@shared_task
def send_notification(message):
    print(f"Notification: {message}")