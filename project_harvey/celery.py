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
    'rag-index-candidates-and-jobs-every-2-hours': {
        'task': 'core.tasks.index_candidates_and_jobs',
        'schedule': crontab(minute=0, hour='*/2'),  # Every 2 hours
    },
    'daily-manager-leave-digest': {
        'task': 'core.tasks.send_daily_manager_digest',
        'schedule': crontab(minute=0, hour=9, day_of_week='1-5'),  # 9:00 AM Mon-Fri
    },
    'weekly-employee-leave-summary': {
        'task': 'core.tasks.send_weekly_employee_summary',
        'schedule': crontab(minute=0, hour=16, day_of_week='5'),  # 4:00 PM Friday
    },
}

app.conf.timezone = 'Asia/Kolkata'
