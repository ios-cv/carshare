from django.db import models

from hardware.models import Vehicle
from users.models import User


class Booking(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="bookings",
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT, related_name="bookings",
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

