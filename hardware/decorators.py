import json
import logging
import string

from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings

from .models import Box

log = logging.getLogger(__name__)


def require_authenticated_box(view_func=None):
    """
    Decorator for views that checks the box authentication in the request headers,
    and returns a 401 status code otherwise.
    """

    def wrapper_func(request, *args, **kwargs):
        box_id = request.headers.get("X-Carshare-Box-ID", None)
        box_secret = request.headers.get("X-Carshare-Box-Secret", None)

        if (
            box_id is None
            or not all(c in string.hexdigits for c in box_id)
            or box_secret is None
            or len(box_id) > 16
            or len(box_secret) != 36
        ):
            return JsonResponse(
                {"error": "proper credentials must be provided"}, status=401
            )

        box = Box.objects.filter(serial=int(box_id, base=16), secret=box_secret).first()

        if box is None:
            log.info(f"Box {box_id} could not be authenticated.")
            log.debug(f"box ID: {box_id}, box secret: {box_secret}")
            return JsonResponse({"error": "unauthorized"}, status=401)
        else:
            # Update that we've seen the box.
            box.last_seen_at = timezone.now()
            box.save()
            return view_func(request, *args, box=box, **kwargs)

    return wrapper_func


def json_payload(view_func=None):
    """
    Decorator for views that parses the request body as JSON and injects it into the view.
    """

    def wrapper_func(request, *args, **kwargs):
        data = None
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid JSON payload"}, status=400)
        return view_func(request, *args, data=data, **kwargs)

    return wrapper_func

def strip_errors_from_api_response(view_func=None):
    """Utility function to strip error messages from API responses, to avoid exposing internal details to the hardware.
    """
    def strip_errors(json_object):
        if settings.STRIP_ERRORS_FROM_API_RESPONSE is False:
            return json_object
        else:
            if isinstance(json_object, dict):
                return {
                    k: strip_errors(v) for k, v in json_object.items() if k != "error"
                }
            elif isinstance(json_object, list):
                return [strip_errors(item) for item in json_object]
            else:
                return json_object

    def wrapper_func(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        if isinstance(response, JsonResponse):
            try:
                data = json.loads(response.content)
                stripped_data = strip_errors(data)
                response.content = json.dumps(stripped_data)
            except Exception:
                pass
        return response

    return wrapper_func