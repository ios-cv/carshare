"""Shared pytest fixtures for the carshare test suite."""
import datetime
import uuid

import pytest
from django.utils import timezone
from psycopg2.extras import DateTimeTZRange


# ---------------------------------------------------------------------------
# Autouse: ensure django.contrib.sites has a Site row with id=1
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _setup_site(db):
    from django.contrib.sites.models import Site
    Site.objects.get_or_create(id=1, defaults={"domain": "localhost", "name": "localhost"})


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def make_user(db):
    from users.models import User

    counter = {"n": 0}

    def _make(email=None, password="password123", is_operator=False, mobile=None,
              first_name="Test", last_name="User"):
        counter["n"] += 1
        if email is None:
            email = f"user{counter['n']}@example.com"
        u = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_operator=is_operator,
            mobile=mobile,
        )
        return u

    return _make


@pytest.fixture
def make_operator_user(make_user):
    def _make(**kwargs):
        return make_user(is_operator=True, **kwargs)
    return _make


# ---------------------------------------------------------------------------
# Hardware fixtures (needed by billing/bookings)
# ---------------------------------------------------------------------------

@pytest.fixture
def make_firmware(db):
    from hardware.models import Firmware

    counter = {"n": 0}

    def _make():
        counter["n"] += 1
        return Firmware.objects.create(
            version=counter["n"],
            created_at=timezone.now(),
            notes="test firmware",
            bin_file="hardware/firmware/test.bin",
        )

    return _make


@pytest.fixture
def make_box(db, make_firmware):
    from hardware.models import Box

    def _make(firmware=None):
        if firmware is None:
            firmware = make_firmware()
        return Box.objects.create(
            serial=int(uuid.uuid4()) % (2**32),
            secret=uuid.uuid4(),
            locked=True,
            desired_firmware_version=firmware,
        )

    return _make


@pytest.fixture
def make_station(db):
    from hardware.models import Station

    counter = {"n": 0}

    def _make(name=None):
        counter["n"] += 1
        return Station.objects.create(name=name or f"Station {counter['n']}")

    return _make


@pytest.fixture
def make_bay(db, make_station):
    from hardware.models import Bay

    counter = {"n": 0}

    def _make(station=None):
        counter["n"] += 1
        if station is None:
            station = make_station()
        return Bay.objects.create(name=f"Bay {counter['n']}", station=station)

    return _make


@pytest.fixture
def make_vehicle_type(db):
    from hardware.models import VehicleType

    counter = {"n": 0}

    def _make(name=None):
        counter["n"] += 1
        return VehicleType.objects.create(name=name or f"Type {counter['n']}")

    return _make


@pytest.fixture
def make_vehicle(db, make_box, make_bay, make_vehicle_type):
    from hardware.models import Vehicle

    counter = {"n": 0}

    def _make(box=None, bay=None, vehicle_type=None):
        counter["n"] += 1
        if box is None:
            box = make_box()
        if bay is None:
            bay = make_bay()
        if vehicle_type is None:
            vehicle_type = make_vehicle_type()
        return Vehicle.objects.create(
            name=f"Vehicle {counter['n']}",
            display_model="Test Model",
            registration=f"T{counter['n']:02d}TST",
            vin=f"VIN{counter['n']:010d}",
            vehicle_type=vehicle_type,
            bay=bay,
            firmware_model="test",
            box=box,
        )

    return _make


# ---------------------------------------------------------------------------
# Billing fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def make_billing_account(db, make_user):
    from billing.models import BillingAccount

    def _make(owner=None, account_type="p", driver_profile_type="f",
              approved=False, credit_account=False,
              stripe_customer_id=None, stripe_setup_intent_active=False,
              account_name="Test Business"):
        if owner is None:
            owner = make_user()
        ba = BillingAccount(
            owner=owner,
            account_type=account_type,
            driver_profile_type=driver_profile_type,
            credit_account=credit_account,
            stripe_customer_id=stripe_customer_id,
            stripe_setup_intent_active=stripe_setup_intent_active,
        )
        if account_type == "b":
            ba.account_name = account_name
        if approved:
            ba.approved_at = timezone.now()
        ba.save()
        return ba

    return _make


# ---------------------------------------------------------------------------
# Booking fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def make_booking(db, make_user, make_vehicle, make_billing_account):
    from bookings.models import Booking

    counter = {"n": 0}

    def _make(user=None, vehicle=None, billing_account=None,
              start=None, end=None, state=Booking.STATE_PENDING):
        counter["n"] += 1
        if user is None:
            user = make_user()
        if vehicle is None:
            vehicle = make_vehicle()
        if billing_account is None:
            billing_account = make_billing_account(owner=user, approved=True,
                                                    stripe_customer_id="cus_test",
                                                    stripe_setup_intent_active=True)
        if start is None:
            # Use unique times to avoid ExclusionConstraint violations
            offset = counter["n"] * 100
            start = timezone.now() + timezone.timedelta(hours=offset)
        if end is None:
            end = start + timezone.timedelta(hours=2)
        b = Booking(
            user=user,
            vehicle=vehicle,
            billing_account=billing_account,
            reservation_time=DateTimeTZRange(start, end),
            block_time=DateTimeTZRange(start, end + timezone.timedelta(minutes=15)),
            state=state,
        )
        b.save()
        return b

    return _make


# ---------------------------------------------------------------------------
# Driver profile fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def make_full_driver_profile(db, make_user):
    from drivers.models import FullDriverProfile

    def _make(user=None, approved=False, expires_at=None, submitted=False):
        if user is None:
            user = make_user()
        dp = FullDriverProfile(
            user=user,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        if submitted:
            dp.submitted_at = timezone.now()
        if approved:
            dp.approved_at = timezone.now()
            dp.approved_to_drive = True
            dp.expires_at = expires_at or (timezone.now() + timezone.timedelta(days=365))
        elif expires_at is not None:
            dp.expires_at = expires_at
        dp.save()
        return dp

    return _make


@pytest.fixture
def make_external_driver_profile(db, make_user):
    from drivers.models import ExternalDriverProfile

    def _make(user=None, approved=False, expires_at=None):
        if user is None:
            user = make_user()
        dp = ExternalDriverProfile(
            user=user,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        if approved:
            dp.approved_at = timezone.now()
            dp.approved_to_drive = True
            dp.expires_at = expires_at or (timezone.now() + timezone.timedelta(days=365))
        elif expires_at is not None:
            dp.expires_at = expires_at
        dp.save()
        return dp

    return _make
