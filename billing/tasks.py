import logging
import os
import stripe

from celery import shared_task

from datetime import time

from django.utils import timezone

from billing.models import BillingAccount
from bookings.models import Booking

log = logging.getLogger(__name__)

# TODO: Use Django Settings for this.
TAX_RATE_ID = os.environ.get("STRIPE_VAT_TAX_RATE_ID")
TAX_NUMBER_ID = os.environ.get("STRIPE_VAT_NUMBER_ID")


def last_month(now):
    # FIXME: needs to be timezone aware time.
    return timezone.datetime.combine(
        now.replace(day=1) - timezone.timedelta(days=1), time.max
    )


def invoice_line_text(booking):
    return (
        f"GO-EV Car Share: Rental #{booking.id:06d}, "
        f"{booking.reservation_time.lower:%d/%m/%y %H:%M} "
        f"to {booking.reservation_time.upper:%d/%m/%y %H:%M}, "
        f"({booking.user.first_name} {booking.user.last_name}) "
        f"[{booking.vehicle.registration}]."
    )


@shared_task(name="run_billing")
def run_billing():
    now = timezone.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    log.info(f"Running run_billing job at {current_time}")

    # Fetch all bookings in the "ended" state.
    # FIXME: Temporarily exclude bookings on "credit accounts" from billing process.
    bookings = Booking.objects.filter(
        state=Booking.STATE_ENDED,
        billing_account__credit_account=False,
    ).order_by("reservation_time")

    for booking in bookings:
        log.info(f"Starting billing process for booking: {booking.id}")

        # TODO: Handle "credit account" billing accounts differently here.

        # Don't bother doing anything on Stripe if the booking has zero cost.
        # Just mark as billed and return early.
        if booking.cost == 0:
            booking.state = Booking.STATE_BILLED
            booking.save()
            continue

        invoice_kwargs = {
            "customer": booking.billing_account.stripe_customer_id,
            "collection_method": "charge_automatically",
            "auto_advance": False,
            "pending_invoice_items_behavior": "exclude",
            "account_tax_ids": [TAX_NUMBER_ID],
            "rendering": {"pdf": {"page_size": "a4"}},
            "custom_fields": [],
        }

        if booking.billing_account.business_purchase_order:
            invoice_kwargs["custom_fields"].append(
                {
                    "name": "Purchase Order No.",
                    "value": booking.billing_account.business_purchase_order,
                }
            )

        invoice = stripe.Invoice.create(**invoice_kwargs)

        amount = booking.cost * 100

        item = stripe.InvoiceItem.create(
            customer=booking.billing_account.stripe_customer_id,
            invoice=invoice.id,
            currency="gbp",
            description=invoice_line_text(booking),
            amount=amount,
            tax_rates=[TAX_RATE_ID],
        )

        booking.state = Booking.STATE_BILLED
        booking.stripe_invoice_item_id = item.id
        booking.save()


@shared_task(name="monthly_billing")
def monthly_billing():
    now = timezone.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    log.info(f"Running monthly_billing job at {current_time}")

    # Loop through all "credit accounts".
    accounts = BillingAccount.objects.filter(credit_account=True)

    end_before = last_month(timezone.now())
    log.info(f"Including all bookings which ended at or before: {end_before}")

    for account in accounts:
        # Get bookings for this account.
        bookings = Booking.objects.filter(
            billing_account=account,
            state=Booking.STATE_ENDED,
            reservation_time__endswith__lte=end_before,
        )

        # If no bookings in this category, then continue.
        if bookings.count() == 0:
            continue

        # We have bookings for this account.
        # First create the invoice.
        log.info(f"Creating Stripe invoice for billing account {account.id}")

        invoice_kwargs = {
            "customer": account.stripe_customer_id,
            "collection_method": "charge_automatically",
            "auto_advance": False,
            "pending_invoice_items_behavior": "exclude",
            "account_tax_ids": [TAX_NUMBER_ID],
            "rendering": {"pdf": {"page_size": "a4"}},
            "custom_fields": [],
        }
        invoice = stripe.Invoice.create(**invoice_kwargs)

        if account.business_purchase_order:
            invoice = stripe.Invoice.modify(
                invoice.id,
                custom_fields=[
                    {
                        "name": "Purchase Order No.",
                        "value": account.business_purchase_order,
                    },
                ],
            )

        for booking in bookings:
            log.info(f"Starting billing process for booking: {booking.id}")

            amount = booking.cost * 100

            item = stripe.InvoiceItem.create(
                customer=booking.billing_account.stripe_customer_id,
                invoice=invoice.id,
                currency="gbp",
                description=invoice_line_text(booking),
                amount=amount,
                tax_rates=[TAX_RATE_ID],
            )

            booking.state = Booking.STATE_BILLED
            booking.stripe_invoice_item_id = item.id
            booking.save()
