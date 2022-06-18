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
    STATE_PENDING = "pending"
    STATE_CANCELLED = "cancelled"
    STATE_ACTIVE = "active"
    STATE_LATE = "late"
    STATE_ENDED = "ended"
    STATE_BILLED = "billed"

    STATE_CHOICES = [
        (STATE_PENDING, "pending"),
        (STATE_CANCELLED, "cancelled"),
        (STATE_ACTIVE, "active"),
        (STATE_LATE, "late"),
        (STATE_ENDED, "ended"),
        (STATE_BILLED, "billed"),
    ]

    ALLOW_USER_UNLOCK_STATES = [
        STATE_PENDING,
        STATE_ACTIVE,
    ]

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

    state = models.CharField(
        max_length=16,
        choices=STATE_CHOICES,
    )

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

    @property
    def cancelled(self):
        return self.state == self.STATE_CANCELLED


def get_available_vehicles(start, end, van=True, car=True, combi=True):
    return Vehicle.objects.exclude(
        id__in=Subquery(
            Booking.objects.values("vehicle_id")
            .filter(
                ~Q(state=Booking.STATE_CANCELLED),
                block_time__overlap=TsTzRange(start, end, RangeBoundary()),
            )
            .order_by("vehicle_id")
            .distinct("vehicle_id")
        )
    )


def get_current_booking_for_vehicle(vehicle):
    return Booking.objects.filter(
        ~Q(state=Booking.STATE_CANCELLED),
        reservation_time__contains=timezone.now(),
        vehicle=vehicle,
    ).first()
