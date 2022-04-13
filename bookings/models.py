from abc import ABC

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import (
    DateTimeRangeField,
    RangeBoundary,
    RangeOperators,
)
from django.db import models
from django.db.models import Func, Q, Subquery
from django.utils import timezone
from psycopg2.extras import DateTimeTZRange

from hardware.models import Vehicle
from users.models import User


class TsTzRange(Func, ABC):
    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class Booking(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    cancelled = models.BooleanField(default=False, null=False)

    # Actual reservation times as visible to the user.
    reservation_time = DateTimeRangeField()

    # Full extents of time that this booking will block others from being created.
    block_time = DateTimeRangeField()

    class Meta:
        # Ensure no overlapping uncancelled bookings on any vehicle.
        constraints = [
            ExclusionConstraint(
                name="prevent_overlaps",
                expressions=(
                    ("block_time", RangeOperators.OVERLAPS),
                    ("vehicle_id", RangeOperators.EQUAL),
                ),
                condition=Q(cancelled=False),
            ),
        ]

    @staticmethod
    def create_booking(user, vehicle, start, end):
        reservation_time = DateTimeTZRange(lower=start, upper=end)
        block_time = DateTimeTZRange(
            lower=start, upper=end + timezone.timedelta(minutes=15)
        )
        b = Booking(
            user=user,
            vehicle=vehicle,
            reservation_time=reservation_time,
            block_time=block_time,
        )

        b.save()

    def reservation_ended(self):
        return timezone.now() > self.reservation_time.upper

    def reservation_in_progress(self):
        now = timezone.now()
        return self.reservation_time.lower <= now <= self.reservation_time.upper


def get_available_vehicles(start, end, van=True, car=True, combi=True):
    return Vehicle.objects.exclude(
        id__in=Subquery(
            Booking.objects.values("vehicle_id")
            .filter(
                cancelled=False,
                block_time__overlap=TsTzRange(start, end, RangeBoundary()),
            )
            .order_by("vehicle_id")
            .distinct("vehicle_id")
        )
    )
