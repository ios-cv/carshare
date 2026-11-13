from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.db import (
    IntegrityError,
    OperationalError,
    close_old_connections,
    connections,
    transaction,
)
from django.test import TransactionTestCase, Client
from django.urls import reverse

from bookings.forms import BookingSearchForm
from bookings.models import Booking, get_available_vehicles
from bookings.tasks import manage_booking_states
from hardware.models import BoxAction
from test_support import factories as f
from test_support.cases import FrozenTestCase


class BookingTests(FrozenTestCase):
    def setUp(self):
        super().setUp()
        self.person = f.user()
        self.account = f.account(self.person)
        f.profile(self.person)
        self.car = f.vehicle()

    def test_create_booking_persists_reserved_and_buffered_times(self):
        start = f.NOW + timedelta(hours=1)
        end = start + timedelta(hours=2)
        Booking.create_booking(self.person, self.car, start, end, self.account)
        b = Booking.objects.get()
        self.assertEqual(b.reservation_time.lower, start)
        self.assertEqual(b.reservation_time.upper, end)
        self.assertEqual(b.block_time.upper, end + timedelta(minutes=15))

    def test_overlap_is_rejected_by_database(self):
        f.booking(self.person, self.car, self.account)
        with self.assertRaises(IntegrityError), transaction.atomic():
            f.booking(self.person, self.car, self.account)
        self.assertEqual(Booking.objects.count(), 1)

    def test_buffer_boundary(self):
        b = f.booking(self.person, self.car, self.account)
        for offset, available in [(14, False), (15, True), (16, True)]:
            with self.subTest(offset=offset):
                start = b.reservation_time.upper + timedelta(minutes=offset)
                self.assertEqual(
                    get_available_vehicles(
                        start, start + timedelta(hours=1), [self.car.vehicle_type]
                    )
                    .filter(pk=self.car.pk)
                    .exists(),
                    available,
                )

    def test_cancelled_interval_can_be_rebooked(self):
        f.booking(self.person, self.car, self.account, state="cancelled")
        f.booking(self.person, self.car, self.account)
        self.assertEqual(Booking.objects.count(), 2)

    def test_search_form_duration_and_horizon(self):
        start = f.NOW + timedelta(hours=1)
        for duration, valid in [(29, False), (30, True), (31, True)]:
            with self.subTest(duration=duration):
                end = start + timedelta(minutes=duration)
                form = BookingSearchForm(
                    {
                        "start_0": start.date(),
                        "start_1": start.time(),
                        "end_0": end.date(),
                        "end_1": end.time(),
                        "vehicle_types": [self.car.vehicle_type_id],
                    }
                )
                self.assertEqual(form.is_valid(), valid, form.errors)

    def test_search_rejects_past_start_and_far_end(self):
        for start, end in [
            (f.NOW - timedelta(minutes=6), f.NOW + timedelta(hours=1)),
            (f.NOW + timedelta(hours=1), f.NOW + timedelta(days=121)),
        ]:
            form = BookingSearchForm(
                {
                    "start_0": start.date(),
                    "start_1": start.time(),
                    "end_0": end.date(),
                    "end_1": end.time(),
                    "vehicle_types": [self.car.vehicle_type_id],
                }
            )
            self.assertFalse(form.is_valid())

    def test_confirmation_creates_booking_for_allowed_account(self):
        self.client.force_login(self.person)
        start = f.NOW + timedelta(hours=1)
        end = start + timedelta(hours=2)
        response = self.client.post(
            reverse("bookings_confirm"),
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "vehicle_id": self.car.pk,
                "billing_account": self.account.pk,
                "confirmed": "True",
            },
        )
        self.assertRedirects(
            response, reverse("bookings_history"), fetch_redirect_response=False
        )
        b = Booking.objects.get()
        self.assertEqual(b.user, self.person)
        self.assertEqual(b.billing_account, self.account)

    def test_confirmation_rejects_foreign_account(self):
        other_account = f.account(f.user())
        self.client.force_login(self.person)
        start = f.NOW + timedelta(hours=1)
        response = self.client.post(
            reverse("bookings_confirm"),
            {
                "start": start.isoformat(),
                "end": (start + timedelta(hours=1)).isoformat(),
                "vehicle_id": self.car.pk,
                "billing_account": other_account.pk,
                "confirmed": "True",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.exists())

    def test_unrelated_user_cannot_cancel(self):
        b = f.booking(self.person, self.car, self.account)
        other = f.user()
        f.account(other)
        self.client.force_login(other)
        self.client.get(reverse("bookings_cancel", args=[b.pk]))
        b.refresh_from_db()
        self.assertEqual(b.state, "pending")

    def test_owner_can_cancel(self):
        b = f.booking(self.person, self.car, self.account)
        self.client.force_login(self.person)
        self.client.get(reverse("bookings_cancel", args=[b.pk]))
        b.refresh_from_db()
        self.assertEqual(b.state, "cancelled")

    def test_confirmation_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.person)
        self.assertEqual(client.post(reverse("bookings_confirm"), {}).status_code, 403)
        self.assertFalse(Booking.objects.exists())

    def test_unlock_and_late_lock_preserve_first_start(self):
        b = f.booking(
            self.person,
            self.car,
            self.account,
            start=f.NOW - timedelta(minutes=30),
            end=f.NOW + timedelta(minutes=30),
        )
        self.client.force_login(self.person)
        self.client.get(reverse("bookings_unlock", args=[b.pk]))
        b.refresh_from_db()
        box = self.car.box
        box.refresh_from_db()
        self.assertEqual(b.state, "active")
        self.assertEqual(box.current_booking, b)
        self.assertFalse(box.locked)
        self.assertEqual(b.actual_start_time, f.NOW)
        with patch(
            "django.utils.timezone.now", return_value=f.NOW + timedelta(hours=1)
        ):
            manage_booking_states.run()
            self.client.get(reverse("bookings_lock", args=[b.pk]))
            manage_booking_states.run()
        b.refresh_from_db()
        box.refresh_from_db()
        self.assertEqual(b.state, "ended")
        self.assertIsNone(box.current_booking)
        self.assertTrue(box.locked)
        self.assertEqual(b.actual_start_time, f.NOW)
        self.assertEqual(BoxAction.objects.count(), 2)

    def test_unauthorised_unlock_creates_no_command(self):
        b = f.booking(
            self.person, self.car, self.account, start=f.NOW - timedelta(minutes=5)
        )
        other = f.user()
        f.account(other)
        f.profile(other)
        self.client.force_login(other)
        self.client.get(reverse("bookings_unlock", args=[b.pk]))
        self.assertFalse(BoxAction.objects.exists())
        self.car.box.refresh_from_db()
        self.assertTrue(self.car.box.locked)

    def test_state_task_is_repeatable(self):
        for index, (state, expected) in enumerate(
            [
                ("active", "late"),
                ("pending", "ended"),
                ("inactive", "ended"),
                ("cancelled", "cancelled"),
            ]
        ):
            start = f.NOW - timedelta(days=index + 1, hours=2)
            end = start + timedelta(hours=1)
            b = f.booking(
                self.person, self.car, self.account, start=start, end=end, state=state
            )
            manage_booking_states.run()
            manage_booking_states.run()
            b.refresh_from_db()
            self.assertEqual(b.state, expected)


class BookingConcurrencyTests(TransactionTestCase):
    def test_simultaneous_overlapping_reservations_have_one_winner(self):
        person = f.user()
        account = f.account(person)
        car = f.vehicle()
        gate = Barrier(2)

        def reserve():
            close_old_connections()
            try:
                gate.wait(timeout=10)
                try:
                    with transaction.atomic():
                        with connections["default"].cursor() as cursor:
                            cursor.execute("SET LOCAL lock_timeout = '5s'")
                        f.booking(person, car, account)
                    return "created"
                except IntegrityError:
                    return "conflict"
                except OperationalError as error:
                    # Exclusion-index contenders can deadlock. PostgreSQL aborts
                    # one transaction, preserving the no-overlap invariant.
                    # This does not assert that the HTTP view retries deadlocks.
                    if getattr(error.__cause__, "pgcode", None) == "40P01":
                        return "conflict"
                    raise
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(reserve) for _ in range(2)]
            results = [future.result(timeout=15) for future in futures]
        self.assertCountEqual(results, ["created", "conflict"])
        self.assertEqual(Booking.objects.count(), 1)
