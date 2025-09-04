import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kejebe.settings")

app = Celery("kejebe")

# Config from Django settings with CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in installed apps
app.autodiscover_tasks()

