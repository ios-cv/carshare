"""Tests for the bookings app."""
import datetime

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from psycopg2.extras import DateTimeTZRange

from bookings.models import (
    Booking,
    POLICY_BUFFER_TIME,
    get_available_vehicles,
    get_current_booking_for_vehicle,
    user_can_access_booking,
)
from bookings.forms import gen_start_time, gen_end_time
from bookings.tasks import manage_booking_states
from bookings.templatetags import utils as booking_tags


# ── Booking model ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_booking_sets_times(make_user, make_vehicle, make_billing_account):
    user = make_user()
    vehicle = make_vehicle()
    ba = make_billing_account(owner=user, approved=True,
                               stripe_customer_id="cus_1",
                               stripe_setup_intent_active=True)
    start = timezone.now() + timezone.timedelta(hours=50)
    end = start + timezone.timedelta(hours=2)
    booking = Booking.create_booking(user=user, vehicle=vehicle, start=start, end=end,
                                     billing_account=ba)
    assert booking.reservation_time.lower == start
    assert booking.reservation_time.upper == end
    assert booking.block_time.upper == end + datetime.timedelta(minutes=POLICY_BUFFER_TIME)


@pytest.mark.django_db
def test_update_times(make_booking):
    b = make_booking()
    new_start = timezone.now() + timezone.timedelta(hours=200)
    new_end = new_start + timezone.timedelta(hours=3)
    b.update_times(new_start, new_end)
    assert b.reservation_time.lower == new_start
    assert b.reservation_time.upper == new_end


@pytest.mark.django_db
def test_reservation_ended_true(make_booking):
    b = make_booking(start=timezone.now() - timezone.timedelta(hours=4),
                     end=timezone.now() - timezone.timedelta(hours=2))
    assert b.reservation_ended() is True


@pytest.mark.django_db
def test_reservation_ended_false(make_booking):
    b = make_booking(start=timezone.now() + timezone.timedelta(hours=1),
                     end=timezone.now() + timezone.timedelta(hours=3))
    assert b.reservation_ended() is False


@pytest.mark.django_db
def test_reservation_started_true(make_booking):
    b = make_booking(start=timezone.now() - timezone.timedelta(hours=1),
                     end=timezone.now() + timezone.timedelta(hours=1))
    assert b.reservation_started() is True


@pytest.mark.django_db
def test_reservation_started_false(make_booking):
    b = make_booking(start=timezone.now() + timezone.timedelta(hours=1),
                     end=timezone.now() + timezone.timedelta(hours=3))
    assert b.reservation_started() is False


@pytest.mark.django_db
def test_reservation_in_progress(make_booking):
    b = make_booking(start=timezone.now() - timezone.timedelta(hours=1),
                     end=timezone.now() + timezone.timedelta(hours=1))
    assert b.reservation_in_progress() is True


@pytest.mark.django_db
def test_in_closeable_state_active(make_booking):
    b = make_booking(state=Booking.STATE_ACTIVE)
    assert b.in_closeable_state() is True


@pytest.mark.django_db
def test_in_closeable_state_pending(make_booking):
    b = make_booking(state=Booking.STATE_PENDING)
    assert b.in_closeable_state() is True


@pytest.mark.django_db
def test_in_closeable_state_late(make_booking):
    b = make_booking(state=Booking.STATE_LATE)
    assert b.in_closeable_state() is True


@pytest.mark.django_db
def test_in_closeable_state_cancelled_false(make_booking):
    b = make_booking(state=Booking.STATE_CANCELLED)
    assert b.in_closeable_state() is False


@pytest.mark.django_db
def test_cancelled_property(make_booking):
    b = make_booking(state=Booking.STATE_CANCELLED)
    assert b.cancelled is True
    b2 = make_booking(state=Booking.STATE_ACTIVE)
    assert b2.cancelled is False


@pytest.mark.django_db
def test_duration_calculation(make_booking):
    start = timezone.now() + timezone.timedelta(hours=1000)
    end = start + timezone.timedelta(days=1, hours=3)
    b = make_booking(start=start, end=end)
    days, hours = b.duration
    assert days == 1
    assert hours == 3


@pytest.mark.django_db
def test_can_be_modified_by_user_owner(make_user, make_booking):
    user = make_user()
    b = make_booking(user=user)
    assert b.can_be_modified_by_user(user) is True


@pytest.mark.django_db
def test_can_be_modified_by_user_billing_account_owner(make_user, make_billing_account, make_booking):
    owner = make_user()
    user2 = make_user()
    ba = make_billing_account(owner=owner, approved=True,
                               stripe_customer_id="cus_bo",
                               stripe_setup_intent_active=True)
    b = make_booking(user=user2, billing_account=ba)
    assert b.can_be_modified_by_user(owner) is True


@pytest.mark.django_db
def test_can_be_modified_by_user_unrelated_false(make_user, make_booking):
    user = make_user()
    other = make_user()
    b = make_booking(user=user)
    assert b.can_be_modified_by_user(other) is False


# ── get_available_vehicles ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_available_vehicles_no_bookings(make_vehicle, make_vehicle_type):
    vt = make_vehicle_type()
    vehicle = make_vehicle(vehicle_type=vt)
    start = timezone.now() + timezone.timedelta(hours=400)
    end = start + timezone.timedelta(hours=2)
    result = get_available_vehicles(start, end, [vt])
    assert vehicle in result


@pytest.mark.django_db
def test_get_available_vehicles_cancelled_not_excluded(make_vehicle, make_booking, make_vehicle_type):
    vt = make_vehicle_type()
    vehicle = make_vehicle(vehicle_type=vt)
    start = timezone.now() + timezone.timedelta(hours=500)
    end = start + timezone.timedelta(hours=2)
    make_booking(vehicle=vehicle, start=start, end=end, state=Booking.STATE_CANCELLED)
    result = get_available_vehicles(start, end, [vt])
    assert vehicle in result


@pytest.mark.django_db
def test_get_available_vehicles_active_booking_excludes(make_vehicle, make_booking, make_vehicle_type):
    vt = make_vehicle_type()
    vehicle = make_vehicle(vehicle_type=vt)
    start = timezone.now() + timezone.timedelta(hours=600)
    end = start + timezone.timedelta(hours=2)
    make_booking(vehicle=vehicle, start=start, end=end, state=Booking.STATE_ACTIVE)
    result = get_available_vehicles(start, end, [vt])
    assert vehicle not in result


# ── get_current_booking_for_vehicle ──────────────────────────────────────────

@pytest.mark.django_db
def test_get_current_booking_for_vehicle_returns_booking(make_vehicle, make_booking):
    vehicle = make_vehicle()
    start = timezone.now() - timezone.timedelta(hours=1)
    end = timezone.now() + timezone.timedelta(hours=1)
    b = make_booking(vehicle=vehicle, start=start, end=end, state=Booking.STATE_ACTIVE)
    result = get_current_booking_for_vehicle(vehicle)
    assert result == b


@pytest.mark.django_db
def test_get_current_booking_for_vehicle_returns_none(make_vehicle):
    vehicle = make_vehicle()
    result = get_current_booking_for_vehicle(vehicle)
    assert result is None


# ── user_can_access_booking ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_user_can_access_booking_unrelated_false(make_user, make_booking, make_billing_account):
    user = make_user()
    other = make_user()
    b = make_booking(user=user)
    assert user_can_access_booking(other, b) is False


@pytest.mark.django_db
def test_user_can_access_booking_owner_with_dp(make_user, make_billing_account,
                                                 make_full_driver_profile, make_booking):
    user = make_user(mobile="07700000001")
    ba = make_billing_account(owner=user, approved=True,
                               stripe_customer_id="cus_abc",
                               stripe_setup_intent_active=True)
    make_full_driver_profile(user=user, approved=True)
    b = make_booking(user=user, billing_account=ba)
    assert user_can_access_booking(user, b) is True


# ── bookings forms ────────────────────────────────────────────────────────────

def test_gen_start_time_rounds_up():
    dt = datetime.datetime(2025, 6, 1, 10, 13, 0, tzinfo=datetime.timezone.utc)
    with pytest.MonkeyPatch().context() as m:
        result = gen_start_time(dt)
    # Should round to nearest 5 minutes then add 5
    assert result.second == 0
    assert result.microsecond == 0
    assert result > dt


def test_gen_end_time_is_one_hour_after_start():
    dt = datetime.datetime(2025, 6, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
    start = gen_start_time(dt)
    end = gen_end_time(dt)
    from django.utils import timezone as tz
    assert end == start + tz.timedelta(hours=1)


# ── bookings tasks ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_manage_booking_states_active_to_late(make_booking):
    start = timezone.now() - timezone.timedelta(hours=4)
    end = timezone.now() - timezone.timedelta(hours=2)
    b = make_booking(start=start, end=end, state=Booking.STATE_ACTIVE)
    manage_booking_states()
    b.refresh_from_db()
    assert b.state == Booking.STATE_LATE


@pytest.mark.django_db
def test_manage_booking_states_pending_to_ended(make_booking):
    start = timezone.now() - timezone.timedelta(hours=4)
    end = timezone.now() - timezone.timedelta(hours=2)
    b = make_booking(start=start, end=end, state=Booking.STATE_PENDING)
    manage_booking_states()
    b.refresh_from_db()
    assert b.state == Booking.STATE_ENDED


@pytest.mark.django_db
def test_manage_booking_states_inactive_to_ended(make_booking):
    start = timezone.now() - timezone.timedelta(hours=4)
    end = timezone.now() - timezone.timedelta(hours=2)
    b = make_booking(start=start, end=end, state=Booking.STATE_INACTIVE)
    manage_booking_states()
    b.refresh_from_db()
    assert b.state == Booking.STATE_ENDED


@pytest.mark.django_db
def test_manage_booking_states_future_unchanged(make_booking):
    start = timezone.now() + timezone.timedelta(hours=1)
    end = start + timezone.timedelta(hours=2)
    b = make_booking(start=start, end=end, state=Booking.STATE_PENDING)
    manage_booking_states()
    b.refresh_from_db()
    assert b.state == Booking.STATE_PENDING


# ── template tags ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_user_can_access_booking_tag(make_user, make_booking, make_billing_account,
                                      make_full_driver_profile):
    user = make_user(mobile="07700000002")
    ba = make_billing_account(owner=user, approved=True,
                               stripe_customer_id="cus_tag",
                               stripe_setup_intent_active=True)
    make_full_driver_profile(user=user, approved=True)
    b = make_booking(user=user, billing_account=ba)
    result = booking_tags.user_can_access_booking(user, b)
    assert result is True


# ── bookings views ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_search_unauthenticated_redirects_to_login():
    client = Client()
    url = reverse("bookings_search")
    response = client.get(url)
    assert response.status_code == 302
    assert "login" in response["Location"]


@pytest.mark.django_db
def test_search_authenticated_without_permission_redirects(make_user):
    user = make_user()  # no mobile, no billing account
    client = Client()
    client.force_login(user)
    url = reverse("bookings_search")
    response = client.get(url)
    assert response.status_code == 302


@pytest.mark.django_db
def test_cancel_not_owner_redirects(make_user, make_booking):
    owner = make_user()
    other = make_user(mobile="07700000003")
    b = make_booking(user=owner)
    # Give other user enough permissions to pass the decorator
    from billing.models import BillingAccount, BillingAccountMember
    ba = BillingAccount.objects.create(
        owner=other,
        account_type="p",
        driver_profile_type="f",
        stripe_customer_id="cus_oth",
        stripe_setup_intent_active=True,
        approved_at=timezone.now(),
    )
    client = Client()
    client.force_login(other)
    url = reverse("bookings_cancel", kwargs={"booking": b.id})
    response = client.get(url)
    assert response.status_code == 302
    b.refresh_from_db()
    assert b.state != Booking.STATE_CANCELLED

