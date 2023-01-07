import logging
import os
import stripe

from celery import shared_task

from django.utils import timezone

from bookings.models import Booking

log = logging.getLogger(__name__)

# TODO: Use Django Settings for this.
TAX_RATE_ID = os.environ.get("STRIPE_VAT_TAX_ID")


@shared_task(name="run_billing")
def run_billing():
    now = timezone.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    log.info(f"Running run_billing job at {current_time}")

    # Fetch all bookings in the "ended" state.
    bookings = Booking.objects.filter(
        state=Booking.STATE_ENDED,
    )

    for booking in bookings:
        log.info(f"Starting billing process for booking: {booking.id}")

        # TODO: Handle "credit account" billing accounts differently here.

        # Don't bother doing anything on Stripe if the booking has zero cost.
        # Just mark as billed and return early.
        if booking.cost == 0:
            booking.state = Booking.STATE_BILLED
            booking.stripe_invoice_item_id = item.id
            booking.save()
            return

        invoice = stripe.Invoice.create(
            customer=booking.billing_account.stripe_customer_id,
            collection_method="charge_automatically",
            auto_advance=False,
            pending_invoice_items_behavior="exclude",
        )

        (days, hours) = booking.duration
        description = f"GO-EV Car Share: Rental #{booking.id:06d}. ({days} days, {hours:.2f} hours)"
        amount = booking.cost * 100

        item = stripe.InvoiceItem.create(
            customer=booking.billing_account.stripe_customer_id,
            invoice=invoice.id,
            currency="gbp",
            description=description,
            amount=amount,
            tax_rates=[TAX_RATE_ID],
        )

        booking.state = Booking.STATE_BILLED
        booking.stripe_invoice_item_id = item.id
        booking.save()
