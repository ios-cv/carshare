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

POLICY_CANCELLATION_CUTOFF_HOURS = 2
POLICY_BUFFER_TIME = 30
MAX_BOOKING_END_DAYS = 120


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
    def create_booking(user, vehicle, start, end, billing_account):
        reservation_time = DateTimeTZRange(lower=start, upper=end)
        block_time = DateTimeTZRange(
            lower=start, upper=end + timezone.timedelta(minutes=POLICY_BUFFER_TIME)
        )
        b = Booking(
            user=user,
            vehicle=vehicle,
            reservation_time=reservation_time,
            block_time=block_time,
            billing_account=billing_account,
        )

        b.save()

    def update_times(self, start, end):
        self.reservation_time = DateTimeTZRange(lower=start, upper=end)
        self.block_time = DateTimeTZRange(
            lower=start, upper=end + timezone.timedelta(minutes=POLICY_BUFFER_TIME)
        )

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

    def can_be_modified_by_user(self, user):
        """Returns whether the provided user is allowed to modify (edit/cancel/etc) this booking."""

        # User made the booking.
        if self.user == user:
            return True

        # User owns the billing account that made the booking.
        if user == self.billing_account.owner:
            return True

        # User is a member with "can_make_bookings" permission on the billing account.
        if user not in self.billing_account.members.all():
            return False

        for member in self.billing_account.billingaccountmember_set.all():
            if member.user == user:
                return member.can_make_bookings


def get_available_vehicles(start, end, vehicle_types):
    return Vehicle.objects.exclude(
        id__in=Subquery(
            Booking.objects.values("vehicle_id")
            .filter(
                ~Q(state=Booking.STATE_CANCELLED),
                block_time__overlap=TsTzRange(
                    start,
                    end + timezone.timedelta(minutes=POLICY_BUFFER_TIME),
                    RangeBoundary(),
                ),
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
                block_time__overlap=TsTzRange(
                    start,
                    end + timezone.timedelta(minutes=POLICY_BUFFER_TIME),
                    RangeBoundary(),
                ),
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
            block_time__overlap=TsTzRange(
                start,
                end + timezone.timedelta(minutes=POLICY_BUFFER_TIME),
                RangeBoundary(),
            ),
        ).order_by("block_time")

        log.debug(f"Overlapping bookings for vehicle {v}: {bookings}")

        if len(bookings) == 0:
            log.warning(f"No overlapping bookings for vehicle {v} found.")
            continue

        bf = bookings.first()
        if bf.block_time.lower >= timezone.now() - timezone.timedelta(
            minutes=POLICY_BUFFER_TIME
        ):
            log.debug(
                f"Available until {bf.block_time.lower - timezone.timedelta(minutes=POLICY_BUFFER_TIME)}"
            )

            v.available_before = bf.block_time.lower - timezone.timedelta(
                minutes=POLICY_BUFFER_TIME
            )
        else:
            v.available_before = None

        bl = bookings.last()
        if bl.block_time.upper < timezone.now() + timezone.timedelta(
            days=MAX_BOOKING_END_DAYS
        ):
            log.debug(f"Available from {bl.block_time.upper}")

            v.available_after = bl.block_time.upper
        else:
            v.available_after = None

        if v.available_before or v.available_after:
            results.append(v)

    return results


def get_current_booking_for_vehicle(vehicle):
    return Booking.objects.filter(
        ~Q(state=Booking.STATE_CANCELLED),
        reservation_time__contains=timezone.now(),
        vehicle=vehicle,
    ).first()


def user_can_access_booking(user, booking):
    """Returns whether the user should be allowed to access the vehicle for this booking."""
    if not (
        booking.billing_account.owner == user
        or booking.billing_account.memembers.contains(user)
    ):
        log.debug(
            f"User {user} does not have access to drive"
            f"for billing account {booking.billing_account}"
            f"used by booking {booking}"
        )
        return False

    if user.has_valid_driver_profile(
        profile_type=booking.billing_account.driver_profile_python_type,
        at=booking.reservation_time.upper,
    ):
        return True

    log.debug(
        f"User {user} does not have access a valid driver profile"
        f"of type {booking.billing_account.driver_profile_type}"
        f"to cover until the end of booking {booking}"
    )
