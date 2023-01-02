import logging

from django.conf import settings
from django.http import HttpResponse, Http404

from drivers.models import FullDriverProfile

log = logging.getLogger(__name__)


def nginx_redirect(url):
    uri = f"/{settings.MEDIA_PROTECTED_URL}{url}"
    log.debug(f"Telling nginx to serve:{uri}")

    response = HttpResponse()
    response["X-Accel-Redirect"] = uri
    response["Content-Type"] = ""
    return response


def media(request, url):
    # URL must begin with MEDIA_URL, so strip that out.
    if url.startswith(settings.MEDIA_URL[1:]):
        url = url[len(settings.MEDIA_URL[1:]) :]
    else:
        raise Http404

    log.debug(f"Media URL requested: {url}")

    # Operator or Staff or Super User can see everything.
    if request.user.is_operator or request.user.is_staff or request.user.is_superuser:
        return nginx_redirect(url)

    # Split the URL into parts.
    parts = url.split("/")

    # Handle driver profile files
    if parts[0] == "drivers" and parts[1] == "profiles":
        if parts[2] == "licence_front":
            dp = FullDriverProfile.objects.filter(licence_front=url).first()
            if dp is not None and dp.user == request.user:
                return nginx_redirect(url)
            else:
                raise Http404

        if parts[2] == "licence_back":
            dp = FullDriverProfile.objects.filter(licence_back=url).first()
            if dp is not None and dp.user == request.user:
                return nginx_redirect(url)
            else:
                raise Http404

        if parts[2] == "licence_selfie":
            dp = FullDriverProfile.objects.filter(licence_selfie=url).first()
            if dp is not None and dp.user == request.user:
                return nginx_redirect(url)
            else:
                raise Http404

    # Handle hardware files
    if parts[0] == "hardware":
        # All files within hardware are public.
        return nginx_redirect(url)

    raise Http404
