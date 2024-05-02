from django import template

from drivers.models import FullDriverProfile, ExternalDriverProfile

register = template.Library()


@register.simple_tag
def can_drive_full(user):
    return user.can_drive(profile_type=FullDriverProfile)


@register.simple_tag
def can_drive_external(user):
    return user.can_drive(profile_type=ExternalDriverProfile)
