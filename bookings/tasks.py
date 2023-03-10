import logging

from celery import shared_task

from django.utils import timezone

from .models import Booking

log = logging.getLogger(__name__)


@shared_task(name="manage_booking_states")
def manage_booking_states():
    now = timezone.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    log.info(f"Running manage_booking_states job at {current_time}")

    # Move active bookings that should have ended to "late" state.
    bookings = Booking.objects.filter(
        state=Booking.STATE_ACTIVE,
        reservation_time__endswith__lt=now,
    )

    for booking in bookings:
        log.info(f"Marking booking as late: {booking.id}")
        booking.state = Booking.STATE_LATE
        booking.save()

    # Move pending bookings that have ended to the "ended" state.
    bookings = Booking.objects.filter(
        state=Booking.STATE_PENDING,
        reservation_time__endswith__lt=now,
    )

    for booking in bookings:
        log.info(f"Marking booking as ended: {booking.id}")
        booking.state = Booking.STATE_ENDED
        booking.save()

    # Move inactive bookings that have ended to the "ended" state.
    bookings = Booking.objects.filter(
        state=Booking.STATE_INACTIVE,
        reservation_time__endswith__lt=now,
    )

    for booking in bookings:
        log.info(f"Marking booking as ended: {booking.id}")
        booking.state = Booking.STATE_ENDED
        booking.save()
