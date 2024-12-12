from django.conf import settings


def get_contact_info(request):
    return {
        "CONTACT_PHONE": settings.CONTACT_PHONE,
        "CONTACT_EMAIL": settings.CONTACT_EMAIL,
        "CONTACT_INTERNATIONAL_PHONE": settings.CONTACT_INTERNATIONAL_PHONE,
    }
