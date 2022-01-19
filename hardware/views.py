from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def unlock(request):
    """View that is called by the box to ask if it can unlock the car or not."""
    print(request.body)
    return JsonResponse({"yes": True})
