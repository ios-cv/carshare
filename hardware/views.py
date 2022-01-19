from django.http import JsonResponse


def unlock(request):
    """View that is called by the box to ask if it can unlock the car or not."""

    return JsonResponse({"yes": True})
