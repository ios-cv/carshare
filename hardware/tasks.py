from celery import shared_task
from django.utils import timezone
from hardware.models import Telemetry
from carshare.settings import TELEMETRY_AGE_DAYS


@shared_task(name="remove_old_telemetry")
def remove_old_telemetry():
    period = timezone.timedelta(days=TELEMETRY_AGE_DAYS)
    boundary = timezone.now() - period
    old_telemetry = Telemetry.objects.filter(created_at__lt=boundary)
    old_telemetry.delete()
