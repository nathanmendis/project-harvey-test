import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')

# Initialize Celery app
app = Celery('project_harvey')

# Load task modules from all registered Django apps.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat Schedule for HRMS Sync - Polling mock APIs every 3 hours
# Setting up polling using the adapter pattern for all organizations in one batch job
app.conf.beat_schedule = {
    'sync-hrms-data-every-3-hours': {
        'task': 'integrations.hrms.sync.tasks.sync_all_data',
        'schedule': crontab(minute=0, hour='*/3'),  # Exactly every 3 hours
    },
}

app.conf.timezone = 'Asia/Kolkata'
