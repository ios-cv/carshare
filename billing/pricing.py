""" This module contains code related to calculating the price of rentals. """

import math

DAY_RATE = 24
HOUR_RATE = 4


def calculate_booking_cost(user, vehicle, start, end):
    """Calculates the cost of a rental."""

    # If user is an operator/admin then don't charge them.
    if user.is_operator:
        return 0

    # We don't actually care about the vehicle type as they are all the same price.

    # We have a day rate, so calculate the number of whole days the booking covers.
    delta = end - start

    day_amount = delta.days * DAY_RATE

    # Take the remainder, and charge the minimum of the hourly rate or one more day.
    hour_amount = min(DAY_RATE, math.ceil(delta.seconds / 3600) * HOUR_RATE)

    return day_amount + hour_amount
