""" This module contains code related to calculating the price of rentals. """

import datetime
import math

from django.utils import timezone

DAY_RATE = 24
HOUR_RATE = 4
NEW_DAY_RATE = 30
NEW_HOUR_RATE = 5


def calculate_booking_cost(user, vehicle, start, end):
    """Calculates the cost of a rental."""

    # If user is an operator/admin then don't charge them.
    if user.is_operator:
        return 0

    # If booking runs into 2024, then use new prices.
    new_billing_start = timezone.datetime(
        2024, 1, 1, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
    )
    if end > new_billing_start:
        day_rate = NEW_DAY_RATE
        hour_rate = NEW_HOUR_RATE
    else:
        day_rate = DAY_RATE
        hour_rate = HOUR_RATE

    # We don't actually care about the vehicle type as they are all the same price.

    # We have a day rate, so calculate the number of whole days the booking covers.
    delta = end - start

    day_amount = delta.days * day_rate

    # Take the remainder, and charge the minimum of the hourly rate or one more day.
    hour_amount = min(day_rate, math.ceil(delta.seconds / 3600) * hour_rate)

    return day_amount + hour_amount
