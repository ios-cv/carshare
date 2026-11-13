"""Small ORM builders: explicit relationships, no production data or fixture IDs."""

from datetime import datetime, timedelta, timezone as dt_timezone
from itertools import count
from uuid import uuid4

from django.utils import timezone
from psycopg2.extras import DateTimeTZRange

from billing.models import BillingAccount, BillingAccountMember
from bookings.models import Booking
from drivers.models import FullDriverProfile
from hardware.models import Bay, Box, Firmware, Station, Vehicle, VehicleType
from users.models import User

NOW = datetime(2026, 6, 15, 10, tzinfo=dt_timezone.utc)
sequence = count(1)


def user(**kwargs):
    n = next(sequence)
    defaults = dict(
        username=f"user{n}",
        email=f"user{n}@example.invalid",
        first_name="Test",
        last_name="Driver",
        mobile="07700000000",
    )
    defaults.update(kwargs)
    return User.objects.create_user(password="test-password", **defaults)


def account(owner, **kwargs):
    defaults = dict(
        account_type="p",
        driver_profile_type="f",
        approved_at=NOW,
        stripe_customer_id=f"cus_test_{next(sequence)}",
        stripe_setup_intent_active=True,
    )
    defaults.update(kwargs)
    return BillingAccount.objects.create(owner=owner, **defaults)


def profile(owner, **kwargs):
    defaults = dict(
        created_at=NOW,
        updated_at=NOW,
        approved_at=NOW,
        approved_to_drive=True,
        expires_at=NOW + timedelta(days=365),
    )
    defaults.update(kwargs)
    return FullDriverProfile.objects.create(user=owner, **defaults)


def member(billing_account, person, can_book=False):
    return BillingAccountMember.objects.create(
        billing_account=billing_account,
        user=person,
        can_make_bookings=can_book,
        created_at=NOW,
        updated_at=NOW,
    )


def vehicle(**kwargs):
    n = next(sequence)
    firmware, _ = Firmware.objects.get_or_create(
        version=0, defaults=dict(created_at=NOW, notes="Test only", bin_file="")
    )
    box = Box.objects.create(
        serial=n, secret=uuid4(), desired_firmware_version=firmware
    )
    station = Station.objects.create(name=f"Test station {n}")
    bay = Bay.objects.create(name=f"Bay {n}", station=station)
    defaults = dict(
        name=f"Test vehicle {n}",
        registration=f"T{n:06d}",
        vin=f"TEST-{n}",
        display_model="Test EV",
        firmware_model="test",
        box=box,
        bay=bay,
        vehicle_type=VehicleType.objects.create(name=f"Type {n}"),
    )
    defaults.update(kwargs)
    return Vehicle.objects.create(**defaults)


def booking(person, car, billing_account, start=None, end=None, **kwargs):
    start = start or NOW + timedelta(hours=1)
    end = end or start + timedelta(hours=2)
    defaults = dict(
        state=Booking.STATE_PENDING,
        reservation_time=DateTimeTZRange(start, end),
        block_time=DateTimeTZRange(start, end + timedelta(minutes=15)),
    )
    defaults.update(kwargs)
    return Booking.objects.create(
        user=person, vehicle=car, billing_account=billing_account, **defaults
    )
