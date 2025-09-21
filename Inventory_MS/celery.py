import os
from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Inventory_MS.settings')

app = Celery('Inventory_MS')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

import tasks
