import json

from django.http import JsonResponse

from .models import Box


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
            or box_secret is None
            or len(box_id) > 16
            or len(box_secret) != 36
        ):
            return JsonResponse(
                {"error": "proper credentials must be provided"}, status=401
            )

        box = Box.objects.filter(serial=int(box_id, base=16), secret=box_secret).first()

        if box is None:
            return JsonResponse({"error": "unauthorized"}, status=401)
        else:
            return view_func(request, *args, box=box, **kwargs)

    return wrapper_func


def json_payload(view_func=None):
    """
    Decorator for views that parses the request body as JSON and injects it into the view.
    """

    def wrapper_func(request, *args, **kwargs):
        data = json.loads(request.body)
        return view_func(request, *args, data=data, **kwargs)

    return wrapper_func
