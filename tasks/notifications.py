from celery import shared_task
from time import sleep


@shared_task
def send_notification(message):
    sleep(1000)  # import time
    print(f"Notification: {message}")