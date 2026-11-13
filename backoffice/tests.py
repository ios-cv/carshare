from django.test import TransactionTestCase, Client
from django.forms import ValidationError
from bookings.models import Booking
from hardware.models import Vehicle, Box, Bay, VehicleType, Station, Card
from billing.models import BillingAccount
from drivers.models import FullDriverProfile
from users.models import User
from datetime import datetime, timezone, timedelta
from backoffice import views
from backoffice.forms import BackofficeEditBookingForm
import time


# Create your tests here.
class TestEditBookings(TransactionTestCase):
    fixtures = ["example.json"]

    def test_booking_creation(self):
        user = User.objects.first()
        self.assertIsNotNone(user)
        vehicle = Vehicle.objects.first()
        self.assertIsNotNone(vehicle)
        ba = BillingAccount.objects.first()
        self.assertIsNotNone(ba)

        Booking.create_booking(
            user=user,
            vehicle=vehicle,
            start=datetime.now(timezone.utc) + timedelta(hours=1),
            end=datetime.now(timezone.utc) + timedelta(hours=2),
            billing_account=ba,
        )
        booking = Booking.objects.last()
        self.assertEqual(booking.user, user)
        self.assertEqual(booking.vehicle, vehicle)
        self.assertEqual(booking.state, "pending")

    def test_booking_transitions(self):
        booking = Booking.objects.last()
        self.assertIsNotNone(booking)
        booking.state = "pending"
        #'pending' can transition to 'active', 'cancelled', 'inactive', 'ended'
        self.assertEqual(booking.can_transition_to("cancelled"), True)
        self.assertEqual(booking.can_transition_to("inactive"), True)
        self.assertEqual(booking.can_transition_to("late"), False)
        self.assertEqual(booking.can_transition_to("pending"), True)
        self.assertEqual(booking.can_transition_to("ended"), True)
        self.assertEqual(booking.can_transition_to("billed"), False)
        self.assertEqual(booking.can_transition_to("active"), True)
        booking.state = "active"
        #'active' can transition to 'inactive', 'late'
        self.assertEqual(booking.can_transition_to("cancelled"), False)
        self.assertEqual(booking.can_transition_to("inactive"), True)
        self.assertEqual(booking.can_transition_to("late"), True)
        self.assertEqual(booking.can_transition_to("pending"), False)
        self.assertEqual(booking.can_transition_to("ended"), False)
        self.assertEqual(booking.can_transition_to("billed"), False)
        self.assertEqual(booking.can_transition_to("active"), True)
        booking.state = "inactive"
        #'inactive' can transition to 'ended', 'active'
        self.assertEqual(booking.can_transition_to("cancelled"), False)
        self.assertEqual(booking.can_transition_to("inactive"), True)
        self.assertEqual(booking.can_transition_to("late"), False)
        self.assertEqual(booking.can_transition_to("pending"), False)
        self.assertEqual(booking.can_transition_to("ended"), True)
        self.assertEqual(booking.can_transition_to("billed"), False)
        self.assertEqual(booking.can_transition_to("active"), True)
        booking.state = "late"
        #'late' can transition to 'inactive'
        self.assertEqual(booking.can_transition_to("cancelled"), False)
        self.assertEqual(booking.can_transition_to("inactive"), True)
        self.assertEqual(booking.can_transition_to("late"), True)
        self.assertEqual(booking.can_transition_to("pending"), False)
        self.assertEqual(booking.can_transition_to("ended"), False)
        self.assertEqual(booking.can_transition_to("billed"), False)
        self.assertEqual(booking.can_transition_to("active"), False)
        booking.state = "ended"
        #'ended' can transition to 'billed'
        self.assertEqual(booking.can_transition_to("cancelled"), False)
        self.assertEqual(booking.can_transition_to("inactive"), False)
        self.assertEqual(booking.can_transition_to("late"), False)
        self.assertEqual(booking.can_transition_to("pending"), False)
        self.assertEqual(booking.can_transition_to("ended"), True)
        self.assertEqual(booking.can_transition_to("billed"), True)
        self.assertEqual(booking.can_transition_to("active"), False)
        booking.state = "billed"
        #'billed' cannot transition to any state
        self.assertEqual(booking.can_transition_to("cancelled"), False)
        self.assertEqual(booking.can_transition_to("inactive"), False)
        self.assertEqual(booking.can_transition_to("late"), False)
        self.assertEqual(booking.can_transition_to("pending"), False)
        self.assertEqual(booking.can_transition_to("ended"), False)
        self.assertEqual(booking.can_transition_to("billed"), True)
        self.assertEqual(booking.can_transition_to("active"), False)

    def test_backoffice_edit_booking_form(self):
        booking = Booking.objects.first()
        self.assertIsNotNone(booking)
        # ensure the booking is in a known state for testing
        self.assertEqual(booking.state, "inactive")
        # ensure the booking edit form is valid with the test booking data
        form = BackofficeEditBookingForm(
            instance=booking,
            data={
                "vehicle": booking.vehicle.pk,
                "state": booking.state,
                "reservation_time_0": (
                    booking.reservation_time.lower if booking.reservation_time else ""
                ),
                "reservation_time_1": (
                    booking.reservation_time.upper if booking.reservation_time else ""
                ),
                "actual_start_time_0": (
                    booking.actual_start_time.strftime("%Y-%m-%d")
                    if booking.actual_start_time
                    else ""
                ),
                "actual_start_time_1": (
                    booking.actual_start_time.strftime("%H:%M")
                    if booking.actual_start_time
                    else ""
                ),
                "actual_end_time_0": (
                    booking.actual_end_time.strftime("%Y-%m-%d")
                    if booking.actual_end_time
                    else ""
                ),
                "actual_end_time_1": (
                    booking.actual_end_time.strftime("%H:%M")
                    if booking.actual_end_time
                    else ""
                ),
                "updated_at": booking.updated_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
            },
        )
        is_valid = form.is_valid()
        self.assertTrue(is_valid)

        # test invalid transtion
        form = BackofficeEditBookingForm(
            instance=booking,
            data={
                "vehicle": booking.vehicle.pk,
                "state": "billed",
                "reservation_time_0": (
                    booking.reservation_time.lower if booking.reservation_time else ""
                ),
                "reservation_time_1": (
                    booking.reservation_time.upper if booking.reservation_time else ""
                ),
                "actual_start_time_0": (
                    booking.actual_start_time.strftime("%Y-%m-%d")
                    if booking.actual_start_time
                    else ""
                ),
                "actual_start_time_1": (
                    booking.actual_start_time.strftime("%H:%M")
                    if booking.actual_start_time
                    else ""
                ),
                "actual_end_time_0": (
                    booking.actual_end_time.strftime("%Y-%m-%d")
                    if booking.actual_end_time
                    else ""
                ),
                "actual_end_time_1": (
                    booking.actual_end_time.strftime("%H:%M")
                    if booking.actual_end_time
                    else ""
                ),
                "updated_at": booking.updated_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
            },
        )
        is_valid = form.is_valid()
        self.assertFalse(is_valid)
        self.assertIn("__all__", form.errors)
        # If the state provided in the form is not in the allowed states then it should not pass the cleaning process
        # as it won't be one of the choices passed to the choicefield and so will be None
        self.assertIn(
            "Transition from inactive to None not allowed.", form.errors["__all__"]
        )

        # test valid state transition
        form = BackofficeEditBookingForm(
            instance=booking,
            data={
                "vehicle": booking.vehicle.pk,
                "state": "active",
                "reservation_time_0": (
                    booking.reservation_time.lower if booking.reservation_time else ""
                ),
                "reservation_time_1": (
                    booking.reservation_time.upper if booking.reservation_time else ""
                ),
                "actual_start_time_0": (
                    booking.actual_start_time.strftime("%Y-%m-%d")
                    if booking.actual_start_time
                    else ""
                ),
                "actual_start_time_1": (
                    booking.actual_start_time.strftime("%H:%M")
                    if booking.actual_start_time
                    else ""
                ),
                "actual_end_time_0": (
                    booking.actual_end_time.strftime("%Y-%m-%d")
                    if booking.actual_end_time
                    else ""
                ),
                "actual_end_time_1": (
                    booking.actual_end_time.strftime("%H:%M")
                    if booking.actual_end_time
                    else ""
                ),
                "updated_at": booking.updated_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
            },
        )
        is_valid = form.is_valid()
        self.assertTrue(is_valid)

        # test race condition
        form = BackofficeEditBookingForm(
            instance=booking,
            data={
                "vehicle": booking.vehicle.pk,
                "state": booking.state,
                "reservation_time_0": (
                    booking.reservation_time.lower if booking.reservation_time else ""
                ),
                "reservation_time_1": (
                    booking.reservation_time.upper if booking.reservation_time else ""
                ),
                "actual_start_time_0": (
                    booking.actual_start_time.strftime("%Y-%m-%d")
                    if booking.actual_start_time
                    else ""
                ),
                "actual_start_time_1": (
                    booking.actual_start_time.strftime("%H:%M")
                    if booking.actual_start_time
                    else ""
                ),
                "actual_end_time_0": (
                    booking.actual_end_time.strftime("%Y-%m-%d")
                    if booking.actual_end_time
                    else ""
                ),
                "actual_end_time_1": (
                    booking.actual_end_time.strftime("%H:%M")
                    if booking.actual_end_time
                    else ""
                ),
                "updated_at": (booking.updated_at - timedelta(seconds=1)).strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                ),
            },
        )

        is_valid = form.is_valid()
        self.assertFalse(is_valid)
        self.assertIn("__all__", form.errors)
        self.assertIn(
            "This booking has been updated by a different process!",
            form.errors["__all__"],
        )
