""" This module contains code related to calculating the price of rentals. """

import datetime
import math

from django.utils import timezone

DAY_RATE_2024 = 30
HOUR_RATE_2024 = 5

DAY_RATE_2026 = 33
HOUR_RATE_2026 = 6
ID_CUTOFF_2026 = 8622
TIME_CUTOFF_2026 = timezone.datetime(
    2026, 4, 1, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
)
SPECIAL_BILLING_ACCOUNTS_2026 = [
    29,
]


def calculate_booking_cost(
    user, vehicle, start, end, billing_account=None, booking=None
):
    """Calculates the cost of a rental."""

    # If user is an operator/admin then don't charge them.
    if user.is_operator:
        return 0

    # If booking ID is greater than ID_CUTOFF_2026 and booking start date is greater than 1st April 2026
    # then use new pricing. Also use new pricing for certain billing accounts if booking is > 1/4/26 whatever
    # the booking ID is.
    if booking is None:
        if start >= TIME_CUTOFF_2026:
            day_rate = DAY_RATE_2026
            hour_rate = HOUR_RATE_2026
        else:
            day_rate = DAY_RATE_2024
            hour_rate = HOUR_RATE_2024
    else:
        if (
            billing_account is not None
            and billing_account.id in SPECIAL_BILLING_ACCOUNTS_2026
            and start >= TIME_CUTOFF_2026
        ):
            day_rate = DAY_RATE_2026
            hour_rate = HOUR_RATE_2026
        elif booking.id >= ID_CUTOFF_2026 and start >= TIME_CUTOFF_2026:
            day_rate = DAY_RATE_2026
            hour_rate = HOUR_RATE_2026
        else:
            day_rate = DAY_RATE_2024
            hour_rate = HOUR_RATE_2024

    # We don't actually care about the vehicle type as they are all the same price.

    # We have a day rate, so calculate the number of whole days the booking covers.
    delta = end - start

    day_amount = delta.days * day_rate

    # Take the remainder, and charge the minimum of the hourly rate or one more day.
    hour_amount = min(day_rate, math.ceil(delta.seconds / 3600) * hour_rate)

    return day_amount + hour_amount
