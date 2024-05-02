from django import template

from bookings import models

register = template.Library()


@register.simple_tag
def user_can_access_booking(user, booking):
    return models.user_can_access_booking(user, booking)
