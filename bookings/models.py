import logging

from abc import ABC

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import (
    DateTimeRangeField,
    RangeBoundary,
    RangeOperators,
)
from django.db import models
from django.db.models import Func, Q, Subquery, DateTimeField
from django.utils import timezone
from psycopg2.extras import DateTimeTZRange

from billing.models import BillingAccount
from billing.pricing import calculate_booking_cost
from hardware.models import Vehicle
from users.models import User

log = logging.getLogger(__name__)


class TsTzRange(Func, ABC):
    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


STATE_PENDING = "pending"
STATE_CANCELLED = "cancelled"
STATE_ACTIVE = "active"
STATE_INACTIVE = "inactive"
STATE_LATE = "late"
STATE_ENDED = "ended"
STATE_BILLED = "billed"


class Booking(models.Model):
    STATE_PENDING = STATE_PENDING
    STATE_CANCELLED = STATE_CANCELLED
    STATE_ACTIVE = STATE_ACTIVE
    STATE_INACTIVE = STATE_INACTIVE
    STATE_LATE = STATE_LATE
    STATE_ENDED = STATE_ENDED
    STATE_BILLED = STATE_BILLED

    STATE_CHOICES = [
        (STATE_PENDING, "pending"),
        (STATE_CANCELLED, "cancelled"),
        (STATE_ACTIVE, "active"),
        (STATE_INACTIVE, "inactive"),
        (STATE_LATE, "late"),
        (STATE_ENDED, "ended"),
        (STATE_BILLED, "billed"),
    ]

    ALLOW_USER_UNLOCK_STATES = [
        STATE_PENDING,
        STATE_ACTIVE,
        STATE_INACTIVE,
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
    billing_account = models.ForeignKey(
        BillingAccount,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    state = models.CharField(
        max_length=16,
        choices=STATE_CHOICES,
        default=STATE_PENDING,
    )

    # Actual reservation times as visible to the user.
    reservation_time = DateTimeRangeField()

    # Full extents of time that this booking will block others from being created.
    block_time = DateTimeRangeField()

    # Actual times - when the vehicle was first unlocked and last locked.
    actual_start_time = DateTimeField(null=True, blank=True)
    actual_end_time = DateTimeField(null=True, blank=True)

    stripe_invoice_item_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "booking"
        # Ensure no overlapping uncancelled bookings on any vehicle.
        constraints = [
            ExclusionConstraint(
                name="prevent_overlaps",
                expressions=(
                    ("block_time", RangeOperators.OVERLAPS),
                    ("vehicle_id", RangeOperators.EQUAL),
                ),
                condition=~Q(state=STATE_CANCELLED),
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

    @property
    def duration(self):
        """Returns the booked duration of the booking, as a tuple of days and hours."""
        delta = self.reservation_time.upper - self.reservation_time.lower

        days = delta.days
        hours = delta.seconds / 3600

        return days, hours

    @property
    def cost(self):
        return calculate_booking_cost(
            self.user,
            self.vehicle,
            self.reservation_time.lower,
            self.reservation_time.upper,
        )


def get_available_vehicles(start, end, vehicle_types):
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
    ).filter(vehicle_type__in=vehicle_types)


def get_unavailable_vehicles(start, end, vehicle_types):
    vehicles = Vehicle.objects.filter(
        id__in=Subquery(
            Booking.objects.values("vehicle_id")
            .filter(
                ~Q(state=Booking.STATE_CANCELLED),
                block_time__overlap=TsTzRange(start, end, RangeBoundary()),
            )
            .order_by("vehicle_id")
            .distinct("vehicle_id")
        ),
        vehicle_type__in=vehicle_types,
    )

    results = []
    for v in vehicles:
        bookings = Booking.objects.filter(
            ~Q(state=Booking.STATE_CANCELLED),
            vehicle=v,
            block_time__overlap=TsTzRange(start, end, RangeBoundary()),
        ).order_by("block_time")

        log.debug(f"Overlapping bookings for vehicle {v}: {bookings}")

        if len(bookings) == 0:
            log.warning(f"No overlapping bookings for vehicle {v} found.")
            continue

        bf = bookings.first()
        # FIXME: Hardcoded block time window.
        print(
            f"Available before {bf.block_time.lower - timezone.timedelta(minutes=15)}"
        )

        bl = bookings.last()
        print(f"Available after {bl.block_time.upper}")

        # FIXME: Hardcoded block time window.
        v.available_before = bf.block_time.lower - timezone.timedelta(minutes=15)
        v.available_after = bl.block_time.upper

        results.append(v)

    return results


def get_current_booking_for_vehicle(vehicle):
    return Booking.objects.filter(
        ~Q(state=Booking.STATE_CANCELLED),
        reservation_time__contains=timezone.now(),
        vehicle=vehicle,
    ).first()
