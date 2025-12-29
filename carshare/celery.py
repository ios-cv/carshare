import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "carshare.settings")

app = Celery("carshare")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


app.conf.beat_schedule = {
    "run-billing-periodically": {
        "task": "run_billing",
        "schedule": 300.0,
    },
    "run-monthly-credit-account-billing-cycle": {
        "task": "monthly_billing",
        "schedule": crontab(hour=2, minute=0, day_of_month="1"),
    },
    "manage-booking-state-updates-periodically": {
        "task": "manage_booking_states",
        "schedule": 60.0,
    },
}
